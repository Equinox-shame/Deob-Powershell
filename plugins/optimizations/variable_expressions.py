# coding=utf-8
from xml.etree.ElementTree import Element

from plugins.logger import *
from plugins.utils import parent_map

def find_variable_value(ast, variable_path):
    """
    fix: 增强型变量查找，支持跨层级搜索
    """
    for node in ast.iter():
        if node.tag == "AssignmentStatementAst" and node.attrib.get("Operator") == "Equals":
            var_node = node.find(".//VariableExpressionAst")
            value_node = node.find(".//StringConstantExpressionAst")
            if (var_node is not None and 
                var_node.attrib.get("VariablePath") == variable_path and
                value_node is not None):
                return value_node
    return None
         
            
# 变量替换
def opt_variable_expression_replace(ast):
    """
    fix: 增加处理逻辑，替换变量表达式
    处理下列结构
    <InvokeMemberExpressionAst Static="False">
        <Arguments>
            <StringConstantExpressionAst> # 被替换内容
            <StringConstantExpressionAst> # 替换内容
        </Arguments>
            <VariableExpressionAst>  # 被替换变量
            <StringConstantExpressionAst>  # Replace 关键字
    </InvokeMemberExpressionAst>
    
    bug: 部分命令可能解析混乱 需要二次修复(手动修复)
    """
    
    parents = parent_map(ast)
    
    for node in ast.iter():
        if node.tag == "InvokeMemberExpressionAst" and node.attrib.get("Static") == "False":  # 非静态调用
            arguments = node.find("Arguments")
            if arguments is not None and len(arguments) == 2:
                first_arg = arguments[0]   # 被替换内容
                second_arg = arguments[1]  # 替换内容
                log_warn("Optimizing variable expression replace, this optimization may not work correctly")
                variable_node = node.find("VariableExpressionAst")
                replace_node = node.find("StringConstantExpressionAst")
                if (first_arg.tag == "StringConstantExpressionAst" and 
                        first_arg.attrib.get("StaticType") == "string" and
                        second_arg.tag == "StringConstantExpressionAst" and
                        second_arg.attrib.get("StaticType") == "string" and
                        variable_node is not None and
                        variable_node.attrib.get("VariablePath") and
                        replace_node is not None and
                        replace_node.text == "Replace"):
                    variable_path = variable_node.attrib.get("VariablePath")
                    variable_value = find_variable_value(ast, variable_path)  # 目标替换节点

                    if variable_value is not None:
                        
                        if second_arg.text is None:
                            new_text = variable_value.text.replace(first_arg.text, '')
                        else:
                            new_text = variable_value.text.replace(first_arg.text, second_arg.text)
                            
                        log_debug(f"Replacing {first_arg.text} with {second_arg.text} in {variable_value.text}")
                        log_debug(f"New value: {new_text}")
                        
                        variable_value.text = new_text
                        
                        # 删除Replace关键字的Ast
                        parent = parents.get(replace_node)
                        if parent is not None:
                            parent.remove(replace_node)
                        
                        # 删除Arguments节点中的参数Ast
                        arguments.remove(first_arg)
                        arguments.remove(second_arg)
                 
                        return True
    return False

"""
todo: 变量表达式拆分 split 逻辑实现
<BinaryExpressionAst Operator="Isplit" StaticType="System.Object">
<StringConstantExpressionAst StringConstantType="SingleQuoted" StaticType="string">xxx</StringConstantExpressionAst> # 被去除内容
<StringConstantExpressionAst StringConstantType="SingleQuoted" StaticType="string">xxx</StringConstantExpressionAst> # 去除内容
</BinaryExpressionAst>
"""
def opt_variable_expression_split(ast):
    for node in ast.iter():
        parents = parent_map(ast)
    
    for node in ast.iter():
        if node.tag == "InvokeMemberExpressionAst" and node.attrib.get("Static") == "False":  # 非静态调用
            arguments = node.find("Arguments")
            if arguments is not None and len(arguments):
                """
                fix: 支持单参数的 split
                """
                if len(arguments) == 1: 
                    first_arg = arguments[0]   # 替换内容
                    variable_node = node.find("VariableExpressionAst")
                    replace_node = node.find("StringConstantExpressionAst")
                    log_warn("Optimizing variable expression split, this optimization may not work correctly")
                    
                    if (first_arg.tag == "StringConstantExpressionAst" and 
                            first_arg.attrib.get("StaticType") == "string" and
                            variable_node is not None and
                            variable_node.attrib.get("VariablePath") and
                            replace_node is not None and
                            replace_node.text == "Split"):
                        variable_path = variable_node.attrib.get("VariablePath")
                        variable_value = find_variable_value(ast, variable_path)  # 目标替换节点

                        if variable_value is not None:
                            
                            new_text = variable_value.text.replace(first_arg.text, '')

                            log_debug(f"Split (Actually Replaced) {first_arg.text} with None in {variable_value.text}")
                            log_debug(f"New value: {new_text}")
                            
                            variable_value.text = new_text
                            
                            # 删除Replace关键字的Ast
                            parent = parents.get(replace_node)
                            if parent is not None:
                                parent.remove(replace_node)
                            
                            # 删除Arguments节点中的参数Ast
                            arguments.remove(first_arg)
                    
                            return True
    return False