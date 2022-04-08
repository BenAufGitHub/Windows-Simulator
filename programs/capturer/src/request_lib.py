# get windows
# get pid
# get closest window in process


def transform_to_output_protocol(input):
    if type(input) == str:
        return f"t {input}"
    if type(input) == int:
        return f"i {input}"
    if type(input) == list:
        return array_to_output_protocol(input)
    raise ValueError("Input only str, int and list")


def array_to_output_protocol(input):
    is_int_arr = True
    result_str = 'at'
    for content in input:
        if type(content) != int:
            is_int_arr = False
    if is_int_arr:
        result_str = ' '.join(map(lambda i: str(i), input))
        return f"ai {result_str}"
    for content in input:
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
    if in_type == 'ai':
        return str_to_int_arr(arr[1:])
    if in_type == 'at':
        return str_to_txt_arr(arr[1:])
    raise ValueError(f"Identifier not supported:{arr[0]}")


def str_to_txt_arr(array):
    index = 0
    result = []
    while index < len(array):
        if int(array[index]) + index >= len(array) or int(array[index]) <= 0:
            raise Exception("Faulty txt array at conversion by protocol.")
        next_word_sequence = array[index+1:1+index+int(array[index])]
        result.append(' '.join(next_word_sequence))
        index += int(array[index])+1
    return result
    
def str_to_int_arr(array):
    return map(lambda figure: int(figure), array)


def split_request(request):
    words = []
    word = ''
    for letter in request:
        if 
