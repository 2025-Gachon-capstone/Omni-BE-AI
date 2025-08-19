# src/app/container/service_container.py
from pathlib import Path
from src.app.bert.vocab import load_vocab
from src.app.bert.predictor import load_predictor
from src.app.services.BenefitService import BenefitService
from src.app.repositories.mysql.OrderRepository import MysqlOrderRepository

class ServiceContainer:
    def __init__(self, config: dict):
        # 1) 리소스 생성
        vocab_path = Path(config["VOCAB_PATH"]).resolve()
        self.vocab = load_vocab(vocab_path)
        self.predictor = load_predictor(num_threads=config.get("PREDICTOR_THREADS", 4))
        # 2) 레포지토리/서비스 조립
        self.order_repo = MysqlOrderRepository  # 정적 메서드만 쓰니 클래스 자체를 넘겨도 OK
        self.benefit_service = BenefitService(
            vocab=self.vocab,
            predictor=self.predictor,
            order_repo=self.order_repo,
        )
