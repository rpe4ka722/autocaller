def parse_ami_response(s:str):
    result = dict()
    raw_list = []
    raw_list = s.split('\r\n')
    for raw in raw_list:
        if raw != '':
            result[raw.split(': ')[0]] = raw.split(': ')[1]
    return result
