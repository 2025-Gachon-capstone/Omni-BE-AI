import datetime
import pytz

def ts():
    # 한국 시간대 설정
    kst = pytz.timezone('Asia/Seoul')
    # 현재 UTC 시간을 한국 시간대로 변환
    now_kst = datetime.datetime.now(kst)
    # 연, 월, 일, 시간, 분, 초 포맷
    return now_kst.strftime("%Y-%m-%d %H:%M:%S")