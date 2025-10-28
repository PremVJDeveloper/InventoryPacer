import os
import json
import logging
from datetime import datetime
import requests
import pandas as pd
from dotenv import load_dotenv
from utils.GetLogger import GetLogger
from utils.mail_agent import Mailer
from utils.google_sheet_agent import GoogleSheetAgent
from utils.database_manager import DatabaseManager
from utils.ratio_calculator import RatioCalculator


load_dotenv()


class ShopifyProductTracker:
    def __init__(self, config_path=r"config/config.json"):
        self.config = self._load_config(config_path)
        self.shopify_store = os.getenv("SHOPIFY_STORE")
        self.access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
        self.date_str = self.config.get("DATE")
        self.current_date = datetime.now().date().strftime("%d-%m-%Y")
        self.share_with = self.config.get("SHARE_WITH", [])
        self.target_ratios = self.config.get("TARGET_RATIOS", {
            "rings": 40, "pendants": 25, "earrings": 20, "bracelets": 15
        })

        self.logger = GetLogger(
            log_file_dir="logs", 
            log_file_name="shopify_tracker.log", 
            file_handler=True, 
            logger_name='shopify_tracker'
        ).logger
        
        # Initialize components
        # self.db_manager = DatabaseManager()
        self.ratio_calculator = RatioCalculator(self.target_ratios)
        credentials_path = os.path.join(os.getcwd(), "config", "google_service_account.json")
        self.google_sheet_id = os.getenv("GOOGLE_SHEET_ID", "1iGiZ7PHUWUwnR8LJStyTQpoq1q6eQVd-cPiTlzKWfLg")
        self.google_agent = GoogleSheetAgent(
            credentials_path=credentials_path,
            sheet_id=self.google_sheet_id
        )
        self.mailer = Mailer(
            sender=os.getenv("MAIL_SENDER", "developer@vaama.co"),
            password=os.getenv("MAIL_PASSWORD"),
            receiver=os.getenv("MAIL_RECEIVER", "developer@vaama.co"),
            cc_ids=os.getenv("MAIL_CC", "developer@vaama.co")
        )

        if not all([self.shopify_store, self.access_token, self.date_str]):
            self.logger.error("Missing SHOPIFY_STORE, ACCESS_TOKEN, or DATE in config.json.")
            raise ValueError("Invalid configuration file.")

        try:
            self.target_date = datetime.strptime(self.date_str, "%d-%m-%Y").date()
        except ValueError:
            self.logger.error("Date in config.json must be in DD-MM-YYYY format.")
            raise

    def _load_config(self, config_path):
        if not os.path.exists(config_path):
            self.logger.error(f"Configuration file not found: {config_path}")
            raise FileNotFoundError(f"Missing {config_path}")
        with open(config_path, "r") as f:
            return json.load(f)

    def get_products(self):
        """
        Fetch products from Shopify based on mode:
        - BY_DATE: Fetch all products created on target date
        - ACTIVE_ONLY: Fetch all active products
        - ACTIVE_BY_DATE: Fetch active products created on target date
        """
        mode = self.config.get("FETCH_MODE", "BY_DATE").upper()
        base_url = f"https://{self.shopify_store}/admin/api/2024-10/products.json"
        headers = {"X-Shopify-Access-Token": self.access_token}

        params = {"limit": 250}

        # Apply filters based on mode
        if mode in ["BY_DATE", "ACTIVE_BY_DATE"]:
            start_time = datetime.combine(self.target_date, datetime.min.time()).isoformat() + "Z"
            end_time = datetime.combine(self.target_date, datetime.max.time()).isoformat() + "Z"
            params.update({
                "created_at_min": start_time,
                "created_at_max": end_time
            })

        if mode in ["ACTIVE_ONLY", "ACTIVE_BY_DATE"]:
            params["status"] = "active"

        self.logger.info(f"Fetching products using mode: {mode}")
        all_products = []

        while True:
            response = requests.get(base_url, headers=headers, params=params)
            if response.status_code == 401:
                self.logger.error("Unauthorized: Invalid or expired Shopify access token.")
                raise PermissionError("Unauthorized Shopify API access.")
            response.raise_for_status()

            products = response.json().get("products", [])
            all_products.extend(products)

            # Handle pagination
            if 'link' in response.headers and 'rel="next"' in response.headers['link']:
                next_url = response.headers['link'].split(';')[0].strip('<>')
                base_url = next_url
                params = {}
            else:
                break

        # Filter for published/active if needed (extra safety)
        if mode in ["ACTIVE_ONLY", "ACTIVE_BY_DATE"]:
            active_products = [
                p for p in all_products
                if p.get("status") == "active" or p.get("published_at") is not None
            ]
            self.logger.info(f"Fetched {len(active_products)} active products out of {len(all_products)} total.")
            return active_products

        self.logger.info(f"Fetched {len(all_products)} total products.")
        return all_products

    def summarize_and_export(self, products):
        product_types = ["Pendants", "Rings", "Earrings", "Bracelets"]
        counts = {ptype.lower(): 0 for ptype in product_types}
        
        for p in products:
            ptype = p.get("product_type", "").lower().strip()
            if ptype in counts:
                counts[ptype] += 1

        # Update database
        import pdb;pdb.set_trace()  
        db_manager = DatabaseManager()
        success = db_manager.upsert_product_counts(self.current_date, counts)
        if not success:
            self.logger.error("Failed to upsert product counts to database.")
            return None
        data = {"Date": self.current_date, **counts}
        df_row = pd.DataFrame([data])

        # Save to Excel
        folder_path = os.path.join("reports", self.date_str)
        os.makedirs(folder_path, exist_ok=True)
        timestamp = datetime.now().strftime("%H-%M-%S")
        excel_path = os.path.join(folder_path, f"shopify_products_{self.date_str}_{timestamp}.xlsx")
        df_row.to_excel(excel_path, index=False)
        self.logger.info(f"Excel file saved: {excel_path}")
        # self.google_agent.append_data(df_row)
        # if self.share_with:
        #     self.google_agent.share_with_users(self.share_with, role="reader")
        #     self.logger.info(f"Shared sheet with configured users: {self.share_with}")

        self._check_ratio_and_alert(counts)

        return excel_path

    def _check_ratio_and_alert(self, counts):
        """
        Enhanced ratio checking with recommendations
        Filters out overrepresented (negative difference) product types.
        """
        self.logger.info(f"Checking product ratio for: {counts}")
        
        total_products = sum(counts.values())
        if total_products == 0:
            self.logger.error("No products uploaded, skipping ratio check.")
            return

        # Perform ratio analysis
        analysis = self.ratio_calculator.calculate_required_uploads(counts)
        
        if 'error' in analysis:
            self.logger.error(analysis['error'])
            return
        
        # Check ratio balance
        is_balanced = self.ratio_calculator.is_ratio_balanced(analysis)
        
        if not is_balanced:
            recommendations = self.ratio_calculator.get_recommendations(analysis)
            
            # Prepare summary data — only include rows where Difference > 0
            summary_data = []
            for product_type, data in analysis.items():
                diff_value = data.get('adjusted_difference', data['next_upload_count'])
                if diff_value > 0:  # ✅ include only underrepresented categories
                    summary_data.append({
                        'Product Type': product_type,
                        'Current Count': data['current'],
                        'Current %': f"{data['current_percent']:.1f}%",
                        'Target %': f"{data['target_percent']:.1f}%",
                        'Required Count': f"{data['required']:.1f}",
                        'Next Upload Count': f"{diff_value:+.1f}"
                    })
            
            if not summary_data:
                self.logger.info("All product ratios are balanced or above target — no alert needed.")
                return
            
            import pandas as pd
            df_summary = pd.DataFrame(summary_data)
            
            # Build email content
            subject = f"Shopify Ratio Alert for {self.date_str}"
            body = (
                f"The uploaded product ratios deviate from the target ratios.\n\n"
                f"Total Products: {total_products}\n\n"
                f"Recommendations:\n" + "\n".join(f"• {rec}" for rec in recommendations) + 
                f"\n\nPlease review the detailed summary below:"
            )
            
            # Send alert email
            self.mailer.send_alert(subject, body, df_summary)
            self.logger.info(" Alert email triggered due to ratio deviation.")
        else:
            self.logger.info(" Product ratio within expected range.")


if __name__ == "__main__":
    tracker = ShopifyProductTracker()
    products = tracker.get_products()
    tracker.summarize_and_export(products)
    tracker.logger.info("Process completed successfully.")
