# coding=utf-8
import re

from xml.etree.ElementTree import Element

from plugins.barewords import BAREWORDS
from plugins.logger import *
from plugins.scope import Scope
from plugins.special_vars import SPECIAL_VARS_NAMES
from plugins.utils import (create_array_literal_values, create_constant_number,
                           create_constant_string, get_array_literal_values, get_assigned_vars,
                           parent_map, replace_node, to_numeric)

# 优化命令元素为裸字函数
def opt_command_element_as_bareword(ast):
    """
    fix: 修复 aa.bb.cc 方法通过添加单/双引号的混淆
    """
    def process_subnode(subnode):
        if subnode.tag == "StringConstantExpressionAst" and subnode.attrib["StringConstantType"] != "BareWord": # 修复关键字为 string 类型混淆
            parts = subnode.text.split('.')

            if all(part.lower() in BAREWORDS for part in parts):
                subnode.attrib["StringConstantType"] = "BareWord"
                log_debug(f"Fix string type for command {subnode.text}")
                return True
        elif subnode.tag == "ParenExpressionAst": 
            for nested_node in subnode:
                if process_subnode(nested_node):
                    return True
        return False

    for node in ast.iter():
        if node.tag == "CommandElements":
            for subnode in node:
                if process_subnode(subnode):
                    return True
    return False

# 原有方法 - 暂时废弃
# def opt_command_element_as_bareword(ast):
#     for node in ast.iter():
#         if node.tag == "CommandElements":
#             for subnode in node: 
#                 if subnode.tag == "StringConstantExpressionAst" and subnode.attrib["StringConstantType"] != "BareWord": # 修复关键字为 string 类型混淆
#                     if subnode.text in BAREWORDS:
#                         subnode.attrib["StringConstantType"] = "BareWord"

#                         log_debug(f"Fix string type for command {subnode.text}")

#                         return True
#     return False

# 优化特殊变量大小写函数
def opt_special_variable_case(ast):
    for node in ast.iter():
        if node.tag == "VariableExpressionAst":
            if node.attrib["VariablePath"].lower() in SPECIAL_VARS_NAMES: # 修复特殊变量名
                if node.attrib["VariablePath"] != SPECIAL_VARS_NAMES[node.attrib["VariablePath"].lower()]:
                    node.attrib["VariablePath"] = SPECIAL_VARS_NAMES[node.attrib["VariablePath"].lower()]
                       
                    log_debug(f'Fix variable name case for ${node.attrib["VariablePath"]}')

                    return True
    return False

# 优化类型约束转换函数
def opt_type_constraint_from_convert(ast):
    for node in ast.iter():
        if node.tag == "ConvertExpressionAst":
            subnodes = list(node)
            if subnodes[0].tag == "TypeConstraintAst":
                if subnodes[0].attrib["TypeName"] != node.attrib["StaticType"]:
                    subnodes[0].attrib["TypeName"] = node.attrib["StaticType"]
                    return True
    return False

# 优化类型约束大小写函数
def opt_type_constraint_case(ast):
    def get_new_value(t): # 字符替换
        
        new_val = t
        new_val = ".".join(
            [BAREWORDS[t.lower()] if t.lower() in BAREWORDS else t for t in new_val.split(".")])
        new_val = "-".join(
            [BAREWORDS[t.lower()] if t.lower() in BAREWORDS else t for t in new_val.split("-")])
        return new_val

    for node in ast.iter():
        if node.tag == "ConvertExpressionAst":
            typename = node.attrib["StaticType"]
            new_value = get_new_value(typename)

            if typename != new_value:
                node.attrib["StaticType"] = new_value
                log_debug("Fix typename case from '%s' to '%s'" % (typename, new_value))
                return True

        elif node.tag in ["TypeConstraintAst", "TypeExpressionAst"]:
            typename = node.attrib["TypeName"]
            new_value = get_new_value(typename)

            if typename != new_value:
                node.attrib["TypeName"] = new_value
                log_debug("Fix typename case from '%s' to '%s'" % (typename, new_value))
                return True

    return False

# 优化简化单表达式括号函数
def opt_simplify_paren_single_expression(ast):
    replacements = []
    for node in ast.iter():
        if node.tag == "ParenExpressionAst":
            subnodes = list(node)
            if len(subnodes) == 1 and subnodes[0].tag in ["PipelineAst"]:
                subnodes = list(subnodes[0])
            if len(subnodes) == 1 and subnodes[0].tag in ["PipelineElements"]:
                subnodes = list(subnodes[0])
            if len(subnodes) == 1 and subnodes[0].tag in ["CommandExpressionAst"]:
                subnodes = list(subnodes[0])
            if len(subnodes) == 1 and subnodes[0].tag not in ["CommandAst", "UnaryExpressionAst",
                                                              "BinaryExpressionAst"]:
                log_debug("Replace paren with single expression by %s" % subnodes[0].tag)

                replacements.append((node, subnodes[0]))

    if replacements:
        parents = parent_map(ast)
    for node, repl in replacements:
        replace_node(ast, node, repl, parents=parents)

    return len(replacements) != 0

# 优化简化单命令管道函数
def opt_simplify_pipeline_single_command(ast):
    replacements = []
    for node in ast.iter():
        if node.tag == "PipelineAst":
            subnodes = list(node)
            if len(subnodes) == 1 and subnodes[0].tag in ["PipelineElements"]:
                subnodes = list(subnodes[0])
            if len(subnodes) == 1:
                log_debug("Replace pipeline with single elements by %s" % subnodes[0].tag)

                replacements.append((node, subnodes[0]))

    if replacements:
        parents = parent_map(ast)
    for node, repl in replacements:
        replace_node(ast, node, repl, parents=parents)

    return len(replacements) != 0

# 优化简化单元素数组函数
def opt_simplify_single_array(ast):
    for node in ast.iter():
        if node.tag == "ArrayLiteralAst":
            subnodes = list(node)
            if len(subnodes) == 1 and subnodes[0].tag in ["Elements"]:
                subnodes = list(subnodes[0])
            if len(subnodes) == 1 and subnodes[0].tag not in ["CommandAst", "UnaryExpressionAst",
                                                              "BinaryExpressionAst"]:
                log_debug("Replace array with single element by %s" % subnodes[0].tag)

                replace_node(ast, node, subnodes[0])

                return True
    return False

# 优化常量字符串类型函数
def opt_constant_string_type(ast):
    for node in ast.iter():
        if node.tag in ["InvokeMemberExpressionAst", "MemberExpressionAst"]:
            for cst_string_node in node.findall("StringConstantExpressionAst"):
                if cst_string_node.text is None:
                    continue
                member = cst_string_node.text.lower()
                if member in BAREWORDS:
                    if cst_string_node.attrib["StringConstantType"] != "BareWord":
                        cst_string_node.text = BAREWORDS[member]

                        log_debug("Fix member string type for '%s'" % cst_string_node.text)

                        cst_string_node.attrib["StringConstantType"] = "BareWord"

                        return True

        if node.tag in ["CommandElements"]:
            for subnode in node:
                if subnode.tag == "StringConstantExpressionAst" and subnode.attrib["StringConstantType"] != "BareWord":
                    subnode.attrib["StringConstantType"] = "BareWord"

                    log_debug("Fix command string type for '%s'" % subnode.text)

                    return True
                break
    return False

# 优化裸字大小写函数
def opt_bareword_case(ast):
    for node in ast.iter():
        if node.tag in ["StringConstantExpressionAst"] and node.attrib["StringConstantType"] == "BareWord":
            """
            fix: 加入正则匹配修复特例 [SYSTeM.IO.CoMPRESsiON.cOMpreSSIonMOde]::DeComPrEss
            bug: 部分时候ast解析会得到如 xxx]::xxx 的格式，疑似对于特殊字符的 AST解析处理不当 存在空格时候可能会被吞 " [ "
            """
            old_value = node.text
            new_value = node.text
            
            is_type_1 = new_value[0] == "[" and new_value[-1] == "]"  # 检测 [xxx] 格式
            type_2_pattern = "\[([^\]]+)\]::(\w+)"
            is_type_2 = re.match(type_2_pattern, new_value) # 检测 [xxx]::xxx 格式
            
            if is_type_2: 
                part_1 = is_type_2.group(1)
                part_2 = is_type_2.group(2)
                
                part_1 = ".".join([BAREWORDS[t.lower()] if t.lower() in BAREWORDS else t for t in part_1.split(".")])
                part_1 = "-".join([BAREWORDS[t.lower()] if t.lower() in BAREWORDS else t for t in part_1.split("-")])
                part_2 = ".".join([BAREWORDS[t.lower()] if t.lower() in BAREWORDS else t for t in part_2.split(".")])
                part_2 = "-".join([BAREWORDS[t.lower()] if t.lower() in BAREWORDS else t for t in part_2.split("-")])
                
                new_value = "[" + part_1 + "]" + "::" + part_2
                
            elif is_type_1: 
                new_value = new_value[1:-1]
                new_value = ".".join([BAREWORDS[t.lower()] if t.lower() in BAREWORDS else t for t in new_value.split(".")])
                new_value = "-".join([BAREWORDS[t.lower()] if t.lower() in BAREWORDS else t for t in new_value.split("-")])
                
            else: # 常规情况
                new_value = ".".join([BAREWORDS[t.lower()] if t.lower() in BAREWORDS else t for t in new_value.split(".")])
                new_value = "-".join([BAREWORDS[t.lower()] if t.lower() in BAREWORDS else t for t in new_value.split("-")])
                
            if is_type_1:
                new_value = "[" + new_value + "]"

            if old_value != new_value:
                node.text = new_value

                log_debug("Fix bareword case from '%s' to '%s'" % (old_value, node.text))

                return True

    return False

# 优化前缀变量大小写函数
def opt_prefixed_variable_case(ast):
    for node in ast.iter():
        if node.tag == "StringConstantExpressionAst" and node.attrib["StringConstantType"] == "BareWord":
            names = node.text.split(":")
            if len(names) > 1 and names[0].lower() in ["variable", "env"]:
                old_name = node.text
                names[0] = names[0].lower()
                new_name = ":".join(names)

                if old_name != new_name:
                    node.text = new_name

                    log_debug("Fix string case from '%s' to '%s'" % (old_name, node.text))

                    return True
    return False

# 常量传播器类
class ConstantPropagator:

    def __init__(self):
        self._scope = Scope()
        self._loop_assigned = None
        self.replacements = []

    # 替换变量
    def _replace_var(self, parent_node, var_expression):
        var_name = var_expression.attrib["VariablePath"].lower()
        if self._loop_assigned is not None and var_name in self._loop_assigned:
            # 变量在循环中被修改，因此我们无法进行修改
            return

        value = self._scope.get_var(var_name)
        if value is not None:
            if isinstance(value, str):
                new_element = create_constant_string(value,
                                                     "BareWord" if parent_node.tag == "InvokeMemberExpressionAst"
                                                     else "DoubleQuoted")

                log_debug("Replace constant variable %s (string) in expression" % (
                    var_expression.attrib["VariablePath"]))

                self.replacements.append((var_expression, new_element))

            elif isinstance(value, (int, float)):
                new_element = create_constant_number(value)
                log_debug("Replace constant variable %s (number) in expression" % (
                    var_expression.attrib["VariablePath"]))
                self.replacements.append((var_expression, new_element))

            elif isinstance(value, list):
                new_element = create_array_literal_values(value)
                log_debug(
                    "Replace constant variable %s (array) in expression" % (var_expression.attrib["VariablePath"]))
                self.replacements.append((var_expression, new_element))

    # 传播常量
    def propagate(self, node):
        is_loop_tag = False

        if node.tag == "StatementBlockAst":
            self._scope.enter()

        elif node.tag in ["ForStatementAst", "ForEachStatementAst", "DoWhileStatementAst", "WhileStatementAst"]:
            if self._loop_assigned is None:
                # 一旦进入任何类型的循环，获取循环触及的变量集
                # 这包括任何嵌套的循环语句，所以我们只获取一次（直到我们离开最顶层的循环）
                self._loop_assigned = get_assigned_vars(node)
                is_loop_tag = True

        elif node.tag in ["AssignmentStatementAst"]:
            subnodes = list(node)
            if subnodes[0].tag == "VariableExpressionAst":
                variable = subnodes[0]
                if subnodes[1].tag == "CommandExpressionAst":
                    var_name = variable.attrib["VariablePath"].lower()
                    subnodes = list(subnodes[1])
                    if len(subnodes) == 1 and node.attrib["Operator"] == "Equals":
                        if subnodes[0].tag == "StringConstantExpressionAst":
                            self._scope.set_var(var_name, subnodes[0].text)
                        elif subnodes[0].tag == "ConstantExpressionAst":
                            self._scope.set_var(var_name, to_numeric(subnodes[0].text))
                        elif subnodes[0].tag == "ArrayLiteralAst":
                            self._scope.set_var(var_name, get_array_literal_values(subnodes[0]))
                        elif subnodes[0].tag == "VariableExpressionAst":
                            # $somevar = $var_that_is_constant;
                            self._replace_var(node, subnodes[0])
                    else:
                        self._scope.del_var(var_name)

        elif node.tag == "UnaryExpressionAst" and node.attrib["TokenKind"] in ["PostfixPlusPlus", "PostfixMinusMinus"]:
            subnodes = list(node)
            if subnodes[0].tag == "VariableExpressionAst":
                variable = subnodes[0]
                self._scope.del_var(variable.attrib["VariablePath"].lower())

        if node.tag in ["UnaryExpressionAst", "BinaryExpressionAst", "Arguments",
                        "InvokeMemberExpressionAst", "ConvertExpressionAst"]:
            subnodes = list(node)
            for subnode in subnodes:
                if subnode.tag == "VariableExpressionAst":
                    self._replace_var(node, subnode)

        for subnode in node:
            self.propagate(subnode)

        if is_loop_tag:
            self._loop_assigned = None

        if node.tag == "StatementBlockAst":
            self._scope.leave()

# 优化将常量变量替换为值函数
def opt_replace_constant_variable_by_value(ast):
    prop = ConstantPropagator() # 常量传播器
    prop.propagate(ast.getroot())

    if prop.replacements:
        parents = parent_map(ast) # 父节点
    for node, repl in prop.replacements:
        replace_node(ast, node, repl, parents=parents) # 替换节点

    return len(prop.replacements) != 0
   

# 优化转换无效循环函数
def opt_convert_bogus_loops(ast):
    """
    将末尾有一个无条件break的循环转换为if语句
    """
    for node in ast.iter():
        if node.tag == "WhileStatementAst" and len(node) == 2:
            if node[0].tag == "StatementBlockAst" and node[0][0].tag == "Statements":
                statements = node[0][0]
                last_break = statements[-1]
                if last_break.tag == "BreakStatementAst":
                    if any(stmt.tag in ["BreakStatementAst", "ContinueStatementAst"] and stmt != last_break
                           for stmt in statements.iter()):
                        # 循环中有另一个break/continue，因此我们不能转换这个循环
                        continue

                    statements.remove(last_break)

                    if_stmt = Element("IfStatementAst")
                    if_stmt.append(node[1])  # Condition
                    if_stmt.append(node[0])  # StatementBlockAst

                    log_debug("Converting while-loop to if-statement")
                    replace_node(ast, node, if_stmt)
                    return True

        elif node.tag == "ForStatementAst":
            assign_index = 0 if node[0].tag == "AssignmentStatementAst" else -1
            for block_index in range(assign_index + 1, 3):
                if node[block_index].tag == "StatementBlockAst":
                    break
            else:
                continue  # 不应该发生

            statements = node[block_index][0]
            if statements.tag != "Statements":
                continue

            last_break = statements[-1]
            if last_break.tag == "BreakStatementAst":
                if any(stmt.tag in ["BreakStatementAst", "ContinueStatementAst"] and stmt != last_break
                       for stmt in statements.iter()):
                    # 循环中有另一个break/continue，因此我们不能转换这个循环
                    continue

                statements.remove(last_break)

                cond_index = block_index + 1 if len(node) > block_index + 1 else -1
                if cond_index != -1:
                    if_stmt = Element("IfStatementAst")
                    if_stmt.append(node[cond_index])   # Condition
                    if_stmt.append(node[block_index])  # StatementBlockAst

                    log_debug("Converting for-loop to if-statement")
                    if assign_index != -1:
                        replace_node(ast, node, (node[assign_index], if_stmt))
                    else:
                        replace_node(ast, node, if_stmt)
                    return True

                else:
                    log_debug("Lifting for-loop without condition")
                    if assign_index != -1:
                        replace_node(ast, node, [node[assign_index]] + list(statements))
                    else:
                        replace_node(ast, node, list(statements))
                    return True

    return False

# 优化提升只有默认值的switch函数
def opt_lift_switch_with_just_default(ast):
    """
    switch (<nothing-with-potential-side-effects>) {
      default {
        ...
      }
    }
    """
    for node in ast.iter():
        if node.tag == "SwitchStatementAst" and len(node) == 2:
            if node[1].tag == "CommandExpressionAst" and node[1][0].tag in \
                    ["ConstantExpressionAst", "StringConstantExpressionAst", "VariableExpressionAst"]:
                if node[0].tag == "StatementBlockAst" and node[0][0].tag == "Statements":
                    replace_node(ast, node, list(node[0][0]))
                    return True

    return False
