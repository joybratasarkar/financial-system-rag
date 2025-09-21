# Deployment Guide - Financial Q&A System

## Overview
This guide explains how to deploy the Financial Q&A System to cloud platforms like Render, Heroku, or Railway.

## 🚀 Quick Deploy to Render

### 1. Repository Setup
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

### 2. Render Configuration
1. **Connect Repository**: Link your GitHub repository to Render
2. **Service Type**: Web Service
3. **Environment**: Python
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `python main.py`

### 3. Environment Variables
Add these environment variables in Render dashboard:

#### Required:
```bash
PYTHONPATH=/opt/render/project/src:/opt/render/project/src/api:/opt/render/project/src/core:/opt/render/project/src/models
UVICORN_HOST=0.0.0.0
UVICORN_PORT=10000
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

#### Google Cloud Credentials:
```bash
GOOGLE_CLOUD_PROJECT=xooper-450012
GOOGLE_CLOUD_LOCATION=us-central1
```

#### Secret Files (Recommended for Render):
1. **In Render Dashboard** → **Environment** → **Secret Files**
2. **Add Secret File**:
   - **Filename**: `xooper.json`
   - **Contents**: Paste your Google Cloud service account JSON file content
3. **Save** - Render will mount this at `/etc/secrets/xooper.json`

**✅ Automatic Detection**: The system automatically detects and uses:
- **Local Development**: `./xooper.json` (in .gitignore)
- **Render Deployment**: `/etc/secrets/xooper.json` (Secret Files)
- **Other Platforms**: `GOOGLE_APPLICATION_CREDENTIALS` environment variable

### 4. Alternative: Use render.yaml
The project includes `render.yaml` for automatic deployment:
1. Push to GitHub
2. In Render dashboard, select "New → Web Service"
3. Choose "Deploy from Git"
4. Select your repository
5. Render will automatically detect and use `render.yaml`

## 🔧 Troubleshooting

### Import Path Issues
The system includes multiple layers of import path resolution:
- **Environment Level**: PYTHONPATH environment variable
- **Application Level**: Explicit sys.path setup in main.py
- **Module Level**: Fallback paths in all modules
- **Package Level**: Proper __init__.py structure

### Common Issues:

#### 1. "ModuleNotFoundError: No module named 'models'"
**Fixed by**: Comprehensive import path setup in all files

#### 2. Google Cloud Authentication
**Local Development**: Uses `xooper.json` file
**Deployment**: Uses `GOOGLE_APPLICATION_CREDENTIALS` environment variable

#### 3. Port Binding
**Fixed by**:
- `UVICORN_HOST=0.0.0.0`
- `UVICORN_PORT=10000`
- Health check endpoint: `/api/v1/health`

## 📊 Verification

### Health Check
```bash
curl https://your-app.onrender.com/api/v1/health
```
Expected response:
```json
{"status":"healthy","message":"Financial Q&A System is running"}
```

### API Test
```bash
curl -X POST https://your-app.onrender.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What was Microsoft'\''s revenue in 2023?"}'
```

## 🌐 Alternative Platforms

### Heroku
1. Use `Procfile`: `web: python main.py`
2. Set environment variables in Heroku dashboard
3. Deploy via Git: `git push heroku main`

### Railway
1. Connect GitHub repository
2. Railway auto-detects Python app
3. Set environment variables in Railway dashboard
4. Deploy automatically on push

## 🔒 Security Notes

- `xooper.json` is excluded from version control (in .gitignore)
- Use environment variables for all secrets in production
- Google Cloud credentials should be stored as secret environment variables
- Never commit API keys or service account files

## 📁 File Structure for Deployment
```
financial-qa-system/
├── main.py                 # FastAPI app with robust import paths
├── api/routes.py           # API endpoints with fallback imports
├── core/                   # Core modules with path setup
├── models/schemas.py       # Pydantic models
├── requirements.txt        # Python dependencies
├── render.yaml            # Render deployment config
├── Dockerfile             # Container deployment
├── .gitignore             # Excludes secrets and local files
└── __init__.py            # Package structure
```

## ✅ Deployment Checklist

- [ ] Repository pushed to GitHub
- [ ] Environment variables configured
- [ ] Google Cloud credentials added as secrets
- [ ] Health endpoint responds correctly
- [ ] API endpoints functional
- [ ] Vector store data accessible
- [ ] LLM integration working

The system is now production-ready with comprehensive error handling and deployment compatibility! 🚀