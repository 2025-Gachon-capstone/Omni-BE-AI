from flask import Flask
from flasgger import Swagger
from ..utils import db
from ..routes.routes import api_blueprints

from ..config import config  # 이 시점에 config.{PROFILE}.py가 로딩됨

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}/{config.DB_NAME}"
    app.config['SQLALCHEMY_DATABASE_URI'] += f"?ssl_disabled=True&use_unicode=True&time_zone=Asia/Seoul" # useSSL처럼 사용 금지. mysql-connector-python 지원 문법 사용 
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

     # ✅ SQLAlchemy 초기화
    db.init_app(app)

    app.config['SWAGGER'] = {
        'title': 'Omni-BE-AI API',
        'openapi': '3.0.0', 
        'uiversion': 3 
    }

    swagger_template = {
        "info": {
            "title": "Omni-BE-AI API", 
            "description": "Flask Backend Server for AI",
            "version": "1.0.0"
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Enter JWT Bearer token **_only_**"
                }
            }
        },
        "security": [
            {
                "BearerAuth": []
            }
        ]
    }
    
    swagger_config = {                         
         "headers": [],
         "specs": [
             {
                 "endpoint": 'flask_spec',
                 "route": config.SWAGGER_SPECS_JSON_ROUTE,
                 "rule_filter": lambda rule: True,
                 "model_filter": lambda tag: True,
             }
         ],
         "static_url_path": config.SWAGGER_STATIC_PATH, 
         "swagger_ui": True,
         "specs_route": config.SWAGGER_SPECS_ROUTE
     }

    swagger = Swagger(app, template=swagger_template, config=swagger_config) 
    
    app.register_blueprint(api_blueprints)
    return app
