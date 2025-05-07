from typing import List
from neomodel import StructuredRel, StructuredNode, StringProperty, IntegerProperty, RelationshipTo, RelationshipFrom, FloatProperty, ArrayProperty, BooleanProperty

class ContainsRel(StructuredRel):
    '''
    주의) 간선에 저장하하게 되어 GraphSAGE에 학습할 수 없게 됨.
    하지만, 이걸 노드로 만들기에는 그래프 DB의 설계에 맞지 않고,
    이 정보가 없더라도 그래프의 이웃 노드 참조만으로도 다른 모델보다
    성능이 좋게 나오는지 궁금해서 이렇게 해봤어요.
    '''
    reordered = BooleanProperty()
    add_to_cart_order = FloatProperty()

class Sponsor(StructuredNode):
    sponsor_id = IntegerProperty(unique_index=True)
    name = StringProperty()

    name_vector = ArrayProperty(FloatProperty())  # 텍스트 임베딩 저장    
    node_vector = ArrayProperty(FloatProperty()) # 그래프 세이지 임베딩 저장
    
    issues = RelationshipTo('Benefit', 'ISSUES')

class Benefit(StructuredNode):
    benefit_id = IntegerProperty(unique_index=True)
    title = StringProperty()
    target_product = StringProperty()
    target_member = StringProperty()
    discount_rate = FloatProperty()
    
    title_vector = ArrayProperty(FloatProperty())  # 텍스트 임베딩 저장
    tartget_product_vector = ArrayProperty(FloatProperty())  # 텍스트 임베딩 저장
    target_member_vector = ArrayProperty(FloatProperty())  # 텍스트 임베딩 저장
    node_embedding = ArrayProperty(FloatProperty())  # 그래프 세이지 임베딩 저장
    
    discounts = RelationshipTo('Product', 'DISCOUNTS')
    given_to = RelationshipFrom('Member', 'GIVEN')
    issued_by = RelationshipFrom('Sponsor', 'ISSUES')

class Product(StructuredNode):
    product_id = IntegerProperty(unique_index=True)
    name = StringProperty()
    category = StringProperty()

    name_vector = ArrayProperty(FloatProperty())  # 텍스트 임베딩 저장
    category_vector = ArrayProperty(FloatProperty()) # 텍스트 임베딩 저장
    node_embedding = ArrayProperty(FloatProperty())
    
    contained_by = RelationshipFrom('Order', 'CONTAINS')
    discounted_by = RelationshipFrom('Benefit', 'DISCOUNTS')

class Order(StructuredNode):
    order_id = IntegerProperty(unique_index=True)
    eval_set = StringProperty(choices={
        'PRIOR': 'PRIOR',
        'TRAIN': 'TRAIN',
        'TEST_PRIOR': 'TEST_PRIOR', # 테스트 유저도  Prior, train이 필요함
        'TEST_TRAIN': 'TEST_TRAIN',
    })
    order_count = IntegerProperty()
    order_dow = IntegerProperty()
    order_hour_of_day = IntegerProperty()
    days_since_prior_order = IntegerProperty()

    order_count_vector = FloatProperty() # min-max정규화
    order_dow_vector = FloatProperty() # min-max
    order_hour_of_day_vector = FloatProperty() # min-max
    days_since_prior_order_vector = FloatProperty() # min-max
    node_embedding = ArrayProperty(FloatProperty())

    '''
    다음 주문내역(next_order_list)의 그래프 세이지 임베딩
    주의 : '다음 주문내역 = 다음 주문서 + 구매한 모든 상품 리스트'
    '''
    predict_order_list = ArrayProperty(FloatProperty()) # 다음 구매 내역 예측
    next_order_list = ArrayProperty(FloatProperty()) # 실제 다음 구매 내역
    loss = FloatProperty() # 예측 - 실제
    
    next_to = RelationshipTo('Order', 'NEXT')
    previous_from = RelationshipFrom('Order', 'NEXT')
    contains = RelationshipTo('Product', 'CONTAINS', model=ContainsRel)
    ordered_by = RelationshipFrom('Member', 'ORDERED') # RelationshipFrom의 두번째 파라미터는 역참조할 간선의 이름을 넣음


class Member(StructuredNode):
    member_id = IntegerProperty(unique_index=True)
    metadata = StringProperty()

    metadata_vector = ArrayProperty(FloatProperty())
    predict_order_list = ArrayProperty(FloatProperty()) # 아직 구매하지 않은 다음 구매내역의 벡터화

    ordered = RelationshipTo('Order', 'ORDERED')