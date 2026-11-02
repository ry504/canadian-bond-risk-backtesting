"""Reproduce everything: download data -> SQLite -> analysis -> charts -> Excel CSVs -> PDF report.
Usage (from repo root):  python src/run_all.py"""
import pathlib
import platform
import subprocess
import sys

SRC = pathlib.Path(__file__).resolve().parent
ROOT = SRC.parent
STEPS = ["fetch_data.py", "run_analysis.py", "make_charts.py", "export_excel_csv.py"]
for s in STEPS:
    print(f"\n>>> {s}")
    subprocess.run([sys.executable, str(SRC / s)], cwd=SRC, check=True)

print("\n>>> tests")
subprocess.run([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")], cwd=ROOT, check=True)

chrome = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
if chrome.exists():
    subprocess.run([str(chrome), "--headless=new", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    f"--print-to-pdf={ROOT / 'report' / 'Research_Report.pdf'}", str(ROOT / "report" / "report.html")],
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(">>> report PDF rebuilt (report/report.html is hand-written; update its numbers if results change)")
else:
    print(">>> Chrome not found: open report/report.html and print to PDF to rebuild the report")
