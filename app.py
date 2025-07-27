from flask import Flask, render_template, url_for, session, redirect, request, jsonify
import google_auth_oauthlib.flow
import google.auth.transport.requests
import google.oauth2.credentials
import requests as http_requests
from datetime import datetime
import json
import os
from modules.image_handler import SimpleImageHandler

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Session configuration for better reliability
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800  # 30 minutes
)

# OAuth 2 scopes
SCOPES = ['https://www.googleapis.com/auth/userinfo.email',
          'https://www.googleapis.com/auth/userinfo.profile',
          'openid']

# Load credentials - Updated with correct redirect URIs
CLIENT_SECRETS = {
    "web": {
        "client_id": "1011657499203-867g0oicr297kdrnqt7d29268708d4fb.apps.googleusercontent.com",
        "project_id": "graphite-record-467002-g2",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "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",
        "redirect_uris": [
            "https://agent-raseed-flask-app-1011657499203.asia-south1.run.app/auth/google",
            "https://agent-raseed-flask-app-1011657499203.asia-south1.run.app/auth/google/",
            "https://agent-raseed-flask-app-1011657499203.asia-south1.run.app/auth",
            "https://agent-raseed-flask-app-1011657499203.asia-south1.run.app/auth/",
            "http://agent-raseed-flask-app-1011657499203.asia-south1.run.app/auth/google",
            "http://agent-raseed-flask-app-1011657499203.asia-south1.run.app/auth/google/",
            "http://agent-raseed-flask-app-1011657499203.asia-south1.run.app/auth",
            "http://agent-raseed-flask-app-1011657499203.asia-south1.run.app/auth/",
            "http://localhost:8080/auth/google",
            "http://127.0.0.1:8080/auth/google"
        ],
        "javascript_origins": [
            "https://agent-raseed-flask-app-1011657499203.asia-south1.run.app",
            "http://agent-raseed-flask-app-1011657499203.asia-south1.run.app",
            "http://localhost:8080",
            "http://127.0.0.1:8080"
        ]
    }
}

# Only exit if we're in a production environment and have no credentials
if CLIENT_SECRETS is None:
    if os.environ.get('FLASK_ENV') != 'development':
        print("❌ No OAuth credentials found in production environment!")
        print("Please set the GOOGLE_CLIENT_SECRETS environment variable")
        # Don't exit immediately - let the app start but warn about missing credentials
    else:
        print("⚠️ Running in development mode without credentials")


def create_flow():
    """Create a Google OAuth flow"""
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        CLIENT_SECRETS,
        scopes=SCOPES
    )
    flow.redirect_uri = url_for('oauth_callback', _external=True)
    print(f"DEBUG: Flask generated redirect URI: {flow.redirect_uri}")
    return flow

@app.route('/')
def index():
    if 'user' in session:
        # If logged in, redirect to the chatbot page
        return redirect(url_for('chatbot_page'))
    return render_template('login.html')

@app.route('/login')
def login():
    """Initiate the OAuth flow"""
    try:
        # Clear any existing session data
        session.pop('state', None)
        session.pop('user', None)
        session.pop('credentials', None)
        
        flow = create_flow()
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        # Store state in session and make session permanent
        session['state'] = state
        session.permanent = True
        
        print(f"DEBUG: Generated state: {state}")
        print(f"DEBUG: Authorization URL: {authorization_url}")
        print(f"DEBUG: Session before redirect: {dict(session)}")
        
        return redirect(authorization_url)
    except Exception as e:
        print(f"Error in login route: {e}")
        return f"Login error: {str(e)}", 500

@app.route('/auth/google')
def oauth_callback():
    """Handle the OAuth callback"""
    try:
        print(f"DEBUG: Received callback request: {request.url}")
        print(f"DEBUG: Session contents: {dict(session)}")
        print(f"DEBUG: Request args: {dict(request.args)}")
        
        # Check if there's an error in the callback
        if 'error' in request.args:
            error = request.args.get('error')
            error_description = request.args.get('error_description', '')
            print(f"OAuth error: {error} - {error_description}")
            return f"Authentication failed: {error} - {error_description}", 400
        
        # Get state from session
        stored_state = session.get('state')
        received_state = request.args.get('state')
        
        print(f"DEBUG: Stored state: {stored_state}")
        print(f"DEBUG: Received state: {received_state}")
        
        if not stored_state:
            print("ERROR: No state found in session during OAuth callback.")
            # Try to redirect back to login to restart the flow
            return redirect(url_for('login'))
        
        if stored_state != received_state:
            print(f"ERROR: State mismatch. Stored: {stored_state}, Received: {received_state}")
            return "Authentication failed: State parameter mismatch.", 400
        
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            CLIENT_SECRETS,
            scopes=SCOPES,
            state=stored_state
        )
        flow.redirect_uri = url_for('oauth_callback', _external=True)
        
        authorization_response = request.url
        print(f"DEBUG: Authorization response URL: {authorization_response}")
        
        flow.fetch_token(authorization_response=authorization_response)
        
        credentials = flow.credentials
        
        # Get user info from Google
        user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {credentials.token}'}
        
        response = http_requests.get(user_info_url, headers=headers)
        user_info = response.json()
        
        print(f"DEBUG: User info response: {user_info}")
        
        if response.status_code == 200 and user_info.get('verified_email', False):
            session['user'] = {
                'id': user_info['id'],
                'email': user_info['email'],
                'name': user_info['name'],
                'picture': user_info.get('picture', ''),
                'login_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'locale': user_info.get('locale', 'en')
            }
            
            session['credentials'] = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            print(f"✅ User successfully authenticated: {user_info['email']}")
            
            # Clear the state after successful authentication
            session.pop('state', None)
            
            # Redirect to the chatbot page after successful login
            return redirect(url_for('chatbot_page'))
        else:
            print(f"User verification failed: {user_info}")
            return "User email not verified by Google.", 400
            
    except Exception as e:
        print(f"OAuth callback error: {e}")
        import traceback
        traceback.print_exc()
        return f"Authentication failed: {str(e)}", 500

@app.route('/chatbot')
def chatbot_page():
    """Main chatbot page after login."""
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('chatbot.html', user=session['user'], active_page='chatbot')

@app.route('/dashboard')
def dashboard():
    """Dashboard page."""
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html', user=session['user'], active_page='dashboard')

@app.route('/account')
def account():
    """Account details page."""
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('account.html', user=session['user'], active_page='account')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    # Clear the session
    session.pop('user', None)
    session.pop('credentials', None)
    session.pop('state', None)
    print("✅ User logged out successfully")
    return redirect(url_for('index'))

@app.route('/api/user')
def api_user():
    """Get current user info"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify(session['user'])

@app.route('/api/refresh-token')
def refresh_token():
    """Refresh the access token if needed"""
    if 'credentials' not in session:
        return jsonify({'error': 'No credentials found'}), 401
    
    try:
        credentials = google.oauth2.credentials.Credentials(
            **session['credentials']
        )
        
        request_obj = google.auth.transport.requests.Request()
        credentials.refresh(request_obj)
        
        session['credentials']['token'] = credentials.token
        
        return jsonify({'message': 'Token refreshed successfully'})
    except Exception as e:
        print(f"Token refresh error: {e}")
        return jsonify({'error': f'Token refresh failed: {str(e)}'}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint to handle chatbot requests and interact with Gemini API."""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        from modules.chatbot import graph

        result = graph.invoke({"messages": [user_message]})

        if result.get("messages"):
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                bot_response = last_message.content
                print(f"🤖 Assistant: {last_message.content}")
                return jsonify({'reply': bot_response})  
        else:
            print(f"Unexpected Gemini API response structure: {result}")
            return jsonify({'error': 'Could not get a valid response from the chatbot model.'}), 500

    except http_requests.exceptions.RequestException as req_err:
        print(f"HTTP Request error to Gemini API: {req_err}")
        return jsonify({'error': f'Failed to connect to chatbot service: {str(req_err)}'}), 500
    except Exception as e:
        print(f"An unexpected error occurred in chat endpoint: {e}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    """Handle image upload and return GCS URL as confirmation"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Call SimpleImageHandler to upload the image to GCS
        result = SimpleImageHandler.upload_image(file)
        
        if result['success']:
            print(f"📸 Image uploaded successfully to GCS! URL: {result['url']}")
            return jsonify({
                'success': True,
                'message': result['message'],
                'gcs_url': result['url']
            })
        else:
            print(f"❌ Image upload to GCS failed: {result['message']}")
            return jsonify({
                'success': False, 
                'error': result['message']
            }), 500
        
    except Exception as e:
        import traceback
        print(f"❌ Critical error in upload_image route: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False, 
            'error': f'An unexpected server error occurred: {str(e)}'
        }), 500
        
          
# Add route to manually test session
@app.route('/debug-session')
def debug_session():
    """Debug endpoint to check session contents"""
    return jsonify({
        'session_contents': dict(session),
        'has_state': 'state' in session,
        'state_value': session.get('state'),
        'session_id': request.cookies.get('session')
    })

@app.route('/test-config')
def test_config():
    """Test endpoint to verify configuration"""
    if CLIENT_SECRETS:
        client_info = CLIENT_SECRETS.get('web', {})
        return jsonify({
            'status': 'success',
            'client_id': client_info.get('client_id', '')[:20] + '...',
            'redirect_uris': client_info.get('redirect_uris', []),
            'scopes': SCOPES,
            'current_redirect_uri': url_for('oauth_callback', _external=True)
        })
    else:
        return jsonify({'status': 'error', 'message': 'No client secrets loaded'})

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return "Page not found", 404

@app.errorhandler(500)
def internal_error(error):
    return "Internal server error", 500

if __name__ == '__main__':
    # Cloud Run provides the PORT environment variable
    port = int(os.environ.get('PORT', 8080))  
    host = '0.0.0.0'

    # Allow insecure transport for local development
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    print(f"🚀 Starting Flask app on {host}:{port}")
    
    if CLIENT_SECRETS:
        client_info = CLIENT_SECRETS.get('web', {})
        print(f"✅ Google OAuth credentials loaded successfully")
        print(f"🔑 Client ID: {client_info.get('client_id', '')[:20]}...")
        print(f"🔄 Redirect URIs: {client_info.get('redirect_uris', [])}")
    else:
        print("⚠️ CLIENT_SECRETS not found - OAuth may not work")

    # Remove debug=True for production
    app.run(host=host, port=port, debug=False)