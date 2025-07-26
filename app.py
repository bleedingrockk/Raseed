from flask import Flask, render_template, url_for, session, redirect, request, jsonify
import google_auth_oauthlib.flow
import google.auth.transport.requests
import requests as http_requests
from datetime import datetime
import json
import os
from modules.image_handler import ImageHandler

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# OAuth 2 scopes
SCOPES = ['https://www.googleapis.com/auth/userinfo.email',
          'https://www.googleapis.com/auth/userinfo.profile',
          'openid']

def load_client_secrets():
    """Load client secrets from JSON file"""
    try:
        with open('client_secret.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ client_secret.json file not found!")
        print("Please download the OAuth 2.0 credentials JSON from Google Cloud Console")
        return None
    except json.JSONDecodeError:
        print("❌ Invalid JSON format in client_secret.json")
        return None

# Load client secrets
CLIENT_SECRETS = load_client_secrets()
if not CLIENT_SECRETS:
    exit(1)

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
    flow = create_flow()
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    session['state'] = state
    
    return redirect(authorization_url)

@app.route('/auth')
def oauth_callback():
    """Handle the OAuth callback"""
    try:
        state = session.get('state')
        if not state:
            print("ERROR: State not found in session during OAuth callback.")
            return redirect(url_for('index'))
        
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            CLIENT_SECRETS,
            scopes=SCOPES,
            state=state
        )
        flow.redirect_uri = url_for('oauth_callback', _external=True)
        
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)
        
        credentials = flow.credentials
        
        user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {credentials.token}'}
        
        response = http_requests.get(user_info_url, headers=headers)
        user_info = response.json()
        
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
            
            # Redirect to the chatbot page after successful login
            return redirect(url_for('chatbot_page'))
        else:
            print(f"User verification failed: {user_info}")
            return "User email not verified by Google.", 400
            
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return redirect(url_for('index'))

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
    # Clear the session
    session.pop('user', None)
    session.pop('credentials', None)
    session.pop('state', None)
    return redirect(url_for('index'))

@app.route('/api/user')
def api_user():
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
        
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        
        session['credentials']['token'] = credentials.token
        
        return jsonify({'message': 'Token refreshed successfully'})
    except Exception as e:
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
    """Handle image upload and convert to base64"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Check if image file is present
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Save the image using ImageHandler
        file_path = ImageHandler.save_image(file)
        if not file_path:
            return jsonify({'success': False, 'error': 'Invalid file type or upload failed'}), 400
        
        # Get image info including base64 data
        image_info = ImageHandler.get_image_info(file_path)
        if not image_info:
            return jsonify({'success': False, 'error': 'Failed to process image'}), 500
        
        # Print base64 data to console (for debugging)
        print(f"📸 Image uploaded successfully!")
        print(f"📁 File: {image_info['filename']}")
        print(f"📏 Size: {image_info['file_size']} bytes")
        print(f"🔗 Extension: {image_info['file_extension']}")
        print(f"🔢 Base64 (first 100 chars): {image_info['base64_data'][:100]}...")
        
        return jsonify({
            'success': True,
            'message': 'Image uploaded and converted to base64 successfully',
            'filename': image_info['filename'],
            'file_size': image_info['file_size'],
            'file_extension': image_info['file_extension'],
            'base64_data': image_info['base64_data']
        })
        
    except Exception as e:
        print(f"❌ Error in upload_image: {e}")
        return jsonify({'success': False, 'error': f'Upload failed: {str(e)}'}), 500

@app.route('/test-config')
def test_config():
    """Test endpoint to verify configuration"""
    if CLIENT_SECRETS:
        client_info = CLIENT_SECRETS.get('web', {})
        return jsonify({
            'status': 'success',
            'client_id': client_info.get('client_id', '')[:20] + '...',
            'redirect_uris': client_info.get('redirect_uris', []),
            'scopes': SCOPES
        })
    else:
        return jsonify({'status': 'error', 'message': 'No client secrets loaded'})

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    print("🚀 Starting Flask Google Auth App with Google Auth Libraries...")
    print(f"📁 Looking for client_secret.json in: {os.getcwd()}")
    
    if CLIENT_SECRETS:
        client_info = CLIENT_SECRETS.get('web', {})
        print(f"✅ Google OAuth credentials loaded successfully")
        print(f"🔑 Client ID: {client_info.get('client_id', '')[:20]}...")
        print(f"🔄 Redirect URIs: {client_info.get('redirect_uris', [])}")
        print(f"🔐 Scopes: {SCOPES}")
    
    app.run(debug=True, port=5000)
