import os

# Configuration file for BookCreatorAI
# Replace with your actual Gemini API key from https://makersuite.google.com/app/apikey

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Database configuration
SQLALCHEMY_DATABASE_URI = 'sqlite:///database/books.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Secret key for Flask sessions
SECRET_KEY = 'your-secret-key-change-in-production'
