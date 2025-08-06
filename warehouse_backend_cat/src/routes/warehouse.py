from flask import Blueprint, request, jsonify
from src.models.sheets_service import sheets_service
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warehouse_bp = Blueprint('warehouse', __name__)

@warehouse_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Handle user authentication."""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # Simple authentication (in production, use proper password hashing)
        if (username == 'alonso.g' and password == 'Mery1978'):
            return jsonify({
                'success': True,
                'user': {
                    'username': username,
                    'role': 'admin'
                }
            })
        elif (username == 'CMES' and password == '12345'):
            return jsonify({
                'success': True,
                'user': {
                    'username': username,
                    'role': 'guest'
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Server error'
        }), 500

@warehouse_bp.route('/api/products', methods=['GET'])
def get_products():
    """Get all products or filtered products."""
    try:
        # Get query parameters
        search = request.args.get('search', '')
        company = request.args.get('company', '')
        
        if search:
            products = sheets_service.search_products(search)
        elif company and company != 'all':
            products = sheets_service.filter_by_company(company)
        else:
            products = sheets_service.get_all_products()
        
        return jsonify({
            'success': True,
            'products': products,
            'count': len(products)
        })
        
    except Exception as e:
        logger.error(f"Get products error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch products',
            'products': [],
            'count': 0
        }), 500

@warehouse_bp.route('/api/products/search', methods=['POST'])
def search_products():
    """Search for products."""
    try:
        data = request.get_json()
        search_term = data.get('search', '')
        
        products = sheets_service.search_products(search_term)
        
        return jsonify({
            'success': True,
            'products': products,
            'count': len(products)
        })
        
    except Exception as e:
        logger.error(f"Search products error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Search failed',
            'products': [],
            'count': 0
        }), 500

@warehouse_bp.route('/api/products/add', methods=['POST'])
def add_product():
    """Add a new product."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['company', 'name', 'quantity']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Prepare product data
        product_data = {
            'company': data.get('company'),
            'name': data.get('name'),
            'alias': data.get('alias', ''),
            'quantity': int(data.get('quantity', 0)),
            'location': data.get('location', ''),
            'lastUpdated': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Add to sheet
        success = sheets_service.add_product(product_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Product added successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to add product'
            }), 500
            
    except Exception as e:
        logger.error(f"Add product error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Server error'
        }), 500

@warehouse_bp.route('/api/products/<int:product_id>/withdraw', methods=['POST'])
def withdraw_product(product_id):
    """Withdraw quantity from a product."""
    try:
        data = request.get_json()
        withdraw_quantity = int(data.get('quantity', 0))
        reason = data.get('reason', '')
        recipient = data.get('recipient', '')
        signature = data.get('signature', '')
        
        if withdraw_quantity <= 0:
            return jsonify({
                'success': False,
                'message': 'Invalid withdrawal quantity'
            }), 400
        
        # Perform withdrawal
        success = sheets_service.withdraw_product(product_id, withdraw_quantity)
        
        if success:
            # Log the withdrawal (in production, save to a separate log sheet)
            logger.info(f"Product {product_id} withdrawal: {withdraw_quantity} units, reason: {reason}, recipient: {recipient}")
            
            return jsonify({
                'success': True,
                'message': f'Successfully withdrew {withdraw_quantity} units'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Withdrawal failed'
            }), 500
            
    except Exception as e:
        logger.error(f"Withdraw product error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Server error'
        }), 500

@warehouse_bp.route('/api/kpi', methods=['GET'])
def get_kpi_data():
    """Get KPI data for the dashboard."""
    try:
        kpi_data = sheets_service.get_kpi_data()
        
        return jsonify({
            'success': True,
            'data': kpi_data
        })
        
    except Exception as e:
        logger.error(f"Get KPI data error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch KPI data',
            'data': {
                'total_products': 0,
                'total_units': 0,
                'low_stock_alerts': 0,
                'active_companies': 0
            }
        }), 500

@warehouse_bp.route('/api/sync', methods=['POST'])
def sync_data():
    """Manually sync data with Google Sheets."""
    try:
        # Force refresh by getting fresh data
        products = sheets_service.get_all_products()
        kpi_data = sheets_service.get_kpi_data()
        
        return jsonify({
            'success': True,
            'message': 'Data synchronized successfully',
            'timestamp': datetime.now().isoformat(),
            'products_count': len(products)
        })
        
    except Exception as e:
        logger.error(f"Sync data error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Sync failed'
        }), 500

@warehouse_bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Test Google Sheets connection
        kpi_data = sheets_service.get_kpi_data()
        
        return jsonify({
            'success': True,
            'message': 'Service is healthy',
            'google_sheets_connected': True,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Service unhealthy',
            'google_sheets_connected': False,
            'error': str(e)
        }), 500

