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

    Handles the actual sheet layout:
      Row 3 (index 2): winner digits in cols C-L (indices 2-11)
      Rows 4-13 (indices 3-12): loser digit in col B (index 1), names in cols C-L (indices 2-11)
    The header row is found dynamically by scanning for the row where
    cols 2-11 all contain single digits.
    """
    client = get_client()
    sheet = client.open_by_key(spreadsheet_id).worksheet(GRID_TAB)
    rows = sheet.get_all_values()

    # Find the header row containing winner digits
    header_row_idx = None
    for i, row in enumerate(rows):
        if len(row) >= 12:
            try:
                digits = [int(row[c]) for c in range(2, 12)]
                if len(digits) == 10:
                    header_row_idx = i
                    break
            except (ValueError, IndexError):
                continue

    if header_row_idx is None:
        return {}

    winner_digits = [int(rows[header_row_idx][c]) for c in range(2, 12)]

    grid = {}
    for row in rows[header_row_idx + 1:]:
        if len(row) < 12:
            continue
        try:
            loser_digit = int(row[1])
        except (ValueError, IndexError):
            continue
        for j, c in enumerate(range(2, 12)):
            winner_digit = winner_digits[j]
            name = row[c].strip() if c < len(row) else ""
            grid[(winner_digit, loser_digit)] = name

    return grid


ROUND_CODE_MAP = {
    "64": "Round of 64",
    "32": "Round of 32",
    "16": "Sweet 16",
    "8":  "Elite 8",
    "4":  "Final Four",
    "2":  "Championship",
}


def load_payouts(spreadsheet_id):
    """Load payouts from the 'Payouts' tab.

    The sheet has rows like: GAME, Round (numeric), WINNER, SCORE, LOSER, SCORE, POOL WINNER, PRIZE MONEY
    Round codes: 64=Round of 64, 32=Round of 32, 16=Sweet 16, 8=Elite 8, 4=Final Four, 2=Championship
    Payout is in col H (index 7), e.g. "$25".
    Returns the payout for each round (all games in a round pay the same amount).
    """
    import logging
    try:
        client = get_client()
        spreadsheet = client.open_by_key(spreadsheet_id)

        # Find the Payouts tab (case-insensitive)
        sheet = None
        all_tabs = [ws.title for ws in spreadsheet.worksheets()]
        logging.info("Available tabs: %s", all_tabs)
        for title in all_tabs:
            if title.strip().lower() == "payouts":
                sheet = spreadsheet.worksheet(title)
                break
        if sheet is None:
            logging.warning("No 'Payouts' tab found. Available: %s", all_tabs)
            return DEFAULT_PAYOUTS.copy()

        rows = sheet.get_all_values()
        payouts = {}
        for row in rows:
            if len(row) < 8:
                continue
            round_code = row[1].strip()
            payout_str = row[7].strip().replace("$", "").replace(",", "").strip()
            if round_code in ROUND_CODE_MAP and payout_str:
                try:
                    round_name = ROUND_CODE_MAP[round_code]
                    if round_name not in payouts:
                        payouts[round_name] = int(float(payout_str))
                except ValueError:
                    pass
        if payouts:
            logging.info("Loaded payouts from sheet: %s", payouts)
            return payouts
        logging.warning("Payouts tab found but no valid rows parsed")
    except Exception as e:
        logging.error("load_payouts error: %s", e, exc_info=True)
    return DEFAULT_PAYOUTS.copy()
