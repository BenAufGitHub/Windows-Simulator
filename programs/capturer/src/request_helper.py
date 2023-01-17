import math
from .utils.app_errors import *


def split_request(request: str):
    id, remainder = _seperate_id(request)
    req, raw_body = _seperate_request(remainder)
    body = _raw_body_to_object(raw_body)
    return id, req, body


def _seperate_id(request):
    str_figure = ''
    text = request.lstrip(' ')
    if len(text) == 0: raise InvalidRequest('Empty request denied')
    for letter in text:
        if letter == ' ': break
        str_figure += letter
    if not str_figure.isdigit(): raise InvalidRequest('No valid ID found')
    if len(str_figure)+2 > len(text): raise InvalidRequest('No request found')
    return int(str_figure), text[len(str_figure)+1:]

def _seperate_request(text):
    text = text.lstrip()
    seperator_index = text.find(" | ")
    # either not existent or at end (= no body)
    if seperator_index < 0 or seperator_index == len(text)-3: raise InvalidRequest("No Request-Body Seperator")
    return text[:seperator_index], text[seperator_index+3:]

def _raw_body_to_object(raw_body):
    identifier, remainder = _seperate_identifier(raw_body)
    if identifier == 'n': return None
    if identifier == 'i': return get_int(remainder)
    if identifier == 'ai': return get_int_list(remainder)
    if identifier == 't': return get_text(remainder)
    if identifier == 'at': return get_text_list(remainder)

def _seperate_identifier(text):
    text = text.lstrip()
    if len(text) == 0: raise InvalidRequest("Request body missing")
    if text[0] == 'n': return 'n', None
    space = text.find(' ')
    if space == -1: space = len(text)
    return text[:space], text[space+1:].lstrip()

def get_int(text):
    space = text.find(" ")
    if space != -1:
        text = text[:space]
    text = text.rstrip()
    if not text.isdigit(): raise InvalidRequest("Request with identifier i requires integer")
    return int(text)

def get_int_list(text):
    arr = []
    while len(text) > 0:
        space = text.find(" ")
        if space == -1: space = len(text)
        try:
            arr.append(get_int(text[:space]))
        except InvalidRequest:
            raise InvalidRequest("Request with identifier ai must only contain integers")
        text = text[space:].lstrip()
    return arr

def get_text(text):
    space = text.find(" ")
    if space == -1: return text
    try:
        chars = get_int(text)
        if chars < 1: return ''
    except InvalidRequest:
        raise InvalidRequest("Request with identifier t has no char amount defined")
    chars_repr_len = int(math.floor(math.log(chars, 10))) + 1
    if chars + chars_repr_len + 1 > len(text): raise InvalidRequest("Text input shorter than character hint suggests")
    return text[chars_repr_len + 1:chars + chars_repr_len + 1]
    
def get_text_list(text):
    arr = []
    while len(text) > 0:
        try:
            sub_text = get_text(text)
            removed_digits = math.floor(math.log(len(sub_text), 10)) + 2
        except InvalidRequest:
            raise InvalidRequest("text-list request invalidly formatted")
        arr.append(sub_text)
        text = text[len(sub_text) + removed_digits:].lstrip()
    return arr


def transform_to_output_protocol(input):
    if input == None:
        return "n"
    if type(input) == str:
        input = input.encode("ascii", "ignore").decode()
        return f"t {len(input)} {input}"
    if type(input) == int:
        return f"i {input}"
    if type(input) == list:
        return array_to_output_protocol(input)
    raise ValueError("Input only str, int and list")


def array_to_output_protocol(input):
    is_int_arr = True
    result_str = 'at '
    for content in input:
        if type(content) != int:
            is_int_arr = False
    if is_int_arr:
        result_str = ' '.join(map(lambda i: str(i), input))
        return f"ai {result_str}"
    for content in input:
        content = str(content).encode("ascii", "ignore").decode()
        result_str += f"{len(str(content))} {str(content)}"
    return result_str