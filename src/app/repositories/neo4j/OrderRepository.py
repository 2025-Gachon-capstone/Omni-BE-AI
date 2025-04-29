from app.models import Order as Neo4jOrder, Product as Neo4jProduct, Member as Neo4jMember, ContainsRel
from app.utils.neo4j import safe_connect

class Neo4jOrderRepository:

    @staticmethod
    def create_member_if_not_exist(member_id: int) -> Neo4jMember:
        member = Neo4jMember.nodes.get_or_none(member_id=member_id)
        if not member:
            member = Neo4jMember(member_id=member_id).save()
        return member

    @staticmethod
    def create_order_if_not_exist(order_info: dict) -> Neo4jOrder:
        print(f'order_info: {order_info}')
        value = order_info['orderId']
        print(f'order_info[orderId]: {value}')

        order = Neo4jOrder.nodes.get_or_none(order_id=order_info['orderId'])
        print(f'order: {order}')
        if not order:
            order = Neo4jOrder(
                order_id=order_info.get("orderId"),
                days_since_prior_order=order_info.get("daysSincePrior"),
                order_dow=order_info.get("orderDow"),
                order_hour_of_day=order_info.get("orderHour"),
                order_count=order_info.get("orderCount"),
                eval_set=order_info.get("status"),
            ).save()
        return order

    @staticmethod
    def create_product_if_not_exist(product_id: int, product_name: str) -> Neo4jProduct:
        product = Neo4jProduct.nodes.get_or_none(product_id=product_id)
        print(f'product: {product is None}')

        if not product:
            product = Neo4jProduct(product_id=product_id, name=[0.1]).save() #TODO: 텍스트 임베딩한 상품명 넣기

        return product

    @staticmethod
    def get_previous_order(member: Neo4jMember, current_order_id: int) -> Neo4jOrder:
        try:
            orders = Neo4jOrder.nodes.filter(ordered_by=member)

            if not orders:
                return None
            
            return max(
                    (o for o in orders if o.order_id != current_order_id),
                    key=lambda o: o.order_id,
                    default=None
                )
        except Exception as e:
            print(f"Error in get_previous_order: {e}")
            return None

    @staticmethod
    def update_previous_order(previous_order: Neo4jOrder, new_order: Neo4jOrder, next_order_list=None):
        previous_order.next_order_list = next_order_list
        previous_order.eval_set = 'PRIOR'

        safe_connect(previous_order.next_to, new_order)
        
        previous_order.save()
