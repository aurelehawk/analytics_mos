import os

INSTANCE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'instance')
DB_PATH = os.path.join(INSTANCE_PATH, 'dev_db.sqlite3')

class Config:
    DEBUG = True
    TESTING = True
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret_key')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = 'DEBUG'
    # Configuration pour les uploads de fichiers
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max 