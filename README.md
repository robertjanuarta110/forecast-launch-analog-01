# Launch Analog Quantiles

[![make.fun](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/c/gta6-twitch-ccu-forecast-01)
[![Rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/robertjanuarta110/forecast-launch-analog-01/rank.svg)](https://make.fun/c/gta6-twitch-ccu-forecast-01)
[![Reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/robertjanuarta110/forecast-launch-analog-01/reward.svg)](https://make.fun/c/gta6-twitch-ccu-forecast-01)

Offline Python forecasts of release-day Twitch concurrent viewers, using historical launch trajectories supplied in the case. Each case produces five quantiles for each of hours 2 through 24. Python 3.13 standard library only; no network calls, model API, packages or embedded answer tables.

## Run

    MAKEFUN_INPUT_DIR=/absolute/path/to/input MAKEFUN_OUTPUT_DIR=/absolute/path/to/output python3 -P -s main.py

The grader invokes `python3 -P -s /bot/main.py` with `/input` and `/output`. Every `*.in` is processed in sorted order. Output JSON has exactly 23 hourly rows, five increasing positive quantiles per row and no extra keys.

## Method

The model compares pre-checkpoint viewer and channel patterns to completed historical launches in the input. It learns each analog's log-viewer trajectory relative to its first hour, then weights those trajectories by prelaunch similarity and release regime. A Gaussian mixture produces marginal quantiles. A small persistence prior and kernel spread acknowledge limited analog samples. Missing histories and sparse analogs fall back to a widening persistence distribution.

Only information before the target checkpoint supplies target features. Future launches, the target's own category and explicitly nonlaunch histories are excluded from analog labels. Analog outcome rows after their release day are ignored. Unlock research-note suffixes containing hindsight figures are excluded from features.

## Local evidence

Development and validation use complete held-out launches, with semantic duplicate categories removed. The latest ten comparable launches were reserved for validation; training uses only development launches completed before the held-out checkpoint. Validation labels remain outside the input passed to the predictor.

The second model revision obtained mean log-pinball loss 0.612469 on 10 validation launches / 230 hours / 1,150 quantile items, against the exact house persistence baseline's 1.104334. Its 90% interval covered 91.74% of held-out hours. It beat the baseline on 9 of 10 launches. Development loss was 0.616360 against 0.888721 on 26 launches / 598 hours. These are historical backtests, not make.fun practice grades or a prediction of final rank.

A separate expanding chronological diagnostic returned loss 0.608985 against 1.104334 on the same latest-ten dates; unlike the fixed development split, earlier validation launches become usable historical training data there. It is reported separately rather than pooled with the fixed validation result.

Behavioral tests cover deterministic output, target future-data exclusion, semantic self exclusion, duplicate analogs, missing and zero counts, scaling, and equivalent minute/hourly input. Independent sandbox checks run each of the four kit practice cases twice under the kit's pinned Python 3.13.17 image, no network, read-only source/root, unprivileged user, 1 CPU, 1,024 MB and 64 processes. Outputs match byte for byte. Validation scripts and genuine native build evidence are maintained outside this submitted source tree.

## Limits and provenance

Thirty-seven historical launch curves are heterogeneous and not a representative sample of GTA VI. Historical hourly averages differ from final minute-read means. Intervals are marginal, not a joint path forecast. A future game's response to streamers, region unlocks and launch conditions can differ materially. No official practice score or final answer is available locally, and beating persistence locally does not establish beating the house model or winning a prize.

Underlying factual counts and release notes come from the official competition kit, which attributes hourly historical observations to [SullyGnome](https://sullygnome.com). The entry does not redistribute those observations, scrape the site or download runtime data.

Code generated and revised in genuine Hermes Agent sessions. Original user request and parent handoff provenance are preserved for transcript packaging. MIT licensed.
