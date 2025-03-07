# coding=utf-8
from xml.etree.ElementTree import Element

from plugins.logger import *
from plugins.special_vars import SPECIAL_VARS_VALUES
from plugins.utils import replace_node, create_array_literal_values


def opt_convert_type_to_type(ast):
    for node in ast.iter():
        if node.tag in ["ConvertExpressionAst"]:
            type_name = node.find("TypeConstraintAst")
            if type_name is not None:
                type_name = type_name.attrib["TypeName"].lower()

            if type_name in ["type"]:
                cst_string_node = node.find("StringConstantExpressionAst")
                if cst_string_node is not None:
                    type_value = cst_string_node.text

                    new_element = Element("StringConstantExpressionAst",
                                          {
                                              "StringConstantType": "BareWord",
                                              "StaticType": "string",
                                          })

                    new_element.text = "[" + type_value + "]"

                    log_debug("Replace type string '%s' by type '%s'" % (type_value, new_element.text))

                    replace_node(ast, node, new_element)

                    return True

# 转换类型为字符串
def opt_convert_type_to_string(ast):
    for node in ast.iter():
        
        """
        fix: 处理下列结构
        <ConvertExpressionAst>
            <TypeConstraintAst TypeName="xxx">
                xxx
            <TypeConstraintAst TypeName="xxx">
        </ConvertExpressionAst>
        """
        if node.tag in ["ConvertExpressionAst"]:
            type_name = node.find("TypeConstraintAst")
            
            if type_name is not None:
                type_name = type_name.attrib["TypeName"].lower()  # 获取 TypeName 属性值

            if type_name in ["string"]: # 如果 TypeName 为 string
                cst_string_node = node.find("VariableExpressionAst") # 获取 VariableExpressionAst 节点
                if cst_string_node is not None:
                    var_value = cst_string_node.attrib["VariablePath"]
             
                    if var_value.lower() in SPECIAL_VARS_VALUES and SPECIAL_VARS_VALUES[var_value.lower()] is not None:
                        log_debug("Use special variable value '%s' for $%s" % (
                                SPECIAL_VARS_VALUES[var_value.lower()], var_value))
                        var_value = SPECIAL_VARS_VALUES[var_value.lower()]

                    new_element = Element(f"StringConstantExpressionAst",
                                          {
                                              "StringConstantType": "SingleQuoted",
                                              "StaticType": "string",
                                          })

                    new_element.text = var_value

                    log_debug("Replace type of variable $%s to string" % (var_value))

                    replace_node(ast, node, new_element)

                    return True

                cst_string_node = node.find("StringConstantExpressionAst")
                if cst_string_node is not None:
                    log_debug("Remove unused cast to string for '%s'" % (cst_string_node.text))

                    replace_node(ast, node, cst_string_node)

                    return True
                
        """
        fix: 添加处理 IndexExpressionAst 的逻辑
        处理下列结构中的特殊变量 $xxx[xxx]
        <IndexExpressionAst>
            <VariableExpressionAst TypeName="xxx">
                <ConstantExpressionAst StaticType="int">
        </IndexExpressionAst>
        """
        if node.tag in ["IndexExpressionAst"]:
            var_node = node.find("VariableExpressionAst")
            index_node = node.find("ConstantExpressionAst")
        
            if var_node is not None and index_node is not None and index_node.attrib["StaticType"] == "int":
                var_value = var_node.attrib["VariablePath"]
                index_value = int(index_node.text)
            
                if var_value.lower() in SPECIAL_VARS_VALUES and SPECIAL_VARS_VALUES[var_value.lower()] is not None:
                    string_value = SPECIAL_VARS_VALUES[var_value.lower()]
                    if 0 <= index_value < len(string_value):
                        char_value = string_value[index_value]

                        new_element = Element("StringConstantExpressionAst",
                                    {
                                    "StringConstantType": "SingleQuoted",
                                    "StaticType": "string",
                                    })
                        new_element.text = char_value

                        log_debug("Replace index expression $%s[%d] with char '%s'" % (var_value, index_value, char_value))

                        replace_node(ast, node, new_element)

                        return True

        """
        fix: 添加处理多节特殊变量 $env.xxx[1,2,3] - join 'xxx' 的逻辑
        处理 BinaryExpressionAst
        <BinaryExpressionAst Operator="Join" StaticType="System.Object">
            <IndexExpressionAst StaticType="System.Object">
                <VariableExpressionAst VariablePath="xxx" StaticType="System.Object" />
                    <ArrayLiteralAst StaticType="System.Object[]">
                        <Elements>
                            <ConstantExpressionAst StaticType="int">4</ConstantExpressionAst>
                            <ConstantExpressionAst StaticType="int">26</ConstantExpressionAst>
                            <ConstantExpressionAst StaticType="int">25</ConstantExpressionAst>
                        </Elements>
                    </ArrayLiteralAst>
                </IndexExpressionAst>
            <StringConstantExpressionAst StringConstantType="SingleQuoted" StaticType="string">test</StringConstantExpressionAst>
        </BinaryExpressionAst>
        """
        if node.tag in ["BinaryExpressionAst"] and node.attrib.get("Operator") == "Join":
            index_expr = node.find("IndexExpressionAst")
            join_separator = node.find("StringConstantExpressionAst")
            
            # 验证结构是否符合 $var[1,2,3] + 空字符串 的模式
            if index_expr is not None and join_separator is not None:
                var_node = index_expr.find("VariableExpressionAst")
                array_node = index_expr.find("ArrayLiteralAst")
                
                if var_node is not None and array_node is not None:
                    # 提取多索引
                    elements = array_node.find("Elements")
                    indexes = []
                    if elements is not None:
                        for idx_node in elements.findall("ConstantExpressionAst"):
                            if idx_node.attrib.get("StaticType") == "int" and idx_node.text.isdigit():
                                indexes.append(int(idx_node.text))
                            else:
                                indexes = None
                                break
                    
                    # 处理特殊变量
                    if indexes is not None and len(indexes) > 0:
                        var_value = var_node.attrib["VariablePath"]
                        var_key = var_value.lower()
                        if var_key in SPECIAL_VARS_VALUES and (spec_value := SPECIAL_VARS_VALUES[var_key]):
                            # 验证索引有效性
                            if all(0 <= idx < len(spec_value) for idx in indexes):
                                # 生成拼接结果
                                joined_str = ''.join([spec_value[idx] for idx in indexes])
                                
                                if join_separator.text is not None:
                                    joined_str = joined_str + str(join_separator.text)
                                    
                                # 创建新节点
                                new_element = Element("StringConstantExpressionAst", {
                                    "StringConstantType": "SingleQuoted",
                                    "StaticType": "string",
                                })
                                new_element.text = joined_str
                                
                                # 替换整个 BinaryExpressionAst
                                log_debug(f"Replaced Join-Index ${var_value}[{indexes}] with '{joined_str}'")
                                replace_node(ast, node, new_element)
                                return True
           
           
        """
        fix: 添加处理多节特殊变量 $env.xxx[1,2,3] 的逻辑
        <IndexExpressionAst StaticType="System.Object">
            <VariableExpressionAst VariablePath="EnV:cOMSpEC" StaticType="System.Object" />
                <ArrayLiteralAst StaticType="System.Object[]">
                    <Elements>
                        <ConstantExpressionAst StaticType="int">4</ConstantExpressionAst>
                        <ConstantExpressionAst StaticType="int">26</ConstantExpressionAst>
                        <ConstantExpressionAst StaticType="int">25</ConstantExpressionAst>
                    </Elements>
                </ArrayLiteralAst>
        </IndexExpressionAst>
        """ 
        if node.tag in ["IndexExpressionAst"]:
            var_node = node.find("VariableExpressionAst")
            array_node = node.find("ArrayLiteralAst")
            
            if var_node is not None and array_node is not None:
                # 提取多索引
                elements = array_node.find("Elements")
                indexes = []
                if elements is not None:
                    for idx_node in elements.findall("ConstantExpressionAst"):
                        if idx_node.attrib.get("StaticType") == "int" and idx_node.text.isdigit():
                            indexes.append(int(idx_node.text))
                        else:
                            indexes = None
                            break
                
                # 处理特殊变量
                if indexes is not None and len(indexes) > 0:
                    var_value = var_node.attrib["VariablePath"]
                    var_key = var_value.lower()
                    if var_key in SPECIAL_VARS_VALUES and (spec_value := SPECIAL_VARS_VALUES[var_key]):
                        # 验证索引有效性
                        if all(0 <= idx < len(spec_value) for idx in indexes):
                            # 生成拼接结果
                            joined_str = ''.join([spec_value[idx] for idx in indexes])
                            # 创建新节点
                            new_element = Element("StringConstantExpressionAst", {
                                "StringConstantType": "SingleQuoted",
                                "StaticType": "string",
                            })
                            new_element.text = joined_str
                            
                            # 替换整个 IndexExpressionAst
                            log_debug(f"Replaced Index ${var_value}[{indexes}] with '{joined_str}'")
                            replace_node(ast, node, new_element)
                            return True
    return False


def opt_convert_type_to_array(ast):
    for node in ast.iter():
        if node.tag in ["ConvertExpressionAst"]:
            type_name = node.find("TypeConstraintAst")
            if type_name is not None:
                type_name = type_name.attrib["TypeName"].lower()

            if type_name == "array":
                cst_string_node = node.find("StringConstantExpressionAst")
                if cst_string_node is not None:
                    log_debug("Replace array of one string to string '%s'" % cst_string_node.text)

                    replace_node(ast, node, cst_string_node)

            elif type_name == "char[]":
                cst_string_node = node.find("StringConstantExpressionAst")
                if cst_string_node is not None:
                    arrayed = [c for c in cst_string_node.text]

                    new_array_ast = create_array_literal_values(arrayed)

                    log_debug("Replace (cast) string to array: '%s'" % arrayed)

                    replace_node(ast, node, new_array_ast)


def opt_convert_type_to_char(ast):
    for node in ast.iter():
        if node.tag in ["ConvertExpressionAst"]:
            type_name = node.find("TypeConstraintAst")
            if type_name is not None:
                type_name = type_name.attrib["TypeName"].lower()

            if type_name == "char":
                cst_int_node = node.find("ConstantExpressionAst")

                if cst_int_node is not None and cst_int_node.attrib["StaticType"] == "int":
                    type_value = int(cst_int_node.text)

                    new_element = Element("StringConstantExpressionAst",
                                          {
                                              "StringConstantType": "SingleQuoted",
                                              "StaticType": "string",
                                          })
                    new_element.text = chr(type_value)

                    log_debug("Replace integer %d convertion to char '%s'" % (type_value, new_element.text))

                    replace_node(ast, node, new_element)

                    return True

    return False


def opt_convert_type_to_int(ast):
    for node in ast.iter():
        if node.tag in ["ConvertExpressionAst"]:
            type_name = node.find("TypeConstraintAst")
            if type_name is not None:
                type_name = type_name.attrib["TypeName"].lower()

            if type_name == "int":
                cst_int_node = node.find("ConstantExpressionAst")

                if cst_int_node is not None and cst_int_node.attrib["StaticType"] == "int":
                    log_debug("Remove no-op integer conversion")

                    replace_node(ast, node, cst_int_node)

                    return True

    return False
