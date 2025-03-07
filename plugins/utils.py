# coding=utf-8
import errno
import glob
import os
import platform
import shutil
import sys
import re
import base64
from xml.etree.ElementTree import Element

from plugins.logger import *
from plugins.barewords import BAREWORDS_PATTERNS


def get_used_vars(ast):
    parents = parent_map(ast)
    used_vars = dict()
    for node in ast.iter():
        if node.tag == "VariableExpressionAst":
            if parents[node].tag != "AssignmentStatementAst" or parents[node].attrib["Operator"] != "Equals":
                var_name = node.attrib["VariablePath"].lower()
                if var_name in used_vars:
                    used_vars[var_name] += 1
                else:
                    used_vars[var_name] = 1
    return used_vars


def get_assigned_vars(ast):
    vars = set()
    for node in ast.iter():
        if node.tag == "AssignmentStatementAst" or (
                node.tag == "UnaryExpressionAst" and
                node.attrib["TokenKind"] in ["PostfixPlusPlus", "PostfixMinusMinus"]):
            if node[0].tag == "VariableExpressionAst":
                vars.add(node[0].attrib["VariablePath"].lower())

    return vars


def create_constant_number(value):
    const_expr = Element("ConstantExpressionAst")
    const_expr.text = str(value)
    const_expr.attrib["StaticType"] = "int" if isinstance(value, int) else "double"
    return const_expr


def create_constant_string(value, string_type="SingleQuoted"):
    string_const_expr = Element("StringConstantExpressionAst")
    string_const_expr.text = value
    string_const_expr.attrib["StringConstantType"] = string_type
    string_const_expr.attrib["StaticType"] = "string"
    return string_const_expr


def create_array_literal_values(values, string_type="SingleQuoted"):
    new_array_ast = Element("ArrayLiteralAst",
                            {
                                "StaticType": "System.Object[]",
                            })
    new_elements = Element("Elements")

    for val in values:
        new_string_item = Element("StringConstantExpressionAst",
                                  {
                                      "StringConstantType": string_type
                                  })
        new_string_item.text = str(val)
        new_elements.append(new_string_item)

    new_array_ast.append(new_elements)
    return new_array_ast


def get_array_literal_values(node):
    argument_values = []

    arguments = node
    if arguments is not None:
        arguments = arguments.find("Elements")
        if arguments is not None:
            for element in list(arguments):
                if element.tag == "StringConstantExpressionAst":
                    argument_values.append(element.text)
                elif element.tag == "ConstantExpressionAst":
                    argument_values.append(int(element.text))
                else:
                    return None
            return argument_values

    return None


def is_prefixed_var(param):
    prefix = param.lower().split(':')[0]
    return prefix in ["env"]


def parent_map(ast):
    return dict((c, p) for p in ast.iter() for c in p)


def replace_node(ast, old, new, until=None, parents=None):
    if parents is None:
        parents = parent_map(ast)

    for i, element in enumerate(parents[old]):
        if element == old:
            if until is not None:
                while element.tag != until and element in parents:
                    element = parents[element]
            if element in parents:
                parents[element].remove(element)
                if not isinstance(new, (list, tuple)):
                    parents[element].insert(i, new)
                else:
                    for j, new_elem in enumerate(new):
                        parents[element].insert(i + j, new_elem)
                break


def delete_node(ast, old, until=None):
    parents = parent_map(ast)
    for i, element in enumerate(parents[old]):
        if element == old:
            if until is not None:
                while element.tag != until:
                    element = parents[element]
            parents[element].remove(element)
            break


def to_numeric(s):
    try:
        result = int(s)
    except ValueError:
        result = float(s)
    return result


def check_python_version():
    if platform.python_version_tuple()[0] == "2":
        print("Please use Python 3. (Python 2 is no more maintained).")
        sys.exit(0)


def is_root_path(p):
    return os.path.dirname(p) == p


def change_extension(f, ext):
    base = os.path.splitext(f)[0]
    os.rename(f, base + ext)


def delete_directory(dir_path):
    shutil.rmtree(dir_path)


def make_directory(dir_path):
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                return False
    return True

def welcome():
    banner = """
_________________________________________________________________________
    ____                                  _____                        _ 
    /    )                                /    )               /     /  `
---/____/----__-----------__---)__-------/----/----__----__---/__--_/__--
  /        /   )| /| /  /___) /   )     /    /   /___) /   ) /   ) /     
_/________(___/_|/_|/__(___ _/_________/____/___(___ _(___/_(___/_/______

    PowerShell Deobfuscation Tool - All test based on Powershell 5.1                    
                          Author: @Autumnal
                          Version: V1.0.0                                                                                               
"""
    print("\u001b[93m" + banner + "\u001b[0m\n")


def humansize(nbytes):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    if nbytes == 0:
        return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def xor(data, key):
    return bytearray(a ^ key for a in data)


def clean_folder(directory):
    for f in glob.glob(directory + '/*'):
        os.remove(f)


"""
fix: 针对 Base64 编码的字符串进行解码
"""
def is_utf8_readable_base64(b64_string):
    """ 
    检测 Base64 解码后是否为可读 UTF-8 文本 
    """
    global is_bs64
    try:
        if b64_string is not None:
            decoded_bytes = base64.b64decode(b64_string, validate=True)   
            is_bs64 = True
            
            # decode bytes 中去除 \x00 
            decoded_bytes = decoded_bytes.replace(b'\x00', b'')
            decoded_str = decoded_bytes.decode("utf-8")  # 直接解码
            
            if decoded_str.isprintable() and decoded_bytes != b'':  # 检测是否为可读文本
                log_warn("Detected Base64 encoded string, this may not work correctly")
                log_warn("Decoded string: %s" % decoded_str)
                return decoded_str
                
        return False
    except Exception:
        is_bs64 = False    
        return False  # 解析错误，或者不是 UTF-8 文本

"""
fix: 针对 ps1 编码的字符串进行积分判断
"""
def is_powershell_code(text):
        if not text:
            return False

        text = text.strip("'\"").lower()
        score = 0
        # 模式匹配计分
        for pattern in BAREWORDS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                score += 2
                if score >= 4:  # 达到阈值判定为代码
                    return True

        # 特殊变量引用检测
        if re.search(r"\$env:[a-z]+\[[0-9,]+\]", text):
            return True
        return False
