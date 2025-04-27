'''
src 경로에서 아래 커맨드 실행
python -m app.run

또는 utils/에서 아래 커맨드 사용시 코드 변경감지하여 자동 변경
flask run --port=5001 --reload 
'''


from .utils import create_app

app = create_app()

if __name__ == "__main__":
    app.run(port=5000) # 로컬에선 5001