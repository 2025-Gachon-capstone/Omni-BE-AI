from flask import Blueprint, request

from ..services import LearningService, PredictService

ml_routes = Blueprint('ml_routes', __name__, url_prefix='/flask/v1/ml')

@ml_routes.route("/train", methods=["POST", "GET"])
def train_model():
    if request.method == "GET":
        # 전체 데이터셋 학습
        return LearningService.train_and_save_model_all()
    # POST: 개별/파라미터 기반 학습
    return LearningService.train_and_save_model()

@ml_routes.route("/predict", methods=["POST", "GET"])
def predict():
    if request.method == "GET":
        # 전체 데이터셋 예측
        return PredictService.predict_all()
    # POST: 개별 예측
    data = request.get_json()
    member_id = data.get('member_id')
    product_id = data.get('product_id')
    if member_id is None or product_id is None:
        return {
            'isSuccess': False,
            'code': 'PREDICT-400',
            'message': 'member_id, product_id는 필수입니다.',
            'timestamp': '...'
        }, 400
    return PredictService.predict_purchase_probability(member_id, product_id)
