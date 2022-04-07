# get windows
# get pid
# get closest window in process


def transform_to_output_protocol(input):
    if type(input) == 'str':
        return f"t {input}"
    if type(input) == 'int':
        return f"i {input}"
    if type(input) == 'list':
        return array_to_output_protocol(input)
    raise ValueError("Input only str, int and list")


def array_to_output_protocol(input):
    is_int_arr = True
    result_str = 'at'
    for content in list:
        if type(content != 'int'):
            is_int_arr = False
    if is_int_arr:
        return f"ai {' '.join(input)}"
    for content in list:
        length = len(str(content).split())
        result_str += f" {length} {str(content)}"
    return result_str


# types t:text i:int at:textarray ai:intarray
def get_input_body_object(input):
    arr = input.split()
    if len(arr) < 2:
        raise ValueError(f"identifier or args missing: {input}")
    in_type = arr[0]
    if in_type == 't':
        return ' '.join(arr[1:])
    if in_type == 'i':
        if len(arr) != 2:
            raise ValueError(f"identifier or args missing: {input}")
        return int(arr[1])
    if type == 'ai':
        return str_to_int_arr(arr[1:])
    if type == 'at':
        return str_to_txt_arr(arr[1:])
    raise ValueError(f"Identifier not supported:{arr[0]}")


def str_to_txt_arr(array):
    index = 0
    result = []
    while index < len(array):
        if(array[index] + index >= len[array]) or int(array[index]) <= 0:
            raise Exception("Faulty txt array at conversion by protocol.")
        next_word_sequence = array[index:1+index+array[index]]
        result.push(' '.join(next_word_sequence))
        index += array[index]+1
    return result
    
def str_to_int_arr(array):
    return map(lambda figure: int(figure), array)
