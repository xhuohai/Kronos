#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path

STICKY_DECIMAL_PAIR = re.compile(r'(-?\d+\.\d{3})(-?\d+\.\d{3})')


def normalize_line(line: str) -> str:
    return STICKY_DECIMAL_PAIR.sub(r'\1,\2', line)


def clean_file(src: Path, dst: Path) -> tuple[int, int]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    ok = 0
    with src.open('r', encoding='utf-8', errors='ignore') as fin, dst.open('w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['datetime', 'open', 'high', 'low', 'close', 'volume', 'amount'])
        _ = fin.readline()
        for raw in fin:
            total += 1
            normalized = normalize_line(raw.strip())
            cols = [c for c in normalized.split(',') if c != '']
            if len(cols) < 7:
                continue
            try:
                _ = float(cols[1]); _ = float(cols[2]); _ = float(cols[3]); _ = float(cols[4]); _ = float(cols[5]); _ = float(cols[6])
            except ValueError:
                continue
            writer.writerow([cols[0].strip(), cols[1], cols[2], cols[3], cols[4], cols[5], cols[6]])
            ok += 1
    return total, ok


def main() -> None:
    parser = argparse.ArgumentParser(description='Clean sticky-field minute CSV into standardized schema.')
    parser.add_argument('--src', required=True, help='Source CSV root, e.g. /stock/extracted')
    parser.add_argument('--dst', required=True, help='Destination cleaned CSV root')
    parser.add_argument('--max-files', type=int, default=0, help='Limit files for quick runs; 0 = all')
    args = parser.parse_args()

    src_root = Path(args.src)
    dst_root = Path(args.dst)
    csv_files = sorted(src_root.rglob('*.csv'))
    if args.max_files > 0:
        csv_files = csv_files[: args.max_files]

    files = 0
    rows = 0
    rows_ok = 0
    for src in csv_files:
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        total, ok = clean_file(src, dst)
        files += 1
        rows += total
        rows_ok += ok

    ratio = rows_ok / rows if rows else 0.0
    print(f'files={files}')
    print(f'rows_total={rows}')
    print(f'rows_clean_ok={rows_ok}')
    print(f'clean_success_rate={ratio:.4f}')


if __name__ == '__main__':
    main()
