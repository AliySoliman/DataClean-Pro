# DataClean Pro — User Guide
### CSV to Excel Converter with Intelligent Data Cleaning

---

## What This Tool Does

DataClean Pro converts your CSV files into clean, formatted Excel files automatically.  
It removes duplicate records, drops empty columns, and handles missing values — all before writing the final Excel file.

You have **two ways** to use it:

| Mode | Best for | File to run |
|------|----------|-------------|
| **Visual App** (Streamlit) | Daily use, non-technical users | `app.py` |
| **Script only** (Command line) | Automation, scheduling, power users | `clean_csv.py` |

---

## Folder Structure

```
DataCleanPro/
│
├── app.py               ← Visual web app (recommended)
├── clean_csv.py         ← Standalone script (no interface)
├── requirements.txt     ← Python packages to install
└── Instructions(How to use).html      ← This file
```

Place your CSV files anywhere on your computer.  
The tool will write the cleaned Excel files to an `output/` folder automatically.

---

## Step 1 — Install Python

If you don't have Python installed:

1. Go to https://www.python.org/downloads/
2. Download **Python 3.10 or newer**
3. During installation, **check the box** that says *"Add Python to PATH"*
4. Click Install

To verify it worked, open Terminal (Mac/Linux) or Command Prompt (Windows) and type:
```
python --version
```
You should see something like `Python 3.11.4`.

---

## Step 2 — Install Required Packages

Open Terminal / Command Prompt, navigate to the `DataCleanPro` folder, and run:

```bash
pip install -r requirements.txt
```

This installs everything the tool needs. You only need to do this **once**.

---

## Option A — Visual App (Recommended)

### How to Launch

In your terminal, inside the `DataCleanPro` folder, run:

```bash
streamlit run app.py
```

A browser window will open automatically at `http://localhost:8501`.

### How to Use

1. **Upload** one or more CSV files using the file upload area
2. **Configure** cleaning options in the left sidebar:
   - Set the column missing-value threshold (default: drop fully empty columns only)
   - Choose how to handle missing row values (drop, fill with mean, fill with fixed value, etc.)
   - Toggle duplicate removal on/off
   - Set the Excel sheet name
3. **Review** the results — each file shows:
   - Quality score (0–100) before cleaning
   - How many rows/columns were removed or changed
   - A missing value chart per file
   - A detailed cleaning log
4. **Download** each Excel file individually, or click **Download ALL as ZIP** to get everything at once
5. Optionally download the **Cleaning Log (.txt)** for a full audit trail

### To Stop the App

Press `Ctrl + C` in the terminal window.

---

## Option B — Standalone Script (No Interface)

Use this if you want to run it from the command line or schedule it automatically.

### Basic Usage

```bash
# Clean all CSVs in the current folder
python clean_csv.py

# Clean a specific file
python clean_csv.py mydata.csv

# Clean multiple files
python clean_csv.py sales.csv customers.csv inventory.csv

# Clean all CSVs in a specific folder
python clean_csv.py --input C:/Users/Me/Desktop/data
```

### Output

Cleaned Excel files and log files are saved in an `output/` folder (created automatically).

```
output/
├── mydata_20250516.xlsx
├── mydata_20250516_log.txt
├── sales_20250516.xlsx
└── sales_20250516_log.txt
```

### Strategy Options

```bash
# Drop rows with ANY missing value (default)
python clean_csv.py --strategy drop_row

# Drop only fully blank rows
python clean_csv.py --strategy drop_empty

# Fill missing values with column mean (numeric) or most common value (text)
python clean_csv.py --strategy fill_mean

# Same but using median instead of mean
python clean_csv.py --strategy fill_median

# Fill all missing values with 0
python clean_csv.py --strategy fill_zero
```

### Additional Options

```bash
# Specify output folder
python clean_csv.py --output D:/cleaned_files

# Change the column drop threshold (e.g. drop if >50% missing)
python clean_csv.py --col-threshold 50

# Keep duplicate rows (do not remove them)
python clean_csv.py --keep-duplicates

# Skip writing the log file
python clean_csv.py --no-log

# Set a custom Excel sheet name
python clean_csv.py --sheet "Monthly Report"
```

---

## Scheduling (Run Automatically Every Day)

### Windows — Task Scheduler

1. Open **Task Scheduler** (search for it in Start menu)
2. Click **Create Basic Task**
3. Set trigger to **Daily** at your preferred time
4. For the action, set:
   - Program: `python`
   - Arguments: `C:\path\to\DataCleanPro\clean_csv.py --input C:\path\to\your\csvs --strategy fill_mean`
5. Click Finish

### Mac / Linux — Cron Job

Open terminal and type `crontab -e`, then add a line like:

```bash
# Run every day at 8:00 AM
0 8 * * * python /path/to/DataCleanPro/clean_csv.py --input /path/to/csvs --strategy fill_mean
```

---

## Understanding the Quality Score

Each file receives a quality score (0–100) calculated before any cleaning:

| Score | Meaning |
|-------|---------|
| 85–100 | Excellent — data is mostly clean |
| 60–84  | Fair — some missing values or duplicates present |
| 0–59   | Poor — significant data quality issues |

The score is based on: % of missing values, % of duplicate rows, and % of empty columns.

---

## Cleaning Order (Always This Sequence)

1. **Columns first** — drop any column that exceeds the missing % threshold
2. **Duplicates** — remove identical rows
3. **Rows** — handle remaining missing values using the chosen strategy

This order matters: cleaning bad columns first prevents good rows from being dropped unnecessarily.

---

## Supported File Formats

| Input | Output |
|-------|--------|
| `.csv` (comma-separated) | `.xlsx` (Excel) |
| `.csv` (semicolon-separated) | `.xlsx` |
| `.csv` (tab-separated) | `.xlsx` |
| `.csv` (pipe-separated) | `.xlsx` |

Encoding is detected automatically (UTF-8, Latin-1, Windows-1252, and others).

---

## Troubleshooting

**"No module named streamlit"**  
→ Run `pip install -r requirements.txt` again.

**"No rows left after cleaning"**  
→ Switch the row strategy to `Fill with mean / median` in the sidebar (or `--strategy fill_mean` in the script). This preserves all rows.

**File opens but data looks wrong (garbled characters)**  
→ The tool detects encoding automatically. If it still looks wrong, open the CSV in a text editor and check what encoding it uses, then let us know.

**Excel file won't open**  
→ Make sure Microsoft Excel or LibreOffice is installed. The output is a standard `.xlsx` file.

---

## Contact & Support

For questions, additional features, or custom automation setup, please reach out via the project channel.

---

*DataClean Pro — Built with Python, Pandas, Streamlit, and Plotly*
