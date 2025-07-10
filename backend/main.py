import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from src.core import db
import logging
from logging.handlers import RotatingFileHandler

# Charger les variables d'environnement
load_dotenv()


def create_app():
    app = Flask(__name__)
    
    # Configuration CORS plus explicite
    CORS(app, resources={
        r"/*": {
            "origins": ["http://localhost:8501", "http://localhost:8502", "http://localhost:8503", "http://localhost:8504", "http://127.0.0.1:8501", "http://127.0.0.1:8502", "http://127.0.0.1:8503", "http://127.0.0.1:8504"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Charger la configuration selon le mode
    env = os.getenv('APP_ENV', 'development')
    if env == 'production':
        app.config.from_object('src.configs.production.Config')
    else:
        app.config.from_object('src.configs.development.Config')
    
    # Configuration des timeouts pour éviter les connexions qui traînent
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

    # Configuration du logger avec rotation
    log_level = app.config.get('LOG_LEVEL', 'DEBUG')
    logger = logging.getLogger()
    logger.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')

    # Handler console
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Handler fichier avec rotation
    log_file = 'backend.log'
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        file_handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=5, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Importer et enregistrer les blueprints ici (routes)
    from src.api.routes.main import main_bp
    from src.api.routes.data import data_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(data_bp)

    db.init_app(app)

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 4000))
    # Désactiver le debug pour éviter les redémarrages pendant l'analyse de sentiment
    debug = False  # Force debug=False pour stabilité
    print(f"🚀 Démarrage du backend sur le port {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)
