# Flask Google Auth App with AI Chatbot

A Flask application with Google OAuth authentication, dashboard, and AI chatbot functionality.

## Features

- 🔐 Google OAuth 2.0 Authentication
- 📊 User Dashboard
- 🤖 AI Chatbot with Gemini API
- 👤 User Account Management
- 📸 Image Upload with Base64 Conversion
- 🐳 Docker Support

## Prerequisites

- Python 3.11+
- Google Cloud Console project with OAuth 2.0 credentials
- Docker (optional, for containerized deployment)

## Quick Start with Docker

### 1. Build and Run with Docker Compose

```bash
# Build and start the application
docker-compose up --build

# Run in background
docker-compose up -d --build
```

### 2. Build and Run with Docker

```bash
# Build the image
docker build -t flask-google-auth-app .

# Run the container
docker run -p 5000:5000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/client_secret.json:/app/client_secret.json:ro \
  flask-google-auth-app
```

## Local Development Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-name>
```

### 2. Set up virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Download the JSON file and save as `client_secret.json` in the project root

### 5. Run the application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Environment Variables

Create a `.env` file for production:

```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
OAUTHLIB_INSECURE_TRANSPORT=0
```

## API Endpoints

- `GET /` - Home page (redirects to login or chatbot)
- `GET /login` - Initiate Google OAuth flow
- `GET /auth` - OAuth callback handler
- `GET /dashboard` - User dashboard
- `GET /account` - User account page
- `GET /chatbot` - AI chatbot interface
- `POST /api/chat` - Chatbot API endpoint
- `POST /api/upload-image` - Image upload endpoint
- `GET /api/user` - Get current user info
- `GET /test-config` - Test configuration endpoint

## Project Structure

```
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose configuration
├── .dockerignore        # Docker ignore file
├── .gitignore          # Git ignore file
├── client_secret.json  # Google OAuth credentials
├── modules/
│   ├── chatbot.py      # Chatbot functionality
│   ├── llm.py          # LLM integration
│   └── image_handler.py # Image processing
├── templates/
│   ├── base.html       # Base template
│   ├── login.html      # Login page
│   ├── dashboard.html  # Dashboard page
│   ├── account.html    # Account page
│   └── chatbot.html    # Chatbot page
└── uploads/            # Uploaded images (created automatically)
```

## Docker Commands

### Development

```bash
# Start with hot reload
docker-compose up

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production

```bash
# Build production image
docker build -t flask-google-auth-app:prod .

# Run production container
docker run -d \
  --name flask-app-prod \
  -p 80:5000 \
  -e FLASK_ENV=production \
  -e SECRET_KEY=your-production-secret \
  -v /path/to/uploads:/app/uploads \
  -v /path/to/client_secret.json:/app/client_secret.json:ro \
  flask-google-auth-app:prod
```

## Security Notes

- Never commit `client_secret.json` to version control
- Use strong secret keys in production
- Enable HTTPS in production
- Set `OAUTHLIB_INSECURE_TRANSPORT=0` in production

## Troubleshooting

### Docker Issues

```bash
# Clean up Docker resources
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache

# Check container logs
docker-compose logs flask-app
```

### OAuth Issues

- Ensure `client_secret.json` is in the project root
- Verify redirect URIs in Google Cloud Console
- Check that Google+ API is enabled

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.