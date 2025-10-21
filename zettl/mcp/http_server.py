"""
HTTP API Server for Zettl MCP Tools

Provides a simple HTTP API that wraps the MCP tools.
Flask web app can call this service to execute tool operations.
"""

from flask import Flask, request, jsonify
import os
import logging
import requests

from zettl.mcp.tools import ZettlMCPTools
from zettl.mcp.auth import MCPAuthenticator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get JWT secret
JWT_SECRET_FILE = os.getenv('JWT_SECRET_FILE')
JWT_SECRET = None

if JWT_SECRET_FILE and os.path.exists(JWT_SECRET_FILE):
    with open(JWT_SECRET_FILE, 'r') as f:
        JWT_SECRET = f.read().strip()
else:
    JWT_SECRET = os.getenv('JWT_SECRET')

if not JWT_SECRET:
    raise ValueError("JWT_SECRET or JWT_SECRET_FILE must be set")

authenticator = MCPAuthenticator(JWT_SECRET)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/tools', methods=['GET'])
def list_tools():
    """List available MCP tools"""
    return jsonify({
        'tools': ZettlMCPTools.TOOL_DEFINITIONS
    }), 200


@app.route('/tool/<tool_name>', methods=['POST'])
def execute_tool(tool_name):
    """Execute a specific MCP tool"""
    try:
        # Get JWT token from Authorization header (for web app)
        # or API key from X-API-Key header (for CLI)
        jwt_token = None
        auth_header = request.headers.get('Authorization')
        api_key = request.headers.get('X-API-Key')

        if auth_header and auth_header.startswith('Bearer '):
            # Web app using JWT token
            jwt_token = auth_header.split(' ')[1]
        elif api_key:
            # CLI using API key - convert to JWT token
            try:
                auth_url = os.getenv('AUTH_URL', 'http://auth-service:3001')
                response = requests.post(f'{auth_url}/token-from-key',
                                       headers={'X-API-Key': api_key},
                                       timeout=5)
                if response.status_code == 200:
                    jwt_token = response.json().get('token')
                else:
                    return jsonify({'error': 'Invalid API key'}), 401
            except Exception as e:
                logger.error(f"Failed to convert API key to JWT: {e}")
                return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Missing Authorization header or X-API-Key'}), 401

        if not jwt_token:
            return jsonify({'error': 'Authentication failed'}), 401

        # Get tool arguments from request body
        args = request.json or {}

        # Initialize tools with JWT
        tools = ZettlMCPTools(jwt_token)

        # Execute the tool
        if not hasattr(tools, tool_name):
            return jsonify({'error': f'Unknown tool: {tool_name}'}), 404

        tool_method = getattr(tools, tool_name)
        result = tool_method(**args)

        return jsonify({
            'success': True,
            'result': result
        }), 200

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.getenv('MCP_PORT', 3002))
    app.run(host='0.0.0.0', port=port, debug=False)
