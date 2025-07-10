from src.core import db
from src.api.models.data_models import MainData
from flask import Flask

app = Flask(__name__)
app.config.from_object('src.configs.development.Config')
db.init_app(app)

with app.app_context():
    db.create_all()
    print("Base de données initialisée avec succès.") 