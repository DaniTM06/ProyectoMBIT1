import json
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # Cargo el archivo JSON con sus credenciales
    with open('credentials.json') as f:
        credentials = json.load(f)

    # Base de datos
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mbit:mbit@db:3306/pictures'
    
    # Configuración de ImageKit e Imagga
    app.config['IMAGEKIT_PUBLIC_KEY'] = credentials['imagekit_public_key']
    app.config['IMAGEKIT_PRIVATE_KEY'] = credentials['imagekit_private_key']
    app.config['IMAGEKIT_URL_ENDPOINT'] = credentials['imagekit_url_endpoint']
    app.config['IMAGGA_API_KEY'] = credentials['imagga_api_key']
    app.config['IMAGGA_API_SECRET'] = credentials['imagga_api_secret']

    db.init_app(app)
    
    from .controllers import main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app
