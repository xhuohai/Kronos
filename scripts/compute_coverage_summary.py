#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


def has_window(datetimes: list[str], start: str, end: str) -> bool:
    return any(start <= d[-8:] <= end for d in datetimes)


def check_file(path: Path) -> tuple[bool, bool]:
    dts = []
    with path.open('r', encoding='utf-8', errors='ignore') as f:
        r = csv.DictReader(f)
        for row in r:
            dt = (row.get('datetime') or '').strip()
            if dt:
                dts.append(dt)
    trade_ok = has_window(dts, '14:50:00', '15:00:00')
    exit_ok = has_window(dts, '09:30:00', '10:30:00')
    return trade_ok, exit_ok


def main() -> None:
    parser = argparse.ArgumentParser(description='Compute minute window coverage summary.')
    parser.add_argument('--root', required=True, help='Root of cleaned CSV tree')
    parser.add_argument('--max-files', type=int, default=0, help='Limit files for quick runs; 0 = all')
    args = parser.parse_args()

    root = Path(args.root)
    files = sorted(root.rglob('*.csv'))
    if args.max_files > 0:
        files = files[: args.max_files]

    total = len(files)
    trade_cnt = 0
    exit_cnt = 0
    joint_cnt = 0
    for p in files:
        trade_ok, exit_ok = check_file(p)
        trade_cnt += int(trade_ok)
        exit_cnt += int(exit_ok)
        joint_cnt += int(trade_ok and exit_ok)

    trade_cov = trade_cnt / total if total else 0.0
    exit_cov = exit_cnt / total if total else 0.0
    joint_cov = joint_cnt / total if total else 0.0

    print(f'total_files={total}')
    print(f'coverage_trade_window={trade_cov:.4f}')
    print(f'coverage_exit_window={exit_cov:.4f}')
    print(f'joint_coverage={joint_cov:.4f}')


if __name__ == '__main__':
    main()
