import gspread
from google.oauth2.service_account import Credentials
import logging
from sheet_config import SPREADSHEET_ID, SHEET_NAME, COLUMNS, DATA_START_ROW

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self.spreadsheet_id = SPREADSHEET_ID
        self.sheet_name = SHEET_NAME
        self.columns = COLUMNS
        self.data_start_row = DATA_START_ROW
        self.client = None
        self.sheet = None
        self._authenticate()

    def _authenticate(self):
        try:
            # Configurar credenciales
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
            self.client = gspread.authorize(creds)
            
            # Abrir spreadsheet
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            self.sheet = spreadsheet.worksheet(self.sheet_name)
            
            logger.info("Successfully authenticated with Google Sheets API")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets API: {e}")
            raise

    def get_all_products(self):
        try:
            # Obtener todos los datos
            all_values = self.sheet.get_all_values()
            
            if len(all_values) <= self.data_start_row - 1:
                logger.warning("No data found in sheet")
                return []
            
            products = []
            
            # Procesar cada fila (empezando desde DATA_START_ROW)
            for i, row in enumerate(all_values[self.data_start_row - 1:], start=self.data_start_row):
                if len(row) > max(self.columns.values()):
                    try:
                        product = {
                            'id': i,
                            'company': row[self.columns['company']].strip() if len(row) > self.columns['company'] else '',
                            'name': row[self.columns['name']].strip() if len(row) > self.columns['name'] else '',
                            'alias': row[self.columns['alias']].strip() if len(row) > self.columns['alias'] else '',
                            'quantity': int(row[self.columns['quantity']]) if row[self.columns['quantity']].strip().isdigit() else 0,
                            'location': f"{row[self.columns['rack']]}-{row[self.columns['level']]}" if len(row) > self.columns['level'] else '',
                            'notes': '',
                            'date_added': '',
                            'added_by': ''
                        }
                        
                        # Solo agregar productos con nombre
                        if product['name']:
                            products.append(product)
                            
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error processing row {i}: {e}")
                        continue
            
            logger.info(f"Successfully loaded {len(products)} products from Google Sheets")
            return products
            
        except Exception as e:
            logger.error(f"Error getting products from Google Sheets: {e}")
            return []

    def search_products(self, search_term):
        products = self.get_all_products()
        if not search_term:
            return products
        
        search_term = search_term.lower()
        filtered_products = []
        
        for product in products:
            if (search_term in product['name'].lower() or 
                search_term in product['alias'].lower() or 
                search_term in product['company'].lower()):
                filtered_products.append(product)
        
        return filtered_products

    def add_product(self, product_data):
        try:
            # Encontrar la próxima fila vacía
            all_values = self.sheet.get_all_values()
            next_row = len(all_values) + 1
            
            # Preparar datos para insertar
            row_data = [''] * (max(self.columns.values()) + 1)
            row_data[self.columns['company']] = product_data.get('company', '')
            row_data[self.columns['name']] = product_data.get('name', '')
            row_data[self.columns['alias']] = product_data.get('alias', '')
            row_data[self.columns['quantity']] = str(product_data.get('quantity', 0))
            
            # Separar location en rack y level
            location = product_data.get('location', '1-1')
            if '-' in location:
                rack, level = location.split('-', 1)
                row_data[self.columns['rack']] = rack
                row_data[self.columns['level']] = level
            
            # Insertar fila
            self.sheet.insert_row(row_data, next_row)
            logger.info(f"Successfully added product: {product_data.get('name')}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            return False

    def update_product_quantity(self, product_id, new_quantity):
        try:
            # Actualizar cantidad en la fila correspondiente
            cell = self.sheet.cell(product_id, self.columns['quantity'] + 1)
            cell.value = str(new_quantity)
            self.sheet.update_cell(product_id, self.columns['quantity'] + 1, str(new_quantity))
            
            logger.info(f"Successfully updated product quantity: row {product_id}, new quantity: {new_quantity}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating product quantity: {e}")
            return False

# Crear instancia global
sheets_service = GoogleSheetsService()
