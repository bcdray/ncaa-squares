import base64
import json
import os

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def get_client(credentials_file="credentials.json"):
    creds_b64 = os.environ.get("GOOGLE_CREDENTIALS_B64", "")
    if creds_b64:
        creds_json = json.loads(base64.b64decode(creds_b64))
        creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    elif os.path.exists(credentials_file):
        creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    else:
        creds_raw = os.environ.get("GOOGLE_CREDENTIALS", "")
        if creds_raw:
            creds_json = json.loads(creds_raw)
            creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
        else:
            raise RuntimeError("No credentials found. Set GOOGLE_CREDENTIALS_B64 or provide credentials.json.")
    return gspread.authorize(creds)


GRID_TAB = os.environ.get("NCAA_GRID_TAB", "Sheet1")

DEFAULT_PAYOUTS = {
    "Round of 64": 5,
    "Round of 32": 10,
    "Sweet 16": 20,
    "Elite 8": 40,
    "Final Four": 75,
    "Championship": 150,
}


def load_grid(spreadsheet_id):
    """Read the 10x10 grid tab.

    Returns a dict mapping (winner_digit, loser_digit) -> participant name.
    Row 1 has digits 0-9 in columns B-K (winner's last digit).
    Column A rows 2-11 have digits 0-9 (loser's last digit).
    Cells B2:K11 have participant names.
    """
    client = get_client()
    sheet = client.open_by_key(spreadsheet_id).worksheet(GRID_TAB)
    rows = sheet.get_all_values()

    grid = {}
    for r in range(1, 11):  # rows 2-11 (0-indexed 1-10)
        loser_digit = int(rows[r][0])
        for c in range(1, 11):  # columns B-K (0-indexed 1-10)
            winner_digit = int(rows[0][c])
            name = rows[r][c].strip()
            grid[(winner_digit, loser_digit)] = name
    return grid


def load_payouts(spreadsheet_id):
    """Load payouts. Tries 'Config' tab, falls back to defaults."""
    try:
        client = get_client()
        sheet = client.open_by_key(spreadsheet_id).worksheet("Config")
        rows = sheet.get_all_values()

        payouts = {}
        for row in rows[1:]:
            if len(row) >= 2 and row[0].strip():
                round_name = row[0].strip()
                payout_str = row[1].strip().replace("$", "").replace(",", "")
                try:
                    payouts[round_name] = int(payout_str)
                except ValueError:
                    pass
        if payouts:
            return payouts
    except Exception:
        pass
    return DEFAULT_PAYOUTS.copy()
