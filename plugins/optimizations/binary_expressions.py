# coding=utf-8
from xml.etree.ElementTree import Element

from plugins.logger import log_debug, log_err
from plugins.utils import (create_array_literal_values, create_constant_number,
                           create_constant_string, get_array_literal_values,
                           parent_map, replace_node, to_numeric)

# 优化加法二元表达式函数
def opt_binary_expression_plus(ast): 
    replacements = []
    for node in ast.iter():
        if node.tag == 'BinaryExpressionAst':
            operator = node.attrib['Operator']
            if operator == "Plus":
                subnodes = list(node)

                # 处理左操作数
                if subnodes[0].tag == "StringConstantExpressionAst":
                    left = subnodes[0].text
                elif subnodes[0].tag == "ConstantExpressionAst":
                    left = to_numeric(subnodes[0].text)
                elif subnodes[0].tag == "ArrayLiteralAst":
                    left = get_array_literal_values(subnodes[0])
                else:
                    continue

                # 处理右操作数
                if subnodes[1].tag == "StringConstantExpressionAst":
                    right = subnodes[1].text
                elif subnodes[1].tag == "ConstantExpressionAst":
                    right = to_numeric(subnodes[1].text)
                elif subnodes[1].tag == "ArrayLiteralAst":
                    right = get_array_literal_values(subnodes[1])
                else:
                    continue

                # 合并字符串常量
                if left is not None and right is not None:
                    if isinstance(left, str) and isinstance(right, str):
                        new_element = create_constant_string(left + right, "DoubleQuoted")
                        log_debug("Merging constant strings:  '%s', '%s' to '%s'" % (subnodes[0].text, subnodes[1].text, new_element.text))
                        replacements.append((node, new_element))

                    # 合并数字常量
                    elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
                        new_element = create_constant_number(left + right)
                        replacements.append((node, new_element))

                    # 合并数组
                    else:
                        items = []
                        if isinstance(left, str) and isinstance(right, list):
                            right.insert(0, left)
                            items = right
                        elif isinstance(left, list) and isinstance(right, str):
                            left.append(right)
                            items = left
                        elif isinstance(left, list) and isinstance(right, list):
                            left.extend(right)
                            items = left

                        new_array_ast = create_array_literal_values(items)
                        replacements.append((node, new_array_ast))

    if replacements:
        parents = parent_map(ast)
    for node, repl in replacements:
        replace_node(ast, node, repl, parents=parents)

    return len(replacements) != 0

# 优化乘法和减法二元表达式函数
def opt_binary_expression_numeric_operators(ast):
    replacements = []
    for node in ast.iter():
        if node.tag == 'BinaryExpressionAst':
            operator = node.attrib['Operator']
            if operator in ["Multiply", "Minus"]:
                subnodes = list(node)

                # 处理左操作数
                if subnodes[0].tag == "ConstantExpressionAst":
                    left = to_numeric(subnodes[0].text)
                else:
                    continue

                # 处理右操作数
                if subnodes[1].tag == "ConstantExpressionAst":
                    right = to_numeric(subnodes[1].text)
                else:
                    continue

                # 计算结果并替换节点
                if left is not None and right is not None:
                    if operator == "Multiply":
                        new_element = create_constant_number(left * right)
                    elif operator == "Minus":
                        new_element = create_constant_number(left - right)
                    replacements.append((node, new_element))

    if replacements:
        parents = parent_map(ast)
    for node, repl in replacements:
        replace_node(ast, node, repl, parents=parents)

    return len(replacements) != 0

# 优化替换操作符二元表达式函数
def opt_binary_expression_replace(ast):
    for node in ast.iter():
        if node.tag in ["BinaryExpressionAst"] and node.attrib["Operator"] == "Ireplace":
            target = node.find("StringConstantExpressionAst")
            if target is not None:
                target = target.text
            else:
                continue

            argument_values = get_array_literal_values(node.find("ArrayLiteralAst"))

            if argument_values is None or len(argument_values) != 2:
                return False

            formatted = target.replace(argument_values[0], argument_values[1])

            log_debug("Apply replace operator to '%s'" % formatted)

            new_element = Element("StringConstantExpressionAst",
                                  {
                                      "StringConstantType": "SingleQuoted",
                                      "StaticType": "string",
                                  })
            new_element.text = formatted

            replace_node(ast, node, new_element)

            return True
    return False


# 优化格式化操作符二元表达式函数
def opt_binary_expression_format(ast):
    for node in ast.iter():
        if node.tag in ["BinaryExpressionAst"] and node.attrib["Operator"] == "Format":
            format_str = node.find("StringConstantExpressionAst")
            if format_str is not None:
                format_str = format_str.text

            argument_values = get_array_literal_values(node.find("ArrayLiteralAst"))
            if argument_values is None:
                continue

            try:
                formatted = format_str.format(*argument_values)
            except IndexError:
                continue

            new_element = Element("StringConstantExpressionAst",
                                  {
                                      "StringConstantType": "SingleQuoted",
                                      "StaticType": "string",
                                  })
            new_element.text = formatted

            log_debug("Apply format operation to '%s'" % formatted)

            replace_node(ast, node, new_element)

            return True
    return False

# 优化连接操作符二元表达式函数
def opt_binary_expression_join(ast):
    for node in ast.iter():
        if node.tag in ["BinaryExpressionAst"] and node.attrib["Operator"] == "Join":
            subnodes = list(node)

            joiner = node.find("StringConstantExpressionAst")
            if joiner is not None:
                joiner = joiner.text
                if joiner is None:
                    joiner = ""
            else:
                log_err(f"BinaryExpression Join with {subnodes[0].tag} joiner is unsupported")
                continue

            values = node.find("ArrayLiteralAst")
            if values is not None:
                values = get_array_literal_values(values)

            if joiner is None or values is None:
                continue

            try:
                joined = joiner.join(values)
            except Exception:
                continue

            new_element = Element("StringConstantExpressionAst",
                                  {
                                      "StringConstantType": "SingleQuoted",
                                      "StaticType": "string",
                                  })
            new_element.text = joined

            log_debug("Apply join operation to '%s'" % joined)

            replace_node(ast, node, new_element)

            return True
    return False
