from flask import Flask
from flask_cors import CORS
from ..routes.routes import api_blueprints

from ..config import config  # 이 시점에 config.{PROFILE}.py가 로딩됨

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    CORS(app)
    app.register_blueprint(api_blueprints)
    return app
