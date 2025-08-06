import os
import json
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self.SPREADSHEET_ID = '1XQYIg30NdAVbHHnq7SLXGs60Xuk2bTPSef20dtmDR5U'
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API using service account credentials."""
        try:
            # Get credentials file path
            creds_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'credentials.json')
            
            if not os.path.exists(creds_path):
                raise FileNotFoundError(f"Credentials file not found at {creds_path}")
            
            # Load credentials
            credentials = Credentials.from_service_account_file(
                creds_path, scopes=self.SCOPES
            )
            
            # Build the service
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Successfully authenticated with Google Sheets API")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets API: {str(e)}")
            raise
    
    def get_all_products(self):
        """Fetch all products from the Google Sheet."""
        try:
            # Get the sheet data from the Inventory sheet starting from row 5
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.SPREADSHEET_ID,
                range="'Inventory'!A5:Z"  # Start from row 5 where the real data begins
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning("No data found in the sheet")
                return []
            
            # Get headers from first row (row 5 of the sheet)
            headers = values[0] if values else []
            logger.info(f"Sheet headers: {headers}")
            
            # Convert rows to dictionaries
            products = []
            for i, row in enumerate(values[1:], start=6):  # Start from row 6 (data rows)
                if len(row) >= 4:  # Ensure we have at least company, name, alias, quantity
                    # Pad row with empty strings if needed
                    while len(row) < 26:  # Ensure we have enough columns
                        row.append('')
                    
                    # Create location from Rack and Level
                    rack = row[4] if len(row) > 4 else ''
                    level = row[5] if len(row) > 5 else ''
                    location = f"{rack}-{level}" if rack and level else (rack or level or '')
                    
                    product = {
                        'id': i,
                        'company': row[0] if len(row) > 0 else '',
                        'name': row[1] if len(row) > 1 else '',
                        'alias': row[2] if len(row) > 2 else '',
                        'quantity': self._safe_int(row[3]) if len(row) > 3 else 0,
                        'location': location,
                        'notes': row[6] if len(row) > 6 else '',
                        'photo_url': row[7] if len(row) > 7 else '',
                        'date_added': row[8] if len(row) > 8 else '2025-01-01',
                        'added_by': row[9] if len(row) > 9 else '',
                        'lastUpdated': row[8] if len(row) > 8 else '2025-01-01'  # Use date_added as lastUpdated
                    }
                    
                    # Clean up company name (CNS -> C&S)
                    if product['company'].upper() == 'CNS':
                        product['company'] = 'C&S'
                    
                    # Only add products with valid data
                    if product['company'] and product['name']:
                        products.append(product)
            
            logger.info(f"Successfully fetched {len(products)} products")
            return products
            
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return []
    
    def search_products(self, search_term):
        """Search for products by name, alias, or company."""
        all_products = self.get_all_products()
        
        if not search_term:
            return all_products
        
        search_term = search_term.lower()
        filtered_products = []
        
        for product in all_products:
            if (search_term in product['name'].lower() or
                search_term in product['alias'].lower() or
                search_term in product['company'].lower()):
                filtered_products.append(product)
        
        logger.info(f"Search for '{search_term}' returned {len(filtered_products)} results")
        return filtered_products
    
    def filter_by_company(self, company):
        """Filter products by company."""
        all_products = self.get_all_products()
        
        if not company or company.lower() == 'all':
            return all_products
        
        # Map frontend company names to sheet names
        company_map = {
            'cmes': 'CMES',
            'cs': 'C&S',
            'c&s': 'C&S',
            'srt': 'SRT'
        }
        
        target_company = company_map.get(company.lower(), company.upper())
        
        filtered_products = [
            product for product in all_products 
            if product['company'].upper() == target_company
        ]
        
        logger.info(f"Filter by company '{target_company}' returned {len(filtered_products)} results")
        return filtered_products
    
    def add_product(self, product_data):
        """Add a new product to the sheet."""
        try:
            # Prepare the row data according to Inventory sheet structure
            row_data = [
                product_data.get('company', ''),
                product_data.get('name', ''),
                product_data.get('alias', ''),
                product_data.get('quantity', 0),
                product_data.get('rack', ''),
                product_data.get('level', ''),
                product_data.get('notes', ''),
                product_data.get('photo_url', ''),
                product_data.get('date_added', '2025-01-01'),
                product_data.get('added_by', ''),
                '',  # Additional columns
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',  # AI Risk Score
                ''   # AI Reorder Suggestion
            ]
            
            # Append the row to Inventory sheet
            sheet = self.service.spreadsheets()
            result = sheet.values().append(
                spreadsheetId=self.SPREADSHEET_ID,
                range="'Inventory'!A:Z",
                valueInputOption='RAW',
                body={'values': [row_data]}
            ).execute()
            
            logger.info(f"Successfully added product: {product_data.get('name')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add product: {str(e)}")
            return False
    
    def update_product_quantity(self, product_id, new_quantity):
        """Update the quantity of a specific product."""
        try:
            # Calculate the row number (product_id is the row number)
            row_num = product_id
            range_name = f"'Inventory'!D{row_num}"  # Column D is quantity in Inventory sheet
            
            # Update the quantity
            sheet = self.service.spreadsheets()
            result = sheet.values().update(
                spreadsheetId=self.SPREADSHEET_ID,
                range=range_name,
                valueInputOption='RAW',
                body={'values': [[new_quantity]]}
            ).execute()
            
            logger.info(f"Successfully updated product {product_id} quantity to {new_quantity}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update product quantity: {str(e)}")
            return False
    
    def withdraw_product(self, product_id, withdraw_quantity):
        """Withdraw a specific quantity from a product."""
        try:
            # Get current product data
            products = self.get_all_products()
            product = next((p for p in products if p['id'] == product_id), None)
            
            if not product:
                logger.error(f"Product with ID {product_id} not found")
                return False
            
            current_quantity = product['quantity']
            if withdraw_quantity > current_quantity:
                logger.error(f"Cannot withdraw {withdraw_quantity} items. Only {current_quantity} available.")
                return False
            
            new_quantity = current_quantity - withdraw_quantity
            return self.update_product_quantity(product_id, new_quantity)
            
        except Exception as e:
            logger.error(f"Failed to withdraw product: {str(e)}")
            return False
    
    def get_kpi_data(self):
        """Get KPI data for the dashboard."""
        try:
            products = self.get_all_products()
            
            total_products = len(products)
            total_units = sum(product['quantity'] for product in products)
            low_stock_count = len([p for p in products if p['quantity'] < 10])
            active_companies = len(set(product['company'] for product in products if product['company']))
            
            return {
                'total_products': total_products,
                'total_units': total_units,
                'low_stock_alerts': low_stock_count,
                'active_companies': active_companies
            }
            
        except Exception as e:
            logger.error(f"Failed to get KPI data: {str(e)}")
            return {
                'total_products': 0,
                'total_units': 0,
                'low_stock_alerts': 0,
                'active_companies': 0
            }
    
    def _safe_int(self, value):
        """Safely convert a value to integer."""
        try:
            return int(float(value)) if value else 0
        except (ValueError, TypeError):
            return 0

# Global instance
sheets_service = GoogleSheetsService()

