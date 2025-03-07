# coding=utf-8
from types import SimpleNamespace

from plugins.logger import log_info, log_debug
from plugins.optimizations.alias import opt_alias
from plugins.optimizations.binary_expressions import opt_binary_expression_plus, opt_binary_expression_format, \
    opt_binary_expression_replace, opt_binary_expression_join, opt_binary_expression_numeric_operators
from plugins.optimizations.complex_operations import opt_value_of_const_array
from plugins.optimizations.dead_codes import opt_unused_variable, opt_remove_uninitialised_variable_usage, \
    opt_remove_dead_loops, opt_remove_dead_switch_cases, opt_remove_dead_if_clauses
from plugins.optimizations.empty_nodes import opt_remove_empty_nodes
from plugins.optimizations.invoke_member import opt_invoke_split_string, opt_invoke_replace_string, \
    opt_invoke_reverse_array, opt_invoke_expression
from plugins.optimizations.replace_long_names import opt_long_variable_names
from plugins.optimizations.simplifications import opt_convert_bogus_loops, opt_simplify_paren_single_expression, \
    opt_bareword_case, opt_constant_string_type, opt_prefixed_variable_case, opt_replace_constant_variable_by_value, \
    opt_simplify_single_array, opt_simplify_pipeline_single_command, opt_type_constraint_from_convert, \
    opt_command_element_as_bareword, opt_type_constraint_case, opt_special_variable_case, \
    opt_lift_switch_with_just_default
from plugins.optimizations.type_convertions import opt_convert_type_to_int, opt_convert_type_to_type, \
    opt_convert_type_to_char, opt_convert_type_to_array, opt_convert_type_to_string
from plugins.optimizations.unary_expressions import opt_unary_expression_join

"""
fix: 增加处理函数
"""
from plugins.optimizations.variable_expressions import opt_variable_expression_replace, opt_variable_expression_split


def optimize_pass(ast, stats):
    # 定义优化函数列表
    optimizations = [
        # 移除节点 - empty_nodes.py
        opt_remove_empty_nodes, # 移除空节点
        opt_unused_variable, # 移除未使用的变量
        opt_simplify_paren_single_expression, # 简化括号表达式 
        opt_simplify_pipeline_single_command, # 简化管道表达式
        opt_simplify_single_array, # 简化数组表达式
        opt_remove_uninitialised_variable_usage, # 移除未初始化的变量 
        opt_remove_dead_switch_cases, # 移除死代码
        opt_remove_dead_loops, # 移除死循环
        opt_remove_dead_if_clauses, # 移除死代码
        # 表达式优化 - binary_expressions.py
        opt_unary_expression_join, 
        opt_binary_expression_plus, 
        opt_binary_expression_format, 
        opt_binary_expression_replace, 
        # ================== Fix ==================
        opt_variable_expression_replace,  # 处理动态变量替换 - 有些许问题
        opt_variable_expression_split,    # 处理变量拆分
        # =========================================
        opt_binary_expression_join,
        opt_binary_expression_numeric_operators,
        # 调用成员优化 - invoke_member.py
        opt_invoke_split_string,
        opt_invoke_replace_string,
        opt_invoke_reverse_array,
        opt_invoke_expression,
        # 类型转换优化 - type_convertions.py
        opt_convert_type_to_type,
        opt_convert_type_to_string,  # fix: 修复类型转换
        opt_convert_type_to_int,
        opt_convert_type_to_char,
        opt_convert_type_to_array,
        # 复杂操作优化 - complex_operations.py
        opt_value_of_const_array,
        # 语法简化优化 - simplifications.py
        opt_long_variable_names,
        opt_prefixed_variable_case,
        opt_bareword_case,
        opt_constant_string_type,
        opt_special_variable_case,
        opt_type_constraint_from_convert,
        opt_command_element_as_bareword,
        opt_type_constraint_case,
        opt_alias,
        opt_convert_bogus_loops,
        opt_lift_switch_with_just_default, # 移除 switch 语句
        # 最后执行 - simplifications.py
        opt_replace_constant_variable_by_value,
    ]

    # 逐个应用优化函数
    for opt in optimizations:
        did_opt = False
        while opt(ast):
            stats.steps += 1
            did_opt = True
        if did_opt:
            return True

    return False


class Optimizer:
    def __init__(self):
        self.stats = SimpleNamespace()
        setattr(self.stats, "steps", 0)

    def optimize(self, ast):
        # 计算输入节点数量
        count_in = sum(1 for _ in ast.getroot().iter())
        log_debug(f"{count_in} nodes loaded")

        # 不断应用优化直到没有更多优化可以应用
        while optimize_pass(ast, self.stats):
            pass

        log_info(f"{self.stats.steps} optimization steps executed")

        # 计算输出节点数量
        count_out = sum(1 for _ in ast.getroot().iter())
        ratio = "{:02.2f}".format(count_out / count_in * 100.00)
        log_debug(f"{count_out} nodes in output ({ratio}%)")

        return ast