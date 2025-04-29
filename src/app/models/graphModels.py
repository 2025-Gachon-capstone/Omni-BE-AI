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
    sponsor_id = IntegerProperty()

    name = ArrayProperty(FloatProperty())  # 텍스트 임베딩 저장    
    node_embedding = ArrayProperty(FloatProperty()) # 그래프 세이지 임베딩 저장
    
    issues = RelationshipTo('Benefit', 'ISSUES')

class Benefit(StructuredNode):
    benefit_id = IntegerProperty()
    
    title = ArrayProperty(FloatProperty())  # 텍스트 임베딩 저장
    tartget_product = ArrayProperty(FloatProperty())  # 텍스트 임베딩 저장
    target_member = ArrayProperty(FloatProperty())  # 텍스트 임베딩 저장
    discount_rate = FloatProperty()
    node_embedding = ArrayProperty(FloatProperty())  # 그래프 세이지 임베딩 저장
    
    discounts = RelationshipTo('Product', 'DISCOUNTS')
    given_to = RelationshipFrom('Member', 'GIVEN')
    issued_by = RelationshipFrom('Sponsor', 'ISSUES')

class Product(StructuredNode):
    product_id = IntegerProperty()

    name = ArrayProperty(FloatProperty())  # 텍스트 임베딩 저장
    category = FloatProperty() # min-max
    node_embedding = ArrayProperty(FloatProperty())
    
    discounted_by = RelationshipFrom('Benefit', 'DISCOUNTS')

class Order(StructuredNode):
    order_id = IntegerProperty()
    eval_set = StringProperty(choices={
        'PRIOR': 'PRIOR',
        'TRAIN': 'TRAIN',
    })

    order_count = FloatProperty() # min-max정규화
    order_dow = FloatProperty() # min-max
    order_hour_of_day = FloatProperty() # min-max
    days_since_prior_order = FloatProperty() # min-max
    node_embedding = ArrayProperty(FloatProperty())

    '''
    다음 주문내역(next_order_list)의 그래프 세이지 임베딩
    주의 : '다음 주문내역 = 다음 주문서 + 구매한 모든 상품 리스트'
    '''
    predict_order_list = ArrayProperty(FloatProperty()) # 다음 구매 내역 예측
    next_order_list = ArrayProperty(FloatProperty()) # 실제 다음 구매 내역
    loss = FloatProperty() # 예측 - 실제
    
    next_to = RelationshipTo('Order', 'NEXT')
    contains = RelationshipTo('Product', 'CONTAINS', model=ContainsRel)
    ordered_by = RelationshipFrom('Member', 'ORDERED_BY')


class Member(StructuredNode):
    member_id = IntegerProperty()

    ordered = RelationshipTo('Order', 'ORDERED')
    predict_order_list = ArrayProperty(FloatProperty()) # 아직 구매하지 않은 다음 구매내역의 벡터화