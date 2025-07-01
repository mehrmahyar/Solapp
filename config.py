import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # Add basedir as a class attribute
    basedir = basedir

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-hard-to-guess-string'
    # Enable CSRF protection
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'solapp.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit for uploads

    # Ensure upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Standard Health Questionnaire Questions
    # Structure: list of dicts, each dict is a question
    # 'id': unique identifier for the question
    # 'label': text displayed to the user
    # 'type': field type ('text', 'textarea', 'select', 'boolean')
    # 'choices': list of (value, label) tuples, only for 'select' type
    # 'validators': list of WTForms validators (Optional, DataRequired etc.) - not implemented in form generation yet
    HEALTH_QUESTIONNAIRE_QUESTIONS = [
        {
            'id': 'general_health',
            'label': 'How would you rate your current general health?',
            'type': 'select',
            'choices': [('', '-- Select --'), ('excellent', 'Excellent'), ('good', 'Good'), ('fair', 'Fair'), ('poor', 'Poor')]
        },
        {
            'id': 'recent_illness',
            'label': 'Have you experienced any significant illness in the past month?',
            'type': 'boolean'
        },
        {
            'id': 'illness_details',
            'label': 'If yes to recent illness, please provide details:',
            'type': 'textarea',
            'conditions': {'recent_illness': True} # Show if recent_illness is True (JS can handle this)
        },
        {
            'id': 'current_medications',
            'label': 'Are you currently taking any medications (prescription or over-the-counter)?',
            'type': 'textarea'
        },
        {
            'id': 'allergies',
            'label': 'Do you have any known allergies (medications, food, environmental)? Please list them.',
            'type': 'textarea'
        },
        {
            'id': 'past_injuries',
            'label': 'Please list any significant past injuries or surgeries (include type and approximate date).',
            'type': 'textarea'
        },
        {
            'id': 'current_pain',
            'label': 'Are you currently experiencing any pain or discomfort in any part of your body?',
            'type': 'boolean'
        },
        {
            'id': 'pain_details',
            'label': 'If yes to current pain, please describe (location, type, severity 1-10):',
            'type': 'textarea',
            'conditions': {'current_pain': True} # Show if current_pain is True
        },
        {
            'id': 'training_goals',
            'label': 'What are your primary training goals for the upcoming period?',
            'type': 'textarea'
        },
        {
            'id': 'consent_participation',
            'label': 'Do you consent to participate in the planned training and testing activities?',
            'type': 'boolean' # Should ideally be DataRequired if form is submitted
        }
    ]

    # Image Optimization Settings
    MAX_IMAGE_WIDTH = 1024  # pixels
    MAX_IMAGE_HEIGHT = 1024 # pixels
    IMAGE_QUALITY = 85 # For JPEGs, 0-100

    # Pagination Settings
    DEFAULT_LIST_PER_PAGE = 15
    PROGRAMS_LIST_PER_PAGE = 10
    CLIENT_VIEW_READINESS_PER_PAGE = 10
    CLIENT_VIEW_BODYCOMP_PER_PAGE = 10
    CLIENT_VIEW_TESTS_PER_PAGE = 10
    CLIENT_VIEW_SESSIONS_PER_PAGE = 5
    CLIENT_VIEW_PHOTOS_PER_PAGE = 8

    # Readiness Score Weights
    READINESS_WEIGHTS = {
        'sleep_quality': 0.1,    # Weight for sleep quality (1-5 scale)
        'sleep_duration': 0.1,   # Weight for sleep duration (normalized to 8hrs)
        'fatigue': 0.15,
        'soreness': 0.15,
        'mood': 0.1,
        'stress': 0.1,
        'confidence': 0.1,
        'cmj': 0.1,
        'drop_jump': 0.1
    }
    READINESS_INJURY_PENALTY = 0.7 # Multiply score by this if injury_pain is true (e.g., 30% reduction)