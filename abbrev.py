import re
import sys

def expand_ctss(mad_text):
    replacements = {
        r"W'R": "WHENEVER",
        r"O'R": "OR WHENEVER",
        r"O'E": "OTHERWISE",
        r"E'L": "END OF CONDITIONAL",
        r"T'O": "TRANSFER TO",
        r"T'H": "THROUGH",
        r"F'N": "FUNCTION RETURN",
        r"V'S": "VECTOR VALUES",
        r"E'M": "END OF PROGRAM",
        r"E'N": "END OF FUNCTION"
    }
    
    for abbrev, full in replacements.items():
        mad_text = re.sub(r"\b" + re.escape(abbrev) + r"\b", full, mad_text)
    return mad_text

with open('hello.mad', 'r') as f:
    code = f.read()

expanded = expand_ctss(code)

with open('hello.mad', 'w') as f:
    f.write(expanded)
