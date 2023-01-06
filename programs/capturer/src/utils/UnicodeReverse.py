# This file is for converting unicode (and ctrl-combinations) to letters and backwards.

def convert_from_unicode(name: str) -> str:
    if is_ctrl_unicode(name):
        code = get_unicode_order_from_char(name)
        return character_from_ctrl_unicode(code)
    return name


# If unicode number is 0-31 or 127, then it is a control unicode.
# Because pynput only registers/only fails to convert the alphabet, this will not return True for the other six control codes.
def is_ctrl_unicode(code: str) -> bool:
    return len(code) == 1 and 0 < ord(code) <= 26


# param: char
def get_unicode_order_from_char(char: str) -> int:
    if len(char) != 1:
        return -1
    return ord(char)

# Returns the character from control + character unicode.
# Example: ctrl + A -> (pynput) -> \u0001 -> (This method) -> a
# There are 32 ctrl combinations, but pynput does not register/struggle the non-alphabetic codes, so they will not be considered.
def character_from_ctrl_unicode(order: int) -> str:
    if not 0 < order <= 26:
        return
    pool = "abcdefghijklmnopqrstuvwxyz"
    assert len(pool) == 26
    return pool[order-1]









