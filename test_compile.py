import re
import os

with open('hello.mad', 'r') as f:
    raw_text = f.read()

ctss_replacements = {
    r"\bW'R\b": "WHENEVER",
    r"\bO'R\b": "OR WHENEVER",
    r"\bO'E\b": "OTHERWISE",
    r"\bE'L\b": "END OF CONDITIONAL",
    r"\bT'O\b": "TRANSFER TO",
    r"\bT'H\b": "THROUGH",
    r"\bF'N\b": "FUNCTION RETURN",
    r"\bV'S\b": "VECTOR VALUES",
    r"\bE'M\b": "END OF PROGRAM",
    r"\bE'N\b": "END OF FUNCTION",
    r"\bR\b": "PRINT COMMENT"
}
for abbrev, full in ctss_replacements.items():
    raw_text = re.sub(abbrev, full, raw_text)

raw_lines = raw_text.split('\n')
mad_keywords = {
    "BOOLEAN", "CONDITIONAL", "CONTINUE", "DATA", "DIMENSION",
    "BACKSPACE_RECORD_OF_TAPE", "END_OF_FILE_TAPE", "END", "ENTRY",
    "ERASABLE", "ERROR_RETURN", "EXECUTE", "EXTERNAL", "FLOATING_POINT",
    "FOR", "FORMAT_VARIABLE", "FUNCTION", "FUNCTION_RETURN", "INTEGER",
    "INTERNAL", "IS", "MODE", "NORMAL", "OF", "OR", "OTHERWISE",
    "PARAMETER", "PAUSE", "PRINT_COMMENT", "PRINT_FORMAT",
    "PRINT_ONLINE_FORMAT", "PRINT_RESULTS", "PROGRAM", "PROGRAM_COMMON",
    "READ_DATA", "READ_AND_PRINT_DATA", "READ_BCD_TAPE",
    "READ_BINARY_TAPE", "READ_FORMAT", "REWIND_TAPE", "RESTORE",
    "RESTORE_RETURN", "SAVE", "SAVE_RETURN", "SET_LIST_TO",
    "STATEMENT_LABEL", "THROUGH", "TO", "TRANSFER", "VALUES",
    "VECTOR", "WHENEVER", "WRITE_BCD_TAPE", "WRITE_BINARY_TAPE",
    "UNLOAD_TAPE", "INSERT_FILE", "COMMENT", "DOTRANGE",
    "SET", "FORMAT", "FLOATING", "PRINT", "PRINT ON", "PRINT ON LINE",
    "V'S", "W'R", "T'O", "O'E", "E'L", "F'N", "E'N", "LIST."
}

processed_lines = []
for line in raw_lines:
    stripped = line.strip()
    if not stripped:
        processed_lines.append(line)
        continue
    
    # If already manually padded to IBM 7090 spec (11 leading spaces)
    if len(line) - len(line.lstrip()) >= 11:
        processed_lines.append(line)
        continue
    
    parts = stripped.split(None, 1)
    if len(parts) == 1:
        processed_lines.append("           " + stripped)
        continue
    
    w1, w2 = parts[0], parts[1]
    w1_upper = w1.upper()
    
    has_label = False
    if w1_upper not in mad_keywords and w1.isalnum() and not w2.startswith("=") and not w2.startswith("("):
        has_label = True
    
    if has_label:
        lbl = w1[:6].ljust(11)
        processed_lines.append(lbl + w2)
    else:
        processed_lines.append("           " + stripped)

with open('hello_padded.mad', 'w') as f:
    f.write('\n'.join(processed_lines))

os.system("./mad_compiler_src/mad -C -S hello_padded.mad")
