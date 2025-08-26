from flask import Flask, render_template
import os
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import get_config
from src.api.routes import create_api_blueprint
from src.utils import setup_logger

# Initialize Flask app
app = Flask(__name__)

# Load configuration
config = get_config()
app.config['SECRET_KEY'] = config.secret_key or 'dev-secret-key'

# Setup logging
logger = setup_logger('JIRA_CSV_App', 'INFO' if not config.debug else 'DEBUG')

# Register API blueprint
api_blueprint = create_api_blueprint()
app.register_blueprint(api_blueprint)

@app.route('/')
def index():
    """Main web interface route."""
    return render_template('index.html')

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    logger.warning(f"404 error: {error}")
    return {'error': 'Not found'}, 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"500 error: {error}")
    return {'error': 'Internal server error'}, 500

if __name__ == '__main__':
    app.run(debug=True)