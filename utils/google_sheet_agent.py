import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import logging

class GoogleSheetAgent:
    def __init__(self, credentials_path, sheet_id=None):
        self.logger = logging.getLogger('shopify_tracker')
        self.sheet_id = sheet_id
        self.credentials_path = credentials_path

        try:
            self.scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            self.creds = Credentials.from_service_account_file(credentials_path, scopes=self.scopes)
            self.client = gspread.authorize(self.creds)
            self.sheet = self.client.open_by_key(sheet_id).sheet1
            self.drive_service = build("drive", "v3", credentials=self.creds)
            self.logger.info("Connected to Google Sheet successfully.")
        except Exception as e:
            self.logger.error(f"Failed to connect to Google Sheet: {e}")
            self.sheet = None
            self.drive_service = None

    def append_data(self, df):
        """
        Appends or updates dataframe rows to Google Sheet.
        Updates existing row if date exists, otherwise appends.
        """
        if self.sheet is None:
            self.logger.error("No valid Google Sheet connection. Skipping upload.")
            return

        try:
            existing_data = self.sheet.get_all_values()
            headers = df.columns.tolist()
            new_row = df.values.tolist()[0]  # Get first row from dataframe
            
            # Add headers if sheet is empty
            if not existing_data:
                self.sheet.append_row(headers, value_input_option='USER_ENTERED')
                self.sheet.append_row(new_row, value_input_option='USER_ENTERED')
                self.logger.info("Headers + new row uploaded to Google Sheet.")
                return

            # Check if date exists and update
            date_to_find = new_row[0]  # Assuming first column is Date
            date_col_index = 0
            
            for i, row in enumerate(existing_data[1:], start=2):  # Skip header row
                if row and row[date_col_index] == date_to_find:
                    # Update existing row
                    for col_idx, value in enumerate(new_row):
                        self.sheet.update_cell(i, col_idx + 1, value)
                    self.logger.info(f"Updated existing row for date {date_to_find}")
                    return
            
            # If date not found, append new row
            self.sheet.append_row(new_row, value_input_option='USER_ENTERED')
            self.logger.info(f"Appended new row for date {date_to_find}")

        except Exception as e:
            self.logger.error(f"Failed to update Google Sheet: {e}")

    def share_with_users(self, emails, role="reader"):
        """
        Share the Google Sheet with a list of emails.
        role = 'reader' (view only) or 'writer' (edit access)
        """
        if not self.drive_service:
            self.logger.error("Drive service not initialized; cannot share file.")
            return

        for email in emails:
            try:
                permission = {
                    "type": "user",
                    "role": role,
                    "emailAddress": email
                }
                self.drive_service.permissions().create(
                    fileId=self.sheet_id,
                    body=permission,
                    fields="id"
                ).execute()
                self.logger.info(f"Shared sheet with {email} ({role}).")
            except Exception as e:
                self.logger.error(f"Failed to share with {email}: {e}")
