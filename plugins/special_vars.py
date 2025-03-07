# coding=utf-8

# 获取用户名
import os

USERNAME = os.getenv("USERNAME")
# print("USERNAME: %s" % USERNAME) 

SPECIAL_VARS_VALUES = {
    "verbosepreference": "SilentlyInstall",
    "pshome": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0",
    "shellid": "Microsoft.PowerShell",
    "env:comspec": "C:\\Windows\\system32\\cmd.exe",
    "executioncontext": "System.Management.Automation.EngineIntrinsics",
    "env:temp": f"C:\\Users\\{USERNAME}\\AppData\\Local\\Temp",
    "env:systemroot": "C:\\Windows",
    "env:windir": "C:\\Windows",
    "env:programfiles": "C:\\Program Files",
    "env:programfiles(x86)": "C:\\Program Files (x86)",
    "env:programfiles(x64)": "C:\\Program Files",
    "env:commonprogramfiles": "C:\\Program Files\\Common Files",
    
}

SPECIAL_VARS_NAMES = {
    "verbosepreference": "SilentlyInstall",
    "executioncontext": "ExecutionContext",
    "pshome": "PsHome",
    "shellid": "shellID",
    "env:comspec": "Env:ComSpec",
    "env:temp": "Env:Temp",
    "env:systemroot": "Env:SystemRoot",
    "env:windir": "Env:WinDir",
    "env:programfiles": "Env:ProgramFiles",
    "env:programfiles(x86)": "Env:ProgramFiles(x86)",
    "env:programfiles(x64)": "Env:ProgramFiles(x64)",
    "env:commonprogramfiles": "Env:CommonProgramFiles", 
}
