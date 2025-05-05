from flask import Flask, request
from flasgger import Swagger
from neomodel import config as neomodel_config

from ..utils import db
from ..routes import prompt_routes, order_routes, ml_routes

from ..config import config, get_swagger_config, get_swagger_template  # 이 시점에 config.{PROFILE}.py가 로딩됨

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    # MYSQL
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}/{config.DB_NAME}"
    app.config['SQLALCHEMY_DATABASE_URI'] += f"?ssl_disabled=True&use_unicode=True&time_zone=Asia/Seoul" # useSSL처럼 사용 금지. mysql-connector-python 지원 문법 사용 
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # NEO4J
    neomodel_config.DATABASE_URL = f'bolt://{config.NEO4J_USER}:{config.DB_PASSWORD}@{config.NEO4J_HOST}:{config.NEO4J_PORT}'

    @app.after_request
    def set_default_headers(response):
        # 클라이언트가 application/json을 기대하는 경우만 설정
        accept = request.headers.get('Accept', '')
        if 'application/json' in accept:
            if response.content_type and response.content_type.startswith('application/json'):
                response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

     # ✅ SQLAlchemy 초기화
    db.init_app(app)

    swagger = Swagger(app, template=get_swagger_template(), config=get_swagger_config()) 
    
    app.register_blueprint(prompt_routes)
    app.register_blueprint(order_routes)
    app.register_blueprint(ml_routes)
    
    return app
