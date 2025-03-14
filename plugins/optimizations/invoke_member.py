# coding=utf-8
import os
import pathlib
from xml.etree.ElementTree import Element

from plugins.getAst import create_ast_file, read_ast_file
from plugins.logger import log_debug
from plugins.utils import replace_node, delete_node, create_array_literal_values

# 优化Invoke-Expression函数
def opt_invoke_expression(ast):
    ret = False
    p = pathlib.Path("tmp.ps1")

    for node in ast.iter():
        if node.tag == "CommandElements":
            subnodes = list(node)
            if len(subnodes) == 2:
                if subnodes[0].tag == "StringConstantExpressionAst" and subnodes[0].attrib[
                    "StringConstantType"] == "BareWord" and subnodes[0].text == "Invoke-Expression":
                    if subnodes[1].tag == "StringConstantExpressionAst" and subnodes[1].attrib[
                        "StringConstantType"] != "BareWord":

                        script_content = subnodes[1].text

                        # 将脚本内容写入临时文件
                        with open(p, "w") as tmp:
                            tmp.write(script_content)

                        # 创建AST文件并读取
                        if create_ast_file(p, None):
                            if sub_ast := read_ast_file(p.with_suffix(".xml")):
                                log_debug("Replace Invoke-Expression by expression AST")

                                replace_node(ast, subnodes[0], sub_ast.getroot(), until="CommandAst")

                                ret = True
                                break

    # 删除临时文件
    try:
        os.remove(p.with_suffix(".xml"))
        os.remove(p.with_suffix(".ps1"))
    except:
        pass

    return ret

# 优化字符串替换函数
def opt_invoke_replace_string(ast):
    for node in ast.iter():
        if node.tag == "InvokeMemberExpressionAst":
            subnodes = list(node)

            if len(subnodes) < 3:
                continue

            if subnodes[2].tag == 'StringConstantExpressionAst' and \
                subnodes[2].attrib["StringConstantType"] == "BareWord" and \
                subnodes[2].text.lower() == "replace":
                if subnodes[1].tag == 'StringConstantExpressionAst' and \
                    subnodes[1].attrib["StringConstantType"] != "BareWord":
                    arguments = subnodes[0]
                    if arguments is not None:
                        argument_values = []

                        for element in list(arguments):
                            if element.tag == "StringConstantExpressionAst":
                                argument_values.append(element.text)

                        if len(argument_values) != 2:
                            continue
                        
                        if argument_values[1] is None:
                            formatted = subnodes[1].text.replace(argument_values[0], "")
                        else:
                            formatted = subnodes[1].text.replace(argument_values[0], argument_values[1])

                        log_debug("Apply replace method on '%s'" % formatted)

                        new_element = Element("StringConstantExpressionAst",
                                              {
                                                  "StringConstantType": "SingleQuoted",
                                                  "StaticType": "string",
                                              })
                        new_element.text = formatted

                        replace_node(ast, node, new_element)

                        return True
    return False

# 优化字符串分割函数
def opt_invoke_split_string(ast):
    for node in ast.iter():
        if node.tag == "InvokeMemberExpressionAst":
            subnodes = list(node)

            if len(subnodes) < 3:
                continue

            if subnodes[2].tag == 'StringConstantExpressionAst' and \
                subnodes[2].attrib["StringConstantType"] == "BareWord" and \
                subnodes[2].text.lower() == "split":
                if subnodes[1].tag == 'StringConstantExpressionAst' and \
                    subnodes[1].attrib["StringConstantType"] != "BareWord":
                    argument = subnodes[0]
                    if argument is not None:
                        argument = argument.find("StringConstantExpressionAst")
                        if argument is not None:
                            splitted = subnodes[1].text.split(argument.text)

                            new_array_ast = create_array_literal_values(splitted)

                            log_debug("Apply split operation to %s" % splitted)

                            replace_node(ast, node, new_array_ast)
                            return True
    return False

# 尝试反转未使用的变量
def try_reverse_variable_if_not_used(ast, variable, before_node):
    parent_map = dict((c, p) for p in ast.iter() for c in p)

    for node in ast.iter():
        if node.tag == "VariableExpressionAst" and node.attrib["VariablePath"].lower() == variable.lower():
            parent = parent_map[node]
            if parent is not None and parent_map[node].tag == "AssignmentStatementAst":
                operands = parent.find("CommandExpressionAst")
                if operands.tag == "CommandExpressionAst":
                    operands = operands.find("ArrayLiteralAst")
                if operands is not None:
                    operands = operands.find("Elements")

                    new_element = Element("Elements")
                    for element in operands:
                        new_element.insert(0, element)

                    replace_node(ast, operands, new_element)

                    log_debug(f"Apply reverse method to variable ${variable}")

                    return True
            else:
                return False

    return False

# 优化数组反转函数
def opt_invoke_reverse_array(ast):
    for node in ast.iter():
        variable = None
        if node.tag in ["InvokeMemberExpressionAst"]:
            subnodes = list(node)
            if subnodes[1].tag == "TypeExpressionAst" and subnodes[1].attrib["TypeName"].lower() == "array":
                if subnodes[2].tag == "StringConstantExpressionAst" and \
                    subnodes[2].attrib["StringConstantType"] == "BareWord":
                    argument = subnodes[0].find("VariableExpressionAst")
                    if argument is not None:
                        variable = argument.attrib["VariablePath"]

                        if try_reverse_variable_if_not_used(ast, variable, node):
                            delete_node(ast, node)

                            return True

    return False
