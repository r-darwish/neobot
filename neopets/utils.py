import re

_NP_RE = re.compile(r'([\d,]+)(?: NP)?')

def to_int(text):
    return int(text.replace(',',''))

def np_to_int(text):
    return to_int(_NP_RE.search(text).group(1))
