"""Offline case runner for launch-relative analog distributions."""
import json
import os
import sys
from pathlib import Path

# The official safe-path interpreter omits the script directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import predict


def run():
    source = Path(os.getenv('MAKEFUN_INPUT_DIR', '/input'))
    destination = Path(os.getenv('MAKEFUN_OUTPUT_DIR', '/output'))
    destination.mkdir(parents=True, exist_ok=True)
    for case_file in sorted(source.glob('*.in')):
        payload = json.loads(case_file.read_bytes())
        answer = predict(payload)
        encoded = json.dumps(answer, allow_nan=False, separators=(',', ':')) + '\n'
        if len(encoded.encode('utf-8')) > 65536:
            raise ValueError('Forecast exceeds output limit')
        (destination / (case_file.stem + '.out')).write_text(encoded, encoding='utf-8')


if __name__ == '__main__':
    run()
