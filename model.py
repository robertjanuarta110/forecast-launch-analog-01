"""Launch-relative empirical forecasts; Python standard library only."""
import math
import re
import unicodedata
from datetime import datetime, timedelta
from statistics import NormalDist, median

LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)
NORMAL = NormalDist()
LAGS = ((-3, 0), (-8, -3), (-16, -8), (-28, -16), (-72, -28))


def instant(text):
    return datetime.fromisoformat(text.replace('Z', '+00:00'))


def number(value):
    return isinstance(value, (float, int)) and math.isfinite(value) and value >= 0


def identity(text):
    plain = unicodedata.normalize('NFKD', str(text)).casefold()
    return ''.join(c for c in plain if c.isalnum())


def same_game(analog, case):
    """Names and source URLs identify games; dates alone do not."""
    game = case.get('game', {})
    name = identity(game.get('name', ''))
    if name and name == identity(analog.get('name', '')):
        return True
    source = game.get('source')
    if source and source == analog.get('source'):
        return True
    own_id = game.get('twitch_id')
    return bool(own_id and str(own_id) == str(analog.get('twitch_id', '')))


def is_launch(analog):
    text = analog.get('unlock', '').casefold()
    return not any(tag in text for tag in ('not a launch', 'target-history', 'before release'))


def hourly(rows, checkpoint):
    """Collapse raw minute reads once; reject future timestamps before aggregation."""
    buckets = {}
    for row in rows:
        timestamp = row.get('from', row.get('at'))
        if not timestamp or not number(row.get('viewers')):
            continue
        at = instant(timestamp)
        if at >= checkpoint:
            continue
        key = at.replace(minute=0, second=0, microsecond=0)
        buckets.setdefault(key, []).append(row)
    result = {}
    for at, group in buckets.items():
        channels = [r['channels'] for r in group if number(r.get('channels'))]
        result[at] = (sum(r['viewers'] for r in group) / len(group),
                      sum(channels) / len(channels) if channels else None)
    return result


def features(points, day, first, channels):
    values = []
    for start, end in LAGS:
        window = [v[0] for at, v in points.items()
                  if start <= (at - day).total_seconds() / 3600 < end]
        values.append(math.log(max(1, median(window)) / max(1, first)) if window else None)
    channel_window = [v[1] for at, v in points.items() if v[1] is not None
                      and -12 <= (at - day).total_seconds() / 3600 < 0]
    values.append(math.log(max(1, median(channel_window)) / max(1, channels))
                  if channel_window and number(channels) else None)
    values.append(math.log(max(1, first)))
    values.append(math.log(max(1, channels)) if number(channels) else None)
    return values


def regime(text, platforms=''):
    # Research-note suffixes contain hindsight statistics, and are never features.
    text = re.split(r'Source:|Tier:|Research note:', text, flags=re.I)[0].casefold()
    early = bool(re.search(r'early.access|premium|deluxe', text)) and 'no early access' not in text
    rolling = 'midnight local' in text or 'rolling' in text
    global_time = 'global' in text or 'simultaneous' in text
    console = bool(platforms) and not re.search(r'\bpc\b|steam|stadia', platforms, re.I)
    return (float(early), float(rolling or console), float(global_time))


def target(case):
    day = instant(case['day_start'])
    checkpoint = instant(case['checkpoint'])
    first_row = next((r for r in case.get('known', []) if r.get('hour') == 1
                      and instant(r.get('until', case['checkpoint'])) <= checkpoint), {})
    first = max(1, first_row.get('viewers', 1)) if number(first_row.get('viewers')) else 1
    channels = first_row.get('channels')
    points = hourly(case.get('history_hourly') or case.get('history', []), checkpoint)
    return day, first, features(points, day, first, channels)


def analogs(case):
    cutoff = instant(case['checkpoint'])
    result = []
    seen = set()
    for analog in case.get('comparables', []):
        if not is_launch(analog) or same_game(analog, case):
            continue
        day = instant(analog['day_start'])
        # Only completed historical launch days can supply outcomes.
        if day + timedelta(days=1) > cutoff:
            continue
        key = (identity(analog.get('name', '')), analog.get('source', ''))
        if key in seen:
            continue
        seen.add(key)
        rows = hourly(analog.get('hourly', []), day + timedelta(days=1))
        if day not in rows:
            continue
        first, channels = rows[day]
        if not number(first) or first < 1:
            continue
        pre = {at: v for at, v in rows.items() if at < day + timedelta(hours=1)}
        feats = features(pre, day, first, channels)
        ratios = {h: math.log(max(1, rows[day + timedelta(hours=h-1)][0]) / first)
                  for h in range(2, 25) if day + timedelta(hours=h-1) in rows}
        if len(ratios) < 12:
            continue
        result.append((feats, regime(analog.get('unlock', ''), analog.get('platforms', '')), ratios))
    return result


def distance(left, right):
    scales = (1.0, 1.2, 1.5, 1.8, 2.0, 1.0, 2.5, 2.5)
    parts = [min(9, ((a-b)/s)**2) for a, b, s in zip(left, right, scales)
             if a is not None and b is not None]
    return sum(parts) / max(1, len(parts))


def mixture_quantiles(samples, spread):
    total = sum(weight for _, weight in samples)
    low = min(value for value, _ in samples) - 7 * spread
    high = max(value for value, _ in samples) + 7 * spread
    quantiles = []
    for tau in LEVELS:
        a, b = low, high
        for _ in range(40):
            mid = (a+b)/2
            cdf = sum(w * NORMAL.cdf((mid-v)/spread) for v, w in samples) / total
            if cdf < tau:
                a = mid
            else:
                b = mid
        quantiles.append((a+b)/2)
    return quantiles


def predict(case):
    _, first, feats = target(case)
    pool = analogs(case)
    kind = regime(case.get('notes', ''), case.get('platforms', ''))
    weighted = []
    for other, other_kind, ratios in pool:
        penalty = sum((a-b)**2 for a, b in zip(kind, other_kind)) * 0.6
        weight = math.exp(-distance(feats, other) - penalty)
        weighted.append((weight, ratios))
    hours = []
    for h in range(2, 25):
        samples = [(r[h], w) for w, r in weighted if h in r]
        if samples:
            mass = sum(w for _, w in samples)
            effective = mass * mass / sum(w*w for _, w in samples)
            samples = [(v, w/mass) for v, w in samples]
            # Small historical pools cannot justify a confident trajectory.
            prior_mass = 0.10 + 0.35 / math.sqrt(effective)
            samples = [(v, w*(1-prior_mass)) for v, w in samples]
            for z, probability in ((-1.645, 0.10), (-0.674, 0.20), (0, 0.40),
                                   (0.674, 0.20), (1.645, 0.10)):
                samples.append((z * 0.15 * math.sqrt(h-1), prior_mass * probability))
            # Kernels acknowledge both hourly/minute measurement differences and
            # uncertainty between the finite set of observed launch trajectories.
            spread = 0.18 + 0.035 * math.sqrt(h-1) + 0.20 / math.sqrt(effective)
            offsets = mixture_quantiles(samples, spread)
        else:
            offsets = [NORMAL.inv_cdf(t) * 0.25 * math.sqrt(h-1) for t in LEVELS]
        q = [round(min(1e9, max(0.000001, first * math.exp(max(-25, min(25, x))))), 6)
             for x in offsets]
        hours.append({'hour': h, 'q': q})
    return {'hours': hours}
