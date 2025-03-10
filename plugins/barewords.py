# coding=utf-8

BAREWORDS_PATTERNS = [
    # 基础混淆检测
    r"\b(?:n[e3][wv]?[\-\_]?[o0][bj].{1,6}t)\b", # New-Object变形检测
    r"[\|%&]{1,2}\s*[\{\$\(]",                   # 可疑操作符组合 
    r"\[[a-z0-9\.]+\]::",                        # 静态方法调用
    r"\$[a-z]{3,15}\[[0-9]+\]",                  # 数组索引变量
    r"\b(?:i[e3]x|invoke-expression)\b",         # 危险命令检测
    r"-[c][o][m][m][a][n][d]\b",                 # 参数混淆检测
    
    # 新增混淆特征检测
    r"`\w",                                      # 反引号转义字符（如`$、`"）
    r"\b0x[a-f0-9]{2,}\b",                       # 十六进制编码值
    r"\b\d{3,}(?:\.\d+)?\b",                     # 疑似八进制或大整数
    r"['\"]\s*\+\s*['\"]",                       # 字符串拼接操作（如'po'+'wer'）
    r"\$\{[a-z]+:[^}]+\}",                       # 特殊变量格式（如${env:...}）
    r"\b(?:i`ex|ie`x|i[e3]x)\b",                 # Invoke-Expression混淆变形
    
    # 高危API检测
    r"\[System\.Reflection\.",                   # 反射相关类
    r"\b(?:VirtualAlloc|CreateThread|WriteProcessMemory)\b", # 可疑Win32 API
    r"\bAdd-Type\s+-MemberDefinition\b",         # 动态编译代码
    
    # 编码特征检测
    r"\bConvert\.FromBase64String\b",            # Base64解码
    r"\b-GZip\s+\[Byte\[\]\]\b",                 # GZip压缩数据
    r"\b-EncodedCommand\b",                      # 编码命令参数
    
    # 可疑行为模式
    r"\bStart-Process\s+-WindowStyle\s+Hidden\b",# 隐藏窗口启动
    r"\b-NonInteractive\b",                      # 非交互模式参数
    r"\b-ExecutionPolicy\s+Bypass\b",            # 绕过执行策略
    
    # 新增协议处理器检测
    r"\b(?:ms-msdt|ms-officecmd):",              # 可疑协议处理器
    r"\bRegister-ObjectEvent\b",                 # 事件订阅持久化
    
    # 恶意代码特征
    r"\b(?:Mimikatz|CobaltStrike|Metasploit)\b", # 已知攻击工具关键词
    r"\b(?:[A-Za-z0-9+/]{4}){10,}[A-Za-z0-9+/]{2}==?\b" # 长Base64模式
]

# 标准化的优化函数列表
BAREWORDS = {
    "compressionmode": "CompressionMode",
    "decompress": "Decompress",
    "memorystream": "MemoryStream",
    "text": "Text",
    "encoding": "Encoding",
    "ascii": "ASCII",
    "length": "Length",
    "readtoend": "ReadToEnd",
    "compression": "Compression",
    "deflatestream": "DeflateStream",
    "streamreader": "StreamReader",
    "value": "Value",
    "powershell": "Powershell",
    "invokecommand": "InvokeCommand",
    "invokescript": "InvokeScript",
    "securityprotocol": "SecurityProtocol",
    "createdirectory": "CreateDirectory",
    "webclient": "WebClient",
    "new": "New",
    "set": "Set",
    "type": "Type",
    "environment": "Environment",
    "variable": "Variable",
    "downloadfile": "DownloadFile",
    "create": "Create",
    "frombase64string": "FromBase64String",
    "tobase64string": "ToBase64String",
    "getenvironmentvariable": "GetEnvironmentVariable",
    "replace": "Replace",
    "creplace": "CReplace",
    "split": "Split",
    "system": "System",
    "io": "IO",
    "directory": "Directory",
    "net": "Net",
    "servicepointmanager": "ServicePointManager",
    "convert": "Convert",
    "invoke": "Invoke",
    "foreach": "ForEach",
    "object": "Object",
    "get": "Get",
    "item": "Item",
    "tochararray": "ToCharArray",
    "string": "String",
    "tostring": "ToString",
    "shellid": "ShellID",
    "downloadstring": "DownloadString",
    "request": "Request",
    "name": "Name",
    "toint16": "ToInt16",
    "toint32": "ToInt32",
    "toint64": "ToInt64",
    "touint16": "ToUInt16",
    "touint32": "ToUInt32",
    "touint64": "ToUInt64",
    "tobyte": "ToByte",
    "runtime": "Runtime",
    "convertto": "ConvertTo",
    "getmembers": "GetMembers",
    "gettype": "GetType",
    "getproperties": "GetProperties",
    "getfields": "GetFields",
    "name": "Name",
    "invoke": "Invoke",
    "runtime": "Runtime",
    "interopservices": "InteropServices",
    "marshal": "Marshal",
    "ptrtostructure": "PtrToStructure",
    "structureto": "StructureTo",
    "intptr": "IntPtr",
    "securestring": "SecureString",
    "securestringtobstr": "SecureStringToBStr",
    "out": "Out",
    "ptrtostructure": "PtrToStructure",
    "structureto": "StructureTo",
    "null": "Null",
}
