# coding=utf-8
from plugins.logger import log_info
from plugins.utils import parent_map

# 优化移除空节点函数
def opt_remove_empty_nodes(ast):
    parents = parent_map(ast)
    kill_list = []
    for node in ast.iter():
        # 检查特定类型的节点是否为空
        if node.tag in ("Attributes", "Redirections", "CatchTypes", \
                        "Operator", "TokenKind", "BlockKind", "InvocationOperator", \
                        "Flags", "Clauses"):
            if len(node) == 0:
                kill_list.append(node)

    # 移除空节点
    for node in kill_list:
        parents[node].remove(node)

    if kill_list:
        log_info(f"Deleted {len(kill_list)} empty nodes")

    return False
