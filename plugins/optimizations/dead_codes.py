# coding=utf-8
from plugins.logger import log_debug, log_err
from plugins.operators import do_const_comparison
from plugins.utils import create_constant_number, parent_map, replace_node, \
    is_prefixed_var, get_used_vars, to_numeric

# 优化未使用变量函数
def opt_unused_variable(ast):
    parents = parent_map(ast)
    used_vars = get_used_vars(ast)
    kill_list = []

    for node in ast.iter():
        if node.tag in ["AssignmentStatementAst"]:
            subnodes = list(node)
            if subnodes[0].tag == "VariableExpressionAst":
                if subnodes[0].attrib["VariablePath"].lower() not in used_vars:
                    if not is_prefixed_var(subnodes[0].attrib["VariablePath"]):
                        log_debug("Remove assignment of unused variable %s" % (subnodes[0].attrib["VariablePath"]))
                        kill_list.append(node)

    for node in kill_list:
        parents[node].remove(node)

    return len(kill_list) != 0

# 优化移除未初始化变量使用函数
def opt_remove_uninitialised_variable_usage(ast):
    assigned = set()
    kill_list = []
    replacements = []

    """
    FIXME 这个函数会导致以下结构的无效输出
    $i = 2;
    while ($i -gt 0) {
      $unassgn = $unassn + 4;
      $i--;
    }
    Write-Host $unassgn
    """

    for node in ast.iter():
        if node.tag in ["AssignmentStatementAst"]:
            subnodes = list(node)
            if subnodes[1].tag == "CommandExpressionAst" and subnodes[1][0].tag == "VariableExpressionAst":
                var_source = subnodes[1][0].attrib["VariablePath"].lower()
                if var_source not in assigned:
                    if not is_prefixed_var(var_source) and var_source != "_":
                        try:
                            var_dest = subnodes[0].attrib["VariablePath"].lower()
                            log_debug(f"Remove variable '{var_dest}' assigned from unassigned variable '{var_source}'")
                            kill_list.append(node)
                            continue
                        except KeyError:
                            pass

            if subnodes[0].tag == "VariableExpressionAst":
                assigned.add(subnodes[0].attrib["VariablePath"].lower())

        elif node.tag in ["ParameterAst"]:
            var_expr = node.find("VariableExpressionAst")
            if var_expr is not None:
                assigned.add(var_expr.attrib["VariablePath"].lower())

        elif node.tag in ["BinaryExpressionAst"]:
            subnodes = list(node)

            operator = node.attrib["Operator"]

            if subnodes[0].tag == "VariableExpressionAst":
                variable = subnodes[0]
                other = subnodes[1]
            elif subnodes[1].tag == "VariableExpressionAst":
                variable = subnodes[1]
                other = subnodes[0]
            else:
                variable, other = None, None

            if variable is not None and other is not None:
                if variable.attrib["VariablePath"].lower() not in assigned:
                    if not is_prefixed_var(variable.attrib["VariablePath"]):
                        if operator == "Plus":
                            replacements.append((node, other))
                        elif operator in ["Minus", "Multiply"] and other.tag == "ConstantExpressionAst":
                            replacements.append((variable, create_constant_number(0)))
                        else:
                            continue

                        log_debug("Remove unassigned variable use '%s'" % (variable.attrib["VariablePath"]))

    if kill_list or replacements:
        parents = parent_map(ast)

    for node in kill_list:
        parents[node].remove(node)

    for node, repl in replacements:
        replace_node(ast, node, repl, parents=parents)

    return len(kill_list) + len(replacements) != 0

# 优化移除无效的switch case函数
def opt_remove_dead_switch_cases(ast):
    """
    移除27和28
    switch (48) {
        27 { ... }
        28 { ... }
        ($foo + 4) { ... }
        default { ... }
    }
    """
    kill_list = []
    replacements = []

    for node in ast.iter():
        if node.tag == "SwitchStatementAst":
            switch_expr = node[-1]
            if switch_expr.tag != "CommandExpressionAst" or \
               switch_expr[0].tag not in ["ConstantExpressionAst", "StringConstantExpressionAst"]:
                continue

            switch_val = switch_expr[0].text
            kill_counter = 0

            label = block = None
            for i, subnode in enumerate(node[:-1]):
                if i > 0 and subnode.tag == "StatementBlockAst" and node[i - 1].tag != "StatementBlockAst":
                    label = node[i - 1]
                    block = subnode

                    if label.tag in ["ConstantExpressionAst", "StringConstantExpressionAst"]:
                        if label.text != switch_val:
                            kill_list.extend((label, block))
                            kill_counter += 2
                        elif label.text == switch_val and block[0].tag == "Statements":
                            # 找到匹配的case
                            replacements.append((node, list(block[0])))
                            break

            # 如果移除了除switch表达式外的所有内容，则需要移除整个switch
            if kill_counter == len(node) - 1:
                kill_list.append(node)

    if kill_list or replacements:
        parents = parent_map(ast)

    for node in kill_list:
        parents[node].remove(node)

    for node, repl in replacements:
        replace_node(ast, node, repl, parents=parents)

    return len(kill_list) + len(replacements) != 0

# 获取常量二元表达式结果函数
def _get_const_binary_expression_result(node):
    if node.tag == "CommandExpressionAst" and node[0].tag == "BinaryExpressionAst":
        bin_expr = node[0]
        if bin_expr[0].tag == "ConstantExpressionAst" and bin_expr[1].tag == "ConstantExpressionAst":
            a = to_numeric(bin_expr[0].text)
            b = to_numeric(bin_expr[1].text)
            return do_const_comparison(a, b, bin_expr.attrib["Operator"])
        
    return None

# 优化移除无效循环函数
def opt_remove_dead_loops(ast):
    kill_list = []
    replacements = []

    for node in ast.iter():
        if node.tag == "ForStatementAst":
            # 移除类似 "for ($x = 0; $x -gt 4; $x++) {}" 的语句
            # 保留初始赋值，因为它可能在其他地方被访问
            subnodes = list(node)
            assign = subnodes[0]
            if assign.tag != "AssignmentStatementAst" or assign.attrib["Operator"] != "Equals":
                continue

            if assign[0].tag != "VariableExpressionAst" or assign[1].tag != "CommandExpressionAst":
                continue

            if assign[1][0].tag != "ConstantExpressionAst":
                continue
            
            cond = subnodes[-1]
            if cond.tag != "CommandExpressionAst" or cond[0].tag != "BinaryExpressionAst":
                continue

            bin_expr = cond[0]

            var_name = assign[0].attrib["VariablePath"].lower()
            var_val = to_numeric(assign[1][0].text)
            operator = bin_expr.attrib["Operator"]

            # 检查形式 "$x OP const" 或 "const OP $x"
            if bin_expr[0].tag == "VariableExpressionAst" and bin_expr[1].tag == "ConstantExpressionAst":
                if bin_expr[0].attrib["VariablePath"].lower() != var_name:
                    continue

                cmp_val = to_numeric(bin_expr[1].text)
                cmp_res = do_const_comparison(var_val, cmp_val, operator)
            elif bin_expr[0].tag == "ConstantExpressionAst" and bin_expr[1].tag == "VariableExpressionAst":
                if bin_expr[1].attrib["VariablePath"].lower() != var_name:
                    continue

                cmp_val = to_numeric(bin_expr[0].text)
                cmp_res = do_const_comparison(cmp_val, var_val, operator)
            else:
                continue

            if cmp_res is not None and not cmp_res:
                log_debug(f"Remove dead For loop '{node.attrib['Condition']}'")
                replacements.append((node, assign))

        elif node.tag == "WhileStatementAst":
            # 移除无法进入的While语句（例如 "65 -gt 100"）
            cond = node[1]
            if cond.tag != "CommandExpressionAst" or cond[0].tag != "BinaryExpressionAst":
                continue

            bin_expr = cond[0]
            if bin_expr[0].tag == "ConstantExpressionAst" and bin_expr[1].tag == "ConstantExpressionAst":
                a = to_numeric(bin_expr[0].text)
                b = to_numeric(bin_expr[1].text)
                cmp_res = do_const_comparison(a, b, bin_expr.attrib["Operator"])

                if cmp_res is not None and not cmp_res:
                    log_debug(f"Remove dead While loop '{node.attrib['Condition']}'")
                    kill_list.append(node)

    if kill_list or replacements:
        parents = parent_map(ast)

    for node in kill_list:
        parents[node].remove(node)

    for node, repl in replacements:
        replace_node(ast, node, repl, parents=parents)

    return len(kill_list) + len(replacements) != 0

# 优化移除无效if子句函数
def opt_remove_dead_if_clauses(ast):
    kill_list = []
    replacements = []

    for node in ast.iter():
        if node.tag == "IfStatementAst":
            first_cond = node[0]
            first_block = node[1]

            cmp_res = _get_const_binary_expression_result(first_cond)
            if cmp_res is not None and cmp_res:
                # If总是进入，因此用第一个块的内容替换它
                if first_block.tag == "StatementBlockAst" and first_block[0].tag == "Statements":
                    replacements.append((node, list(first_block[0])))
                    continue

            # 查找条件为假的子句并删除它们
            kill_counter = 0
            for i in range(0, len(node), 2):
                if node[i].tag == "StatementBlockAst":
                    break

                cmp_res = _get_const_binary_expression_result(node[i])
                if cmp_res is not None and not cmp_res:
                    kill_list.extend((node[i], node[i + 1]))
                    kill_counter += 2

            if kill_counter == len(node) - 1:
                # 只剩下 "else {}"，因此提升其内容，否则我们将有一个无效的AST
                if node[-1].tag == "StatementBlockAst" and node[-1][0].tag == "Statements":
                    replacements.append((node, list(node[-1][0])))
                else:
                    log_err("Got only an else clause left, but structure was unknown")
                    return False

            elif kill_counter == len(node):
                # 所有条件为假，没有else -> 整个If消失
                kill_list.append(node)

    if kill_list or replacements:
        parents = parent_map(ast)

    for node in kill_list:
        parents[node].remove(node)

    for node, repl in replacements:
        replace_node(ast, node, repl, parents=parents)

    return len(kill_list) + len(replacements) != 0
