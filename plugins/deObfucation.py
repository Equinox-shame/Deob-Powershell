import pathlib

from plugins.getAst import *
from plugins.logger import *
from plugins.optimize import Optimizer
from plugins.rebuilder import Rebuilder


def deObfucation(ps1_file):
    log_info("Deobfuscating " + ps1_file)
    ps1_file_path = pathlib.Path(ps1_file)
    if ast := read_ast_file(ps1_file_path.with_suffix(".xml")):
        o = Optimizer()
        o.optimize(ast) 
        
        try:
            with open(ps1_file_path.with_suffix(".deobfucated.xml"), "wb") as output:
                ast.write(output)
        except Exception as e:
            log_err(str(e))
            return
        
        r = Rebuilder(ps1_file_path.with_suffix(".deobfucated.ps1"))
        r.rebuild(ast.getroot())
       
    
if __name__ == '__main__':
    deObfucation("Data\\Test.ps1")