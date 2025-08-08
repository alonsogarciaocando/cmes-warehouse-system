# Configuración correcta del Google Sheet
SPREADSHEET_ID = "1XQYIg30NdAVbHHnq7SLXGs60Xuk2bTPSef20dtmDR5U"
SHEET_NAME = "Inventory"

# Mapeo de columnas (basado en tu Google Sheet)
COLUMNS = {
    'company': 0, # Columna A - Company
    'name': 1, # Columna B - Item Name  
    'alias': 2, # Columna C - Alias
    'quantity': 3, # Columna D - Quantity
    'rack': 4, # Columna E - Rack
    'level': 5 # Columna F - Level
}

# Fila donde empiezan los datos (después del encabezado)
DATA_START_ROW = 2