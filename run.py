from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(port=5001) # 로컬에선 5001
