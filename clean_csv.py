"""
clean_csv.py — DataClean Pro (Standalone Script)
-------------------------------------------------
Converts CSV files to cleaned Excel files from the command line.
No interface needed. Just run it and it processes everything automatically.

Usage:
    python clean_csv.py                        # cleans all CSVs in current folder
    python clean_csv.py data.csv               # cleans a single file
    python clean_csv.py file1.csv file2.csv    # cleans multiple specific files
    python clean_csv.py --input ./my_folder    # cleans all CSVs in a folder
    python clean_csv.py --strategy fill_mean   # choose missing value strategy

Options:
    --input PATH          Folder or file(s) to process (default: current folder)
    --output PATH         Output folder for Excel files (default: ./output)
    --strategy            How to handle missing row values:
                            drop_row      → remove any row with a missing value (default)
                            drop_empty    → remove only fully-blank rows
                            fill_mean     → fill numeric with mean, text with mode
                            fill_median   → fill numeric with median, text with mode
                            fill_zero     → fill everything with 0
    --col-threshold INT   Drop column if % missing >= this value (default: 100)
    --keep-duplicates     Do NOT remove duplicate rows
    --no-log              Skip writing the audit log .txt file
    --sheet NAME          Excel sheet name (default: Cleaned Data)
"""

import sys
import os
import io
import argparse
import chardet
import pandas as pd
from datetime import datetime
from pathlib import Path

try:
    from openpyxl import load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ── Config defaults ───────────────────────────────────────────────────────────
DEFAULT_COL_THRESHOLD = 100   # drop column only if fully empty
DEFAULT_STRATEGY      = "drop_row"
DEFAULT_SHEET         = "Cleaned Data"


# ── Helpers ───────────────────────────────────────────────────────────────────
def detect_encoding(raw_bytes):
    result = chardet.detect(raw_bytes)
    return result.get("encoding") or "utf-8"


def detect_delimiter(sample):
    for delim in [",", ";", "\t", "|"]:
        if delim in sample:
            return delim
    return ","


def col_type_summary(df):
    summary = {"Numeric": 0, "Categorical": 0, "Datetime": 0}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            summary["Numeric"] += 1
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            summary["Datetime"] += 1
        else:
            summary["Categorical"] += 1
    return {k: v for k, v in summary.items() if v > 0}


def quality_score(df_raw, dropped_cols, col_threshold):
    if df_raw.empty:
        return 0
    total_cells = df_raw.shape[0] * df_raw.shape[1]
    missing     = df_raw.isna().sum().sum()
    dup_rows    = df_raw.duplicated().sum()
    empty_cols  = len(dropped_cols)
    penalty  = (missing    / max(total_cells, 1))       * 40
    penalty += (dup_rows   / max(len(df_raw), 1))       * 30
    penalty += (empty_cols / max(df_raw.shape[1], 1))   * 30
    return max(0, min(100, round(100 - penalty)))


def clean_dataframe(df_raw, strategy, col_threshold, remove_duplicates):
    report = {
        "rows_before":  len(df_raw),
        "cols_before":  len(df_raw.columns),
        "dropped_cols": [],
        "removed_dup":  0,
        "removed_rows": 0,
        "imputed_cols": [],
        "rows_after":   0,
        "cols_after":   0,
    }
    df = df_raw.copy()
    n  = len(df)

    # Step 1 — columns
    if n > 0:
        for col in list(df.columns):
            pct = df[col].isna().sum() / n * 100
            if pct >= col_threshold:
                report["dropped_cols"].append((col, round(pct, 1)))
                df = df.drop(columns=[col])

    if df.columns.empty:
        raise ValueError("All columns dropped. Raise --col-threshold.")

    # Step 2 — duplicates
    if remove_duplicates:
        before = len(df)
        df = df.drop_duplicates()
        report["removed_dup"] = before - len(df)

    # Step 3 — rows
    if strategy == "drop_row":
        before = len(df)
        df = df.dropna()
        report["removed_rows"] = before - len(df)

    elif strategy == "drop_empty":
        before = len(df)
        df = df.dropna(how="all")
        report["removed_rows"] = before - len(df)

    elif strategy in ("fill_mean", "fill_median"):
        for col in df.columns:
            if df[col].isna().any():
                if pd.api.types.is_numeric_dtype(df[col]):
                    val = df[col].mean() if strategy == "fill_mean" else df[col].median()
                    df[col] = df[col].fillna(val)
                    report["imputed_cols"].append((col, strategy.replace("fill_", ""), round(float(val), 4)))
                else:
                    mode_vals = df[col].mode()
                    if not mode_vals.empty:
                        df[col] = df[col].fillna(mode_vals[0])
                        report["imputed_cols"].append((col, "mode", str(mode_vals[0])))

    elif strategy == "fill_zero":
        for col in df.columns:
            if df[col].isna().any():
                df[col] = df[col].fillna(0)
                report["imputed_cols"].append((col, "fixed", 0))

    report["rows_after"] = len(df)
    report["cols_after"] = len(df.columns)
    return df, report


def write_excel(df, sheet_name, output_path):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        ws = writer.sheets[sheet_name[:31]]

        # Style header
        hdr_fill = PatternFill("solid", fgColor="00FF87")
        hdr_font = Font(name="Calibri", bold=True, color="000000", size=11)
        thin     = Side(style="thin", color="00CC6A")
        for cell in ws[1]:
            cell.fill      = hdr_fill
            cell.font      = hdr_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border    = Border(bottom=thin)

        ws.freeze_panes = "A2"

        for col_cells in ws.columns:
            try:
                max_len = max(
                    (len(str(c.value)) if c.value is not None else 0 for c in col_cells),
                    default=0,
                )
                ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 60)
            except Exception:
                pass

    with open(output_path, "wb") as fh:
        fh.write(buf.getvalue())


def write_log(filename, report, score, enc, delim, output_path):
    lines = [
        "=" * 60,
        "  DataClean Pro — Cleaning Report",
        f"  File      : {filename}",
        f"  Date      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        "",
        f"  Quality Score (before) : {score}/100",
        "",
        "  SUMMARY",
        f"  Encoding    : {enc}",
        f"  Delimiter   : {repr(delim)}",
        f"  Rows before : {report['rows_before']}",
        f"  Rows after  : {report['rows_after']}",
        f"  Cols before : {report['cols_before']}",
        f"  Cols after  : {report['cols_after']}",
        "",
    ]
    if report["dropped_cols"]:
        lines.append("  DROPPED COLUMNS")
        for col, pct in report["dropped_cols"]:
            lines.append(f"  - '{col}' ({pct}% missing) removed")
        lines.append("")
    if report["removed_dup"]:
        lines.append(f"  DUPLICATES : {report['removed_dup']} row(s) removed")
        lines.append("")
    if report["removed_rows"]:
        lines.append(f"  MISSING ROWS : {report['removed_rows']} row(s) dropped")
        lines.append("")
    if report["imputed_cols"]:
        lines.append("  IMPUTED COLUMNS")
        for col, method, val in report["imputed_cols"]:
            lines.append(f"  - '{col}' filled with {method} = {val}")
        lines.append("")
    lines += ["=" * 60, "  End of report", "=" * 60]
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def process_file(csv_path, output_dir, args):
    csv_path = Path(csv_path)
    print(f"\n  Processing: {csv_path.name}")

    raw_bytes = csv_path.read_bytes()
    enc   = detect_encoding(raw_bytes)
    sample = raw_bytes[:4096].decode(enc, errors="replace")
    delim = detect_delimiter(sample)

    try:
        df_raw = pd.read_csv(
            io.BytesIO(raw_bytes),
            encoding=enc,
            sep=delim,
            on_bad_lines="skip",
        )
    except Exception as e:
        print(f"  ERROR reading file: {e}")
        return False

    if df_raw.empty:
        print(f"  SKIPPED — file is empty.")
        return False

    score = quality_score(df_raw, [], args.col_threshold)
    print(f"  Quality score (before): {score}/100")

    try:
        df, report = clean_dataframe(
            df_raw,
            strategy=args.strategy,
            col_threshold=args.col_threshold,
            remove_duplicates=not args.keep_duplicates,
        )
    except ValueError as e:
        print(f"  ERROR: {e}")
        return False

    if df.empty:
        print(f"  SKIPPED — no rows remain after cleaning.")
        return False

    timestamp = datetime.now().strftime("%Y%m%d")
    out_stem  = csv_path.stem + f"_{timestamp}"
    xlsx_path = output_dir / f"{out_stem}.xlsx"
    log_path  = output_dir / f"{out_stem}_log.txt"

    write_excel(df, args.sheet, xlsx_path)
    print(f"  Saved Excel : {xlsx_path.name}")
    print(f"  Rows: {report['rows_before']} → {report['rows_after']}  |  Cols: {report['cols_before']} → {report['cols_after']}")

    if report["dropped_cols"]:
        for col, pct in report["dropped_cols"]:
            label = "fully empty" if pct == 100 else f"{pct}% missing"
            print(f"  Column '{col}' dropped ({label})")

    if not args.no_log:
        write_log(csv_path.name, report, score, enc, delim, log_path)
        print(f"  Saved log   : {log_path.name}")

    return True


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="DataClean Pro — Convert & clean CSV files to Excel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("files", nargs="*", help="CSV file(s) to process")
    parser.add_argument("--input",          default=".",  help="Input folder (default: current folder)")
    parser.add_argument("--output",         default="output", help="Output folder (default: ./output)")
    parser.add_argument("--strategy",       default=DEFAULT_STRATEGY,
                        choices=["drop_row","drop_empty","fill_mean","fill_median","fill_zero"])
    parser.add_argument("--col-threshold",  type=int, default=DEFAULT_COL_THRESHOLD)
    parser.add_argument("--keep-duplicates",action="store_true")
    parser.add_argument("--no-log",         action="store_true")
    parser.add_argument("--sheet",          default=DEFAULT_SHEET)
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.files:
        csv_files = [Path(f) for f in args.files if Path(f).suffix.lower() == ".csv"]
    else:
        input_dir = Path(args.input)
        csv_files = list(input_dir.glob("*.csv"))

    if not csv_files:
        print("No CSV files found. Pass file paths or use --input to specify a folder.")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"  DataClean Pro")
    print(f"  Files found : {len(csv_files)}")
    print(f"  Strategy    : {args.strategy}")
    print(f"  Output      : {output_dir.resolve()}")
    print(f"{'='*50}")

    ok = 0
    for f in csv_files:
        if process_file(f, output_dir, args):
            ok += 1

    print(f"\n{'='*50}")
    print(f"  Done — {ok}/{len(csv_files)} file(s) processed successfully.")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
