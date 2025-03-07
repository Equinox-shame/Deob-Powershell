# coding=utf-8
from plugins.barewords import *
from plugins.logger import *
from plugins.utils import is_utf8_readable_base64, is_powershell_code


ESCAPED_CHARS = { # 用于转义的字符
    '\'': '\'\'',
    '\n': '`n',
    '#': "`#"
}

is_bs64 = False


def escape_string(s, mode):
  
    if mode == "BareWord":
        # 添加判断是否为 ps1 代码
        is_code = is_powershell_code(s)
        if is_code:
            log_warn("Detected inline PowerShell code, this may not work correctly") # 检测到代码
            return s
        
        return ''.join([ESCAPED_CHARS.setdefault(c, c) for c in s])  
    
    else: # 单双引号字符串内容
        # 尝试解码 Base64
        res = is_utf8_readable_base64(s)
        
        if res is not False:
            return res

        return ''.join([ESCAPED_CHARS.setdefault(c, c) for c in s]) 
