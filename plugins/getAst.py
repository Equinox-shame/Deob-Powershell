import os
import subprocess
import xml.etree.ElementTree as ET

from plugins.logger import *

def create_ast_file(ps1_file = "Data\\Test.ps1"):
    log_info("Reading AST from " + ps1_file)
    command = ["PowerShell", "-ExecutionPolicy", "Unrestricted", "-File",
            os.path.abspath(os.path.join("tools", "Get-AST.ps1")),
            "-ps1", os.path.abspath(ps1_file), ]
    log_debug("Running command: " + " ".join(command))
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    
    output = result.stdout
    error = result.stderr
    
    if result.returncode != 0:
        log_err("Error running Get-AST.ps1: " + error)
        return result.returncode
    
    log_debug("Output: " + output.replace("\n", " ")) # AST 执行后输出
    log_info("AST read successfully")
    
    return result.returncode
    
def read_ast_file(filename):
    log_info(f"Reading input AST: {filename}")
    try:
        ast = ET.parse(filename)
        return ast
    except IOError as e:
        log_err(e.args[1])
        return None
    except Exception as e:
        log_err(str(e))
        return None


if __name__ == "__main__":
    create_ast_file()