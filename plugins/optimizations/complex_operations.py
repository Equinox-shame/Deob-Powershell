# coding=utf-8

from plugins.logger import log_debug
from plugins.utils import replace_node, get_array_literal_values, create_array_literal_values

# 优化常量数组的值函数
def opt_value_of_const_array(ast):
    for node in ast.iter():
        if node.tag == "IndexExpressionAst":
            subnodes = list(node)

            # 处理目标数组
            if subnodes[0].tag == "StringConstantExpressionAst":
                target = subnodes[0].text
            elif subnodes[0].tag == "ArrayLiteralAst":
                target = get_array_literal_values(subnodes[0])
            else:
                continue

            # 处理索引
            if subnodes[1].tag == "ConstantExpressionAst":
                indexes = [int(subnodes[1].text)]
            elif subnodes[1].tag == "ArrayLiteralAst":
                values = get_array_literal_values(subnodes[1])
                indexes = values
            else:
                continue

            # 根据索引获取目标数组的值并替换节点
            if target is not None and indexes is not None:
                if len(indexes) > 0:
                    new_array_ast = create_array_literal_values([target[index] for index in indexes])

                    log_debug(f"Apply index {indexes} operation to constant {target.__class__.__name__} {target}")

                    replace_node(ast, node, new_array_ast)

                    return True

    return False
