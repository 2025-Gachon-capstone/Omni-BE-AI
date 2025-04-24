from .utils.app import create_app

app = create_app()

if __name__ == "__main__":
    for r in app.url_map.iter_rules():
        print(r.endpoint, r.rule)
    app.run(port=5001) # 로컬에선 5001

