import sqlite3
import logging
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="database/shopify_tracker.db"):
        self.db_path = db_path
        self.logger = logging.getLogger('shopify_tracker')
        self._init_database()

    def _init_database(self):
        """Initialize database and create table if not exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_counts (
                date TEXT PRIMARY KEY,
                rings INTEGER DEFAULT 0,
                pendants INTEGER DEFAULT 0,
                earrings INTEGER DEFAULT 0,
                bracelets INTEGER DEFAULT 0,
                necklaces INTEGER DEFAULT 0,
                total_products INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        self.logger.info("Database initialized successfully")

    def upsert_product_counts(self, date_str, counts):
        """Insert or update product counts for a specific date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Calculate total products
            total_products = sum(counts.values())
            
            cursor.execute('''
                INSERT INTO product_counts (date, rings, pendants, earrings, bracelets, necklaces, total_products, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    rings = excluded.rings,
                    pendants = excluded.pendants,
                    earrings = excluded.earrings,
                    bracelets = excluded.bracelets,
                    necklaces = excluded.necklaces,
                    total_products = excluded.total_products,
                    updated_at = excluded.updated_at
            ''', (
                date_str,
                counts.get('rings', 0),
                counts.get('pendants', 0),
                counts.get('earrings', 0),
                counts.get('bracelets', 0),
                counts.get('necklaces', 0),
                total_products,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            self.logger.info(f"Updated product counts for date {date_str}: {counts}")
            
        except Exception as e:
            self.logger.error(f"Error upserting product counts: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_product_counts(self, date_str):
        """Get product counts for a specific date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT rings, pendants, earrings, bracelets, necklaces, total_products 
            FROM product_counts WHERE date = ?
        ''', (date_str,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'Rings': result[0],
                'Pendant': result[1],
                'Earrings': result[2],
                'Bracelets': result[3],
                'Necklaces': result[4],
                'Total': result[5]
            }
        return None

    def get_all_counts(self):
        """Get all product counts for reporting"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT date, rings, pendants, earrings, bracelets, necklaces, total_products
            FROM product_counts ORDER BY date
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return results