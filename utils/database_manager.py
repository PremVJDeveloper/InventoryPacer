import os
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv
import requests
from json.decoder import JSONDecodeError
import json

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        self.supabase = create_client(self.SUPABASE_URL, self.SUPABASE_KEY)
        self.table_name = "inventorypacer"

    def check_date_exists(self, date):
        """Check if a record with the given date already exists"""
        try:
            response = self.supabase.table(self.table_name)\
                .select("id, Date, rings, pendants, earrings, bracelets")\
                .filter("Date", "eq", str(date))\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]  # Return the existing record
            return None
        except Exception as e:
            print(f"❌ Error checking date existence: {e}")
            return None

    def insert_jewelry_data(self, jewelry_data):
        """Insert new jewelry data"""
        try:
            response = self.supabase.table(self.table_name).insert(jewelry_data).execute()
            print("✅ Data inserted successfully!")
            return True
        except Exception as e:
            print(f"❌ Error inserting data: {e}")
            return True

    def update_jewelry_data(self, record_id, counts):
        """Update existing jewelry data"""
        try:
            response = self.supabase.table(self.table_name)\
                .update(counts)\
                .filter("id", "eq", record_id)\
                .execute()
            
            print("✅ Data updated successfully!")
            return True
        except JSONDecodeError as e:
            print(f"JSON decode error during update: {e}")
            return True
        except Exception as e:
            print(f"❌ Error updating data: {e}")
            return False

    def upsert_product_counts(self, date, counts):
        """
        Upsert product counts - insert if date doesn't exist, update if counts are different
        
        Args:
            date (str): The date in format 'dd-mm-yyyy'
            counts (dict): Dictionary with product counts like {'rings': 5, 'pendants': 3, ...}
        """
        try:
            # Prepare the data for insertion/update
            jewelry_data = counts.copy()
            jewelry_data['Date'] = date
            
            # Check if date already exists
            existing_record = self.check_date_exists(date)
            
            if existing_record:
                # Date exists, check if counts are different
                needs_update = False
                update_data = {}
                
                for key, new_value in counts.items():
                    existing_value = existing_record.get(key.lower(), None)
                    # Convert both to string for comparison to handle different data types
                    if str(existing_value) != str(new_value):
                        needs_update = True
                        update_data[key] = new_value
                        print(f"{key}: {existing_value} → {new_value}")
                
                if needs_update:
                    print(f"🔄 Updating existing record for date {date}")
                    success = self.update_jewelry_data(existing_record['id'], update_data)
                    return success
                else:
                    print(f"✅ Data unchanged for date {date}, no update needed")
                    return True
                    
            else:
                # Date doesn't exist, insert new record
                print(f"🆕 Inserting new record for date {date}")
                success = self.insert_jewelry_data(jewelry_data)
                return success
                
        except Exception as e:
            print(f"❌ Error in upsert operation: {e}")
            return False
