import os
import importlib

profile = os.getenv("PROFILE", "local")  # default = local

# config.local 또는 config.dev 로딩
config_module = importlib.import_module(f".{profile}", package=__name__)
print("✅ config_module:", dir(config_module))  # 추가!

config = config_module