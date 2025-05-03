import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # Add basedir as a class attribute
    basedir = basedir

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-hard-to-guess-string'
    # Disable CSRF protection for testing
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'solapp.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # Ensure upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Readiness Score Weights (Example - make these configurable in UI later?)
    READINESS_WEIGHTS = {
        'sleep': 0.2,
        'fatigue': 0.15,
        'soreness': 0.15,
        'mood': 0.1,
        'stress': 0.1, # Added from alternative method
        'confidence': 0.1, # Added from alternative method
        'cmj': 0.1,
        'drop_jump': 0.1
    } 