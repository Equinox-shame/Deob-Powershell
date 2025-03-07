import argparse

from plugins.utils import *
from plugins.getAst import *
from plugins.deObfucation import deObfucation

def useage():
    print("Usage: python3 startup.py -i <input.ps1>")


def main():
    parser = argparse.ArgumentParser(description="Deobfuscate PowerShell scripts")
    parser.add_argument("-i", help="Input .ps1 file to deobfuscate")
    args = parser.parse_args()
    if args.i:
        create_ast_file(args.i)
        deObfucation(args.i)
    else:
        useage()
            
if __name__ == "__main__":
    welcome()
    set_log_level(LogLevel.DEBUG)
    main()