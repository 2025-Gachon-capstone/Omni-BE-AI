from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from ..routes.routes import api_blueprints

from ..config import config  # 이 시점에 config.{PROFILE}.py가 로딩됨



def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Omni-BE-AI API",
            "description": "Flask Backend Server for AI",
            "version": "1.0.0"
        },

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
