# coding=utf-8
import re
import base64
from types import SimpleNamespace
from xml.etree.ElementTree import Element

from plugins.escaped_chars import escape_string
from plugins.logger import log_warn, log_err, log_info
from plugins.operators import OPS
from plugins.utils import parent_map, is_powershell_code, is_utf8_readable_base64
from plugins.barewords import *
from plugins.logger import *



class Rebuilder:
    def __init__(self, output_filename):
        self.stats = SimpleNamespace()
        setattr(self.stats, "nodes", 0)

        self._level = 0
        self._indent = 3

        self._parent_map = {}

        self.output_filename = output_filename

    @staticmethod
    def lastNode(node):
        return node.find('..')

    @staticmethod
    def lastWrite(node):
        n = node
        while n.tag in ["PipelineAst", "PipelineElements", "CommandAst", "CommandElements"]:
            try:
                n = list(n)[-1]
            except IndexError:
                pass
        return n

    def indent(self):
        self.output.write(" " * self._indent * self._level)

    def write(self, s):
        self.output.write(s)

    def rebuild_operator(self, op):
        if op in OPS:
            self.write(OPS[op])
        else:
            log_err(f"Operator {op} not supported")
            
            
    """
    fix: 针对 hex 编码的字符串进行解码
    """
    @staticmethod
    def is_hex_readable(hex_string):
        try:
            if hex_string is not None:
                decoded_bytes = bytes.fromhex(hex_string)
                decoded_str = decoded_bytes.decode("utf-8")
                if decoded_str.isprintable() and decoded_bytes != b'':  # 检测是否为可读文本
                    log_warn("Detected hex encoded string, this may not work correctly")
                    log_warn("Decoded string: %s" % decoded_str)
                    return decoded_str
            return False
        except Exception:
            return False
        
    """
    fix: 增加对 ps1 节点处理的替换逻辑
    """
    def process_ps1_code(self, node, stripped_text):
        log_warn(f"PowerShell code string format encoding detected: {stripped_text}")
        # 创建新节点并替换
        new_node = Element("CommandElementAst", {
            "Value": stripped_text,
            "StaticType": "string"
        })
        
        # 执行节点替换（需要确保replace_node能正确处理）
        self._replace_current_node(node, new_node)
        
        # 处理新节点
        self.write(escape_string(stripped_text, mode="BareWord"))
        log_debug(f"Converted to BareWord: {stripped_text}")
        return  # 终止当前节点处理
    
    
    """
    fix: 处理当前节点的替换逻辑
    """
    def _replace_current_node(self, old_node, new_node):
        
        parent = self._parent_map.get(old_node)
        if parent is not None:
            index = list(parent).index(old_node)
            parent[index] = new_node
            # 更新父映射
            self._parent_map[new_node] = parent
            
    def _rebuild_internal(self, node, **kwargs):
        self.stats.nodes += 1

        if node.tag in ["NamedBlockAst"]:
            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["PipelineAst"]:
            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["Redirections", "UsingStatements"]:
            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["Attributes"]:
            if typename := node.find("TypeConstraintAst"):
                self._rebuild_internal(typename)

            if attribute := node.find("AttributeAst"):
                self._rebuild_internal(attribute)
                self.write("\n")

        elif node.tag in ["AttributeAst"]:
            subnodes = list(node)

            self.indent()
            self.write(f"[{node.attrib['TypeName']}]")

            have_args = False
            for subnode in subnodes:
                if len(list(subnode)) > 0:
                    have_args = True
                    break

            if have_args:
                self.write("(")

            for subnode in subnodes:
                self._rebuild_internal(subnode)

            if have_args:
                self.write(")")

        elif node.tag in ["NamedAttributeArgumentAst"]:
            self.write(f"{node.attrib['ArgumentName']}")
            self.write("=")
            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["NamedArguments"]:
            for i, subnode in enumerate(node):
                if i > 0:
                    self.write(", ")
                self._rebuild_internal(subnode)

        elif node.tag in ["ParamBlockAst"]:
            subnodes = list(node)
            if subnodes[0].tag == "Attributes":
                self._rebuild_internal(subnodes[0])
                subnodes.pop(0)

            self.indent()
            self.write("param")

            if node in self._parent_map:
                self.write("\n")
                self.indent()
                self.write("(\n")
                self._level += 1

            for subnode in subnodes:
                self._rebuild_internal(subnode)

            if node in self._parent_map:
                self._level -= 1
                self.indent()
                self.write(")\n")

        elif node.tag in ["PipelineElements"]:
            subnodes = list(node)

            for i, subnode in enumerate(subnodes):
                if i > 0:
                    self.write(" | ")
                self._rebuild_internal(subnode)

        elif node.tag in ["CommandAst"]:
            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["CommandElements"]:
            for i, subnode in enumerate(node):
                self._rebuild_internal(subnode)
                if i < len(node) - 1:
                    self.write(" ")

        elif node.tag in ["Statements"]:
            subnodes = list(node)

            for i, subnode in enumerate(subnodes):
                self.indent()
                self._rebuild_internal(subnode)
                if subnode.tag not in ["IfStatementAst", "ForStatementAst", "TryStatementAst", "ForEachStatementAst",
                                       "PipelineAst", "DoWhileStatementAst", "WhileStatementAst", "SwitchStatementAst"]:
                    self.write(";\n")
                elif subnode.tag in ["PipelineAst"]:
                    if self.lastWrite(subnode).tag not in ["ScriptBlockExpressionAst"]:
                        self.write(";\n")

        elif node.tag in ["Elements"]:
            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["ParenExpressionAst"]:
            self.write("(")
            for subnode in node:
                self._rebuild_internal(subnode)
            self.write(")")

        elif node.tag in ["NestedAst"]:
            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["CommandExpressionAst"]:
            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["CommandParameterAst"]:
            self.write(f"-{node.attrib['ParameterName']}")

            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["ErrorExpressionAst", "ErrorStatementAst"]:
            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["ForStatementAst"]:
            self.write("\n")

            subnodes = list(node)

            block_index = -1
            for i, subnode in enumerate(subnodes):
                if subnode.tag == "StatementBlockAst":
                    block_index = i
                    break
            else:
                log_err("ForStatementAst without StatementBlockAst")
                return

            if block_index == 0:
                # for (;;?) {}
                assign_index = -1
                update_index = -1
            elif block_index == 2:
                # for (x;y;?) {}
                assign_index = 0
                update_index = 1
            elif subnodes[0].tag in ["PipelineAst", "CommandExpressionAst"]:  # format vs. deob
                # for (;y;?) {}
                assign_index = -1
                update_index = 0
            else:
                # for (x;;?) {}
                assign_index = 0
                update_index = -1

            self.indent()
            self.write("for (")
            if assign_index != -1:
                self._rebuild_internal(subnodes[assign_index])
            self.write("; ")
            if len(subnodes) > block_index + 1:
                self._rebuild_internal(subnodes[block_index + 1])
            self.write("; ")
            if update_index != -1:
                self._rebuild_internal(subnodes[update_index])
            self.write(")\n")

            self._rebuild_internal(subnodes[block_index])

        elif node.tag in ["ForEachStatementAst"]:
            self.write("\n")

            subnodes = list(node)

            self.indent()
            self.write("foreach(")
            self._rebuild_internal(subnodes[0])
            self.write(" in ")
            self._rebuild_internal(subnodes[2])
            self.write(")\n")

            self._rebuild_internal(subnodes[1])

        elif node.tag in ["ReturnStatementAst"]:
            self.write("return ")
            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["PositionalArguments"]:
            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["ParameterAst"]:
            subnodes = list(node)
            if subnodes[0].tag == "Attributes":
                self._rebuild_internal(subnodes[0])
                subnodes.pop(0)

            if len(subnodes) == 1:
                self.indent()
                self._rebuild_internal(subnodes[0])
            elif len(subnodes) == 2:
                self.indent()
                self.write(f"[{node.attrib['StaticType']}]")
                self._rebuild_internal(subnodes[0])
                self.write(" = ")
                self._rebuild_internal(subnodes[1])

        elif node.tag in ["Parameters"]:
            for i, subnode in enumerate(node):
                self._rebuild_internal(subnode)
                if i < len(list(node)) - 1:
                    self.write(", ")
                if "inline" not in kwargs:
                    self.write("\n")

        elif node.tag in ["ScriptBlockExpressionAst", "ScriptBlockAst"]:
            if node in self._parent_map:
                self.indent()
                self.write("{\n")
                self._level += 1

            for subnode in node:
                self._rebuild_internal(subnode)

            if node in self._parent_map:
                self._level -= 1
                self.indent()
                self.write("}\n")

        elif node.tag in ["StatementBlockAst"]:
            if node not in self._parent_map or self._parent_map[node].tag != "SwitchStatementAst":
                self.indent()
            else:
                self.write(" ")
            self.write("{\n")

            self._level += 1

            for subnode in node:
                self._rebuild_internal(subnode)

            self._level -= 1

            self.indent()
            self.write("}\n")

        elif node.tag in ["CatchClauses"]:
            self.indent()
            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["CatchClauseAst"]:
            self.write("catch\n")

            for subnode in node:
                self._rebuild_internal(subnode)

        elif node.tag in ["BreakStatementAst"]:
            self.write("break")

        elif node.tag in ["TypeConstraintAst"]:
            self.write("[" + node.attrib["TypeName"] + "]")

        elif node.tag in ["TypeExpressionAst"]:
            self.write("[" + node.attrib["TypeName"] + "]")

        elif node.tag in ["ConvertExpressionAst"]:
            to_type = node.find("TypeConstraintAst")
            self._rebuild_internal(to_type)

            for subnode in node:
                if subnode.tag not in ["TypeConstraintAst"]:
                    self._rebuild_internal(subnode)

        elif node.tag in ["Arguments"]:
            subnodes = list(node)
            for i, subnode in enumerate(subnodes):
                if i > 0:
                    self.write(", ")
                self._rebuild_internal(subnode)

        elif node.tag in ["ArrayExpressionAst"]:
            statement_block = list(node)[0]
            statements_node = list(statement_block)[0]
            statements = list(statements_node)
            if len(statements) > 0:
                self._rebuild_internal(statements[0])
            else:
                self.write("@()")

        elif node.tag in ["ArrayLiteralAst"]:
            subnodes = list(list(node)[0])
            self.write("@(")
            for i, subnode in enumerate(subnodes):
                if i > 0:
                    self.write(", ")
                self._rebuild_internal(subnode)
            self.write(")")

        elif node.tag in ["VariableExpressionAst"]:
            self.write("$" + node.attrib["VariablePath"])

        elif node.tag in ["AssignmentStatementAst"]:
            subnodes = list(node)
            self._rebuild_internal(subnodes[0])

            self.rebuild_operator(node.attrib["Operator"])

            self._rebuild_internal(subnodes[1])

        elif node.tag in ["UnaryExpressionAst"]:
            kind = node.attrib["TokenKind"]

            if kind not in ["PostfixPlusPlus", "PostfixMinusMinus"]:
                self.rebuild_operator(kind)

            for subnode in node:
                self._rebuild_internal(subnode)

            if kind in ["PostfixPlusPlus", "PostfixMinusMinus"]:
                self.rebuild_operator(kind)

        elif node.tag in ["ExitStatementAst"]:
            self.write("exit")

        elif node.tag in ["ContinueStatementAst"]:
            self.write("continue")

        elif node.tag in ["HashtableAst"]:
            self.write("@{ ")

            for i, subnode in enumerate(node):
                self._rebuild_internal(subnode)
                if i < len(list(node)) - 1:
                    self.write(" = ")

            self.write(" }")

        elif node.tag in ["FunctionDefinitionAst"]:
            subnodes = list(node)

            if len(subnodes) == 2:
                self.write(f"function {node.attrib['Name']}")
                self.write("(")
                self._rebuild_internal(subnodes[0], inline=True)
                self.write(")")
                self._rebuild_internal(subnodes[1])
            elif len(subnodes) == 1:
                self.write(f"function {node.attrib['Name']}")
                self._rebuild_internal(subnodes[0])

        elif node.tag in ["BinaryExpressionAst"]:
            subnodes = list(node)
            self._rebuild_internal(subnodes[0])

            self.rebuild_operator(node.attrib["Operator"])

            self._rebuild_internal(subnodes[1])

        elif node.tag in ["ConstantExpressionAst"]:
            if node.attrib["StaticType"] in ["int", "long", "decimal", "double"]:
                self.write(node.text)
 
        elif node.tag in ["StringConstantExpressionAst", "ExpandableStringExpressionAst"]: # Fix
            """
            fix: 优化对 字符串是否为 powershell 代码的判断
            """
            original_text = node.text or ""
            stripped_text = original_text.strip("'\"")
            
            # 使用增强检测逻辑
            is_ps = is_powershell_code(stripped_text)
            is_hex_str = self.is_hex_readable(stripped_text)
            is_bs64 = is_utf8_readable_base64(stripped_text)
            
            new_text = stripped_text 
            process_times = 0
            while is_bs64 is not False or is_hex_str is not False or is_ps is not False: # 处理多层混淆情况
                
                if is_bs64 is not False : # base64 编码
                    new_text = is_bs64
                    process_times += 1
                    is_ps = is_powershell_code(new_text)
                    is_hex_str = self.is_hex_readable(new_text)
                    is_bs64 = is_utf8_readable_base64(new_text)
                    continue
                    
                if is_hex_str is not False and is_hex_str: # hex 编码
                    new_text = is_hex_str
                    process_times += 1
                    is_ps = is_powershell_code(new_text)
                    is_hex_str = self.is_hex_readable(new_text)
                    continue
                
                if is_ps is not False: # PowerShell 代码
                    if process_times != 0 :
                        self.process_ps1_code(node, new_text)
                    
                    break  # 当处理到为代码时应为循环最后一个混淆，此时退出
            
            string_type = node.attrib["StringConstantType"]
            if string_type == "BareWord":
                self.write(escape_string(new_text, mode="BareWord"))
            elif string_type == "SingleQuoted":
                self.write(f"'{escape_string(new_text, mode='SingleQuoted')}'")
            elif string_type == "DoubleQuoted":
                self.write(f'"{escape_string(new_text, mode="DoubleQuoted")}"')
            elif string_type == "SingleQuotedHereString":
                self.write(f"@'{new_text}'@")

        elif node.tag in ["IndexExpressionAst"]:
            subnodes = list(node)
            self._rebuild_internal(subnodes[0])
            self.write("[")
            self._rebuild_internal(subnodes[1])
            self.write("]")

        elif node.tag in ["MemberExpressionAst"]:
            subnodes = list(node)

            self._rebuild_internal(subnodes[0])
            if node.attrib["Static"] == "True":
                self.write("::")
            else:
                self.write(".")
            self._rebuild_internal(subnodes[1])

        elif node.tag in ["TryStatementAst"]:
            subnodes = list(node)

            self.write("try\n")

            self._rebuild_internal(subnodes[0])
            self._rebuild_internal(subnodes[1])

        elif node.tag in ["IfStatementAst"]:
            subnodes = list(node)
            self.write("if (")
            self._rebuild_internal(subnodes[0])
            self.write(")\n")

            self._rebuild_internal(subnodes[1])

            i = 2
            while len(subnodes) > i:
                self.indent()

                if len(subnodes) > i + 1:
                    self.write("elseif (")
                    self._rebuild_internal(subnodes[i])
                    self.write(")\n")
                    i += 1
                else:
                    self.write("else\n")

                self._rebuild_internal(subnodes[i])
                i += 1
                if i == len(subnodes):
                    self.write("\n")

        elif node.tag in ["InvokeMemberExpressionAst"]:

            subnodes = list(node)
            if len(subnodes) == 3:

                for i, subnode in enumerate(subnodes[1:]):
                    if i > 0:
                        if node.attrib["Static"] == "True":
                            self.write("::")
                        else:
                            self.write(".")

                    self._rebuild_internal(subnode)

                self.write('(')
                self._rebuild_internal(subnodes[0])
                self.write(')')

            elif len(subnodes) == 2:

                self._rebuild_internal(subnodes[0])

                if node.attrib["Static"] == "True":
                    self.write("::")
                else:
                    self.write(".")

                self._rebuild_internal(subnodes[1])
                """
                bug: 可能会存在些许问题
                """
                self.write('(')
                self.write(')')

        elif node.tag in ["DoWhileStatementAst"]:
            subnodes = list(node)
            self.write("do ")
            self._rebuild_internal(subnodes[0])
            self.write("while (")
            self._rebuild_internal(subnodes[1])
            self.write(")\n")

        elif node.tag in ["WhileStatementAst"]:
            subnodes = list(node)
            self.write("while (")
            self._rebuild_internal(subnodes[1])
            self.write(")\n")
            self._rebuild_internal(subnodes[0])

        elif node.tag in ["SwitchStatementAst"]:
            flags = ""
            if node.attrib["Flags"] != "None":
                flags = "-" + node.attrib["Flags"] + " "

            subnodes = list(node)
            self.write("switch " + flags + "(")
            self._rebuild_internal(subnodes[-1])
            self.write(") {\n")
            self._level += 1

            default_index = -1
            for i, subnode in enumerate(subnodes):
                if subnode.tag == "StatementBlockAst" and \
                   ((i > 0 and subnodes[i - 1].tag == "StatementBlockAst") or len(subnodes) == 2):
                    default_index = i
                    break

            for i, subnode in enumerate(subnodes[:-1]):
                if subnode.tag != "StatementBlockAst":
                    self.indent()
                elif i == default_index:
                    self.indent()
                    self.write("default")
                self._rebuild_internal(subnode)

            self._level -= 1
            self.indent()
            self.write("}\n")

        elif node.tag in ["SubExpressionAst"]:
            self.write("$(")

            subnodes = list(node)
            if subnodes:
                self._level += 1

                if subnodes[0].tag == "StatementBlockAst":
                    self._rebuild_internal(subnodes[0][0])
                else:
                    log_warn(f"{subnodes[0].tag} unsupported in SubExpressionAst")

                self._level -= 1
                self.indent()

            self.write(")")

        else:
            log_warn(f"NodeType: {node.tag} unsupported")

    def rebuild(self, node):
        self.stats.nodes = 0
        self._parent_map = parent_map(node)

        log_info(f"Rebuilding script to: {self.output_filename}")

        with open(self.output_filename, "w") as self.output:
            self._rebuild_internal(node)

            log_info(f"{self.stats.nodes} nodes traversed")
            log_info(f"{self.output.tell()} bytes written")
