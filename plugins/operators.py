# coding=utf-8
OPS = {
    "Minus": " - ",
    "Plus": " + ",
    "Multiply": " * ",
    "Format": " -f ",
    "Equals": " = ",
    "PlusEquals": " += ",
    "MinusEquals": " -= ",
    "MultiplyEquals": " *= ",
    "PostfixPlusPlus": "++",
    "PostfixMinusMinus": "--",
    "Is": " -is ",
    "As": " -as ",
    "Ieq": " -eq ",
    "Ige": " -ge ",
    "Igt": " -gt ",
    "Ile": " -le ",
    "Ilt": " -lt ",
    "Ine": " -ne ",
    "Bxor": " -bxor ",
    "Ireplace": " -replace ",
    "Join": " -join ",
    "Imatch": " -match ",
    "Inotmatch": " -notmatch ",
    "Isplit": " -split ",
    "And": " -and ",
    "Or": " -or ",
    "DotDot": "..",
    "Ilike": " -like ",
    "Creplace": " -creplace ",
    "Cmatch": " -cmatch ",
    "Cnotmatch": " -cnotmatch ",
    "Csplit": " -csplit ",
}


def do_const_comparison(a, b, operator):
    if operator == "Ieq":
        return a == b
    elif operator == "Ine":
        return a != b
    elif operator == "Ige":
        return a >= b
    elif operator == "Igt":
        return a > b
    elif operator == "Ile":
        return a <= b
    elif operator == "Ilt":
        return a < b

    return None
