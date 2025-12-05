"""
Vercel serverless function entry point for FastAPI
Using BaseHTTPRequestHandler wrapper to satisfy Vercel's handler detection

This wrapper class satisfies Vercel's issubclass() check while routing
requests to the FastAPI ASGI application.
"""

import sys
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler
import asyncio

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the FastAPI app
from app.main import app

# Create handler class that Vercel can detect
# This satisfies: issubclass(handler, BaseHTTPRequestHandler) == True
class handler(BaseHTTPRequestHandler):
    """
    Wrapper class that inherits from BaseHTTPRequestHandler.
    This satisfies Vercel's handler detection while routing to FastAPI.
    """
    
    def do_GET(self):
        self._handle_request()
    
    def do_POST(self):
        self._handle_request()
    
    def do_PUT(self):
        self._handle_request()
    
    def do_DELETE(self):
        self._handle_request()
    
    def do_PATCH(self):
        self._handle_request()
    
    def do_OPTIONS(self):
        self._handle_request()
    
    def _handle_request(self):
        """Route request to FastAPI ASGI app"""
        try:
            # Extract request details
            path = self.path.split('?')[0]
            method = self.command
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b''
            
            # Build ASGI scope
            query_string = self.path.split('?')[1].encode() if '?' in self.path else b''
            headers = [[k.encode('utf-8'), v.encode('utf-8')] for k, v in self.headers.items()]
            
            # Get client address (with fallback)
            try:
                client_addr = [self.client_address[0], self.client_address[1]]
            except:
                client_addr = ['127.0.0.1', 0]
            
            scope = {
                'type': 'http',
                'method': method,
                'path': path,
                'query_string': query_string,
                'headers': headers,
                'client': client_addr,
                'server': ['0.0.0.0', 0],
            }
            
            # Response storage
            response_status = 200
            response_headers = []
            response_body = b''
            
            # ASGI receive function
            async def receive():
                return {
                    'type': 'http.request',
                    'body': body,
                    'more_body': False,
                }
            
            # ASGI send function
            async def send(message):
                nonlocal response_status, response_headers, response_body
                if message['type'] == 'http.response.start':
                    response_status = message['status']
                    response_headers = message['headers']
                elif message['type'] == 'http.response.body':
                    response_body = message.get('body', b'')
            
            # Run ASGI app
            try:
                # Get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Execute ASGI application
                loop.run_until_complete(app(scope, receive, send))
            except Exception as async_error:
                # Fallback on async error
                response_status = 500
                response_body = json.dumps({
                    'error': str(async_error),
                    'type': type(async_error).__name__
                }).encode()
                response_headers = [[b'content-type', b'application/json']]
            
            # Send HTTP response
            self.send_response(response_status)
            
            # Set response headers
            for header_name, header_value in response_headers:
                try:
                    name = header_name.decode('utf-8') if isinstance(header_name, bytes) else header_name
                    value = header_value.decode('utf-8') if isinstance(header_value, bytes) else header_value
                    self.send_header(name, value)
                except Exception:
                    continue
            
            self.end_headers()
            
            # Send response body
            if response_body:
                self.wfile.write(response_body)
                
        except Exception as e:
            # Error handling fallback
            try:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = json.dumps({
                    'error': str(e),
                    'type': type(e).__name__
                }).encode()
                self.wfile.write(error_response)
            except:
                # If even error handling fails, do nothing
                pass
    
    def log_message(self, format, *args):
        """Override to prevent default HTTP server logging"""
        pass
