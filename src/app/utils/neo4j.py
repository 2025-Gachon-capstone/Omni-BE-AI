def safe_connect(rel_manager, target_node, **properties):
    """
    관계가 이미 연결되어 있지 않은 경우에만 연결한다.
    :param rel_manager: node.relationship_manager (예: member.ordered)
    :param target_node: 연결할 대상 노드
    """
    existing_relation = rel_manager.relationship(target_node)

    if existing_relation:
        if properties:
            for key, value in properties.items():
                setattr(existing_relation, key, value)
            existing_relation.save()
    else:
        if properties:
            rel_manager.connect(target_node, properties)
        else:
            rel_manager.connect(target_node)

def safe_disconnect(rel_manager, target_node):
    """
    관계가 연결되어 있을 경우에만 연결을 끊는다.
    :param rel_manager: node.relationship_manager (예: member.ordered)
    :param target_node: 연결 해제할 대상 노드
    """
    if rel_manager.is_connected(target_node):
        rel_manager.disconnect(target_node)
