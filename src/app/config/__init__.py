import os
import importlib

profile = os.getenv("PROFILE", "local")  # default = local

# config.local 또는 config.dev 로딩
config_module = importlib.import_module(f".{profile}", package=__name__)
print("✅ config_module:", dir(config_module))  # 추가!

config = config_module

setattr(config, 'SWAGGER', {
    'title': 'Omni-BE-AI API',
    'openapi': '3.0.0',
    'uiversion': 3
})

def get_swagger_template():
    return {
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

def get_swagger_config():
    return {
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