

class KeyValueConfig():

    def __init__(self, content = None):
        self.settings = {}
        if content != None:
            self.load_string(content)
    
    def load_string(self, content):
        lines = content.splitlines()
        for ln in lines:
            no_comment = ln.split('#', 1)[0].strip()
            if len(no_comment) == 0 or no_comment.isspace():
                continue 
            pair = [itm.strip() for itm in no_comment.split('=', 1)]
            assert(len(pair) == 2)
            self.settings[pair[0]] = pair[1]


def parse_kv_file(file_name):
    fl = open(file_name, 'r')
    fl_content = fl.read()
    conf = KeyValueConfig(content = fl_content)
    fl.close()
    return conf