"""Convert all .xlsx files in a folder to .csv files.

Usage:
    python3 -m excel_utils.xlsx2csv                           # input/ → input/
    python3 -m excel_utils.xlsx2csv ./data/input ./data/csv   # custom paths
    python3 -m excel_utils.xlsx2csv --sheet Sheet2            # specify sheet
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def convert_folder(
    input_dir: Path,
    output_dir: Path,
    sheet: Optional[str] = None,
    recursive: bool = False,
    no_header: bool = False,
) -> list[Path]:
    """
    Convert all .xlsx/.xls files in input_dir to .csv files in output_dir.

    Returns list of created .csv file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    pattern = "**/*.xlsx" if recursive else "*.xlsx"
    xlsx_files = sorted(input_dir.glob(pattern))
    xls_files = sorted(input_dir.glob(pattern.replace("xlsx", "xls")))

    all_files = xlsx_files + xls_files
    if not all_files:
        logger.warning("No .xlsx or .xls files found in %s", input_dir)
        return []

    created: list[Path] = []
    for src in all_files:
        stem = src.stem

        xl = pd.ExcelFile(src)
        sheet_names = [sheet] if sheet else xl.sheet_names

        for sn in sheet_names:
            if sn not in xl.sheet_names:
                logger.warning("Sheet '%s' not found in %s, skipping", sn, src.name)
                continue

            suffix = f"_{sn}" if not sheet and len(xl.sheet_names) > 1 else ""
            dst = output_dir / f"{stem}{suffix}.csv"

            logger.info("Converting %s → %s", src.name, dst.name)
            df = pd.read_excel(src, sheet_name=sn, header=None if no_header else 0)
            df.to_csv(dst, index=False, encoding="utf-8", header=not no_header)

            created.append(dst)
            logger.info("  %s rows written", f"{len(df):,}")

        xl.close()

    return created


def main():
    parser = argparse.ArgumentParser(
        description="Convert .xlsx/.xls files to .csv"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="./data/input",
        help="Input directory containing .xlsx files (default: ./data/input)",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output directory for .csv files (default: same as input)",
    )
    parser.add_argument(
        "-s", "--sheet",
        default=None,
        help="Only convert this sheet (default: all sheets)",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Search subdirectories recursively",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Do not write column headers (use when referencing columns by position like column0, column1)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    input_dir = Path(args.input)
    output_dir = Path(args.output) if args.output else input_dir

    if not input_dir.exists():
        logger.error("Input directory not found: %s", input_dir)
        sys.exit(1)

    created = convert_folder(input_dir, output_dir, sheet=args.sheet,
                             recursive=args.recursive, no_header=args.no_header)

    print(f"\nDone. {len(created)} .csv file(s) created in {output_dir}")

    for f in created:
        print(f"  {f}")


if __name__ == "__main__":
    main()
