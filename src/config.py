"""Shared constants. Every modelling assumption lives here so it is documented once."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "yields.db"
RAW_CSV = ROOT / "data" / "raw_valet_yields.csv"
OUT_DIR = ROOT / "output"
SQL_DIR = ROOT / "sql"

START_DATE = "2019-01-01"
END_DATE = None  # None -> today

# Bank of Canada Valet: Government of Canada benchmark bond yields, business daily, percent.
SERIES = {
    "BD.CDN.2YR.DQ.YLD": 2,
    "BD.CDN.5YR.DQ.YLD": 5,
    "BD.CDN.10YR.DQ.YLD": 10,
}
VALET_URL = "https://www.bankofcanada.ca/valet/observations/{ids}/json"

# Portfolio assumptions
PORTFOLIO_VALUE = 100_000_000          # C$
WEIGHTS = {2: 1 / 3, 5: 1 / 3, 10: 1 / 3}  # equal market-value weights, rebalanced daily
COUPONS_PER_YEAR = 2                    # Canadian government bonds pay semi-annually

# VaR assumptions
WINDOW = 250          # rolling observations, strictly prior to the day being tested
CONFIDENCE = 0.99
