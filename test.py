import os
import logging
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import traceback

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Load Environment Variables ---
load_dotenv()

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "config/google_service_account.json")

if not GOOGLE_SHEET_ID:
    logging.error("❌ GOOGLE_SHEET_ID not found in .env file.")
    exit(1)

if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
    logging.error(f"❌ Google credentials file not found at {GOOGLE_CREDENTIALS_PATH}")
    exit(1)

try:
    # --- Authenticate using service account ---
    logging.info("🔑 Loading Google Service Account credentials...")
    creds = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )

    gc = gspread.authorize(creds)

    # --- Test sheet access ---
    logging.info("📊 Connecting to Google Sheet...")
    sheet = gc.open_by_key(GOOGLE_SHEET_ID)
    worksheet = sheet.sheet1

    # --- Try appending test data ---
    logging.info("➕ Appending test row...")
    worksheet.append_row(["Connection successful", "This row was added by API test"])
    logging.info("✅ Successfully appended test row to sheet.")
    print("\n🎉 Google Sheet connection test passed successfully!")

except gspread.exceptions.APIError as e:
    logging.error(f"❌ API Error: {e}")
    logging.error(f"📋 Full error details: {e.response.text if hasattr(e, 'response') else 'No response details'}")
except gspread.exceptions.SpreadsheetNotFound:
    logging.error("❌ The Google Sheet ID is invalid or not shared with the service account.")
except Exception as e:
    logging.error(f"❌ Unexpected error: {e}")
    logging.error(f"🔍 Full traceback:\n{traceback.format_exc()}")