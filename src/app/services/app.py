from flask import Flask
from flask_cors import CORS
import config  # 이 시점에 config.{PROFILE}.py가 로딩됨

def create_app():
    app = Flask(__name__)
    app.config.from_object(config.config_module)
    CORS(app)

    @app.route("/flask/test")
    def hello():
        return f"DB: {app.config['DATABASE_URL']}"

    return app
