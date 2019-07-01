try: 
    import typing as tp 
except:
    pass 

class KeyValueConfig():

    def __init__(self, content = None):
        #type: (tp.Optional[str]) -> None
        self.settings = {} #type: tp.Dict[str, str]
        if content is not None: 
            self.load_string(content)
    
    def load_string(self, content, key_prefix = None, key_mapper = None, value_mapper = None):
    #type: (str, tp.Optional[str], tp.Optional[tp.Callable[ [str], str]], tp.Optional[tp.Callable[ [str], str]]) -> None
        lines = content.splitlines()
        for ln in lines:
            no_comment = ln.split('#', 1)[0].strip()
            if len(no_comment) == 0 or no_comment.isspace():
                continue 
            pair = [itm.strip() for itm in no_comment.split('=', 1)]
            assert(len(pair) == 2)
            key = pair[0]
            if key_mapper is not None:
                key = key_mapper(key)
            if key_prefix is not None: 
                if not key.startswith(key_prefix):
                    continue 
                else:
                    key = key[len(key_prefix):]
            value = pair[1]
            if value_mapper is not None:
                value = value_mapper(value)
            self.settings[key] = value

def get_config_file_list(file_name = None, arg_path = None):
    #type: (tp.Optional[str], tp.Optional[str]) -> tp.List[str]
    import os 

    retval = []

    if arg_path is not None: 
        if not os.path.exists(arg_path):
            raise RuntimeError, "Error creating config file list: %s is not a valid path."%(str(arg_path))
        elif os.path.isfile(arg_path) and file_name is None:
            file_name = os.path.basename(arg_path)
        print('CFG ARG PATH: %s'%(str(arg_path)))
        retval.append(arg_path)
    if file_name is None:
        file_name = ''
    cur_path = os.path.dirname(os.path.abspath(__file__))
    default_directories = ['~/.config/glideTester', '/etc/glideTester', os.path.join(cur_path, '../etc')]
    possible_defaults = [os.path.join(dir_name, file_name) for dir_name in default_directories]
    defaults = [default_path for default_path in possible_defaults if os.path.exists(default_path)]

    retval.extend(defaults)

    return retval


def parse_kv_file(file_name, key_prefix = None, key_mapper = None, value_mapper = None):
    #type: (str, tp.Optional[str], tp.Optional[tp.Callable[ [str], str]], tp.Optional[tp.Callable[ [str], str]]) -> KeyValueConfig
    fl = open(file_name, 'r')
    fl_content = fl.read()
    conf = KeyValueConfig()
    conf.load_string(fl_content, key_prefix=key_prefix, key_mapper=key_mapper)
    fl.close()
    return conf


def parse_argv(args, valid_flags = None, valid_kv_settings = None, key_markers = ['--', '-']):
    #type: (str, tp.Optional[str], tp.Optional[tp.List[str]], tp.Optional[tp.List[str]]) -> tp.Dict[str, tp.Union[str, bool]]
    if args is None or len(args) <= 0:
        return {}
    retval = {} #type: tp.Dict[str, tp.Union[str, bool]]
    idx = 0
    print('Parsing args: %s'%(str(args)))
    while idx + 1 < len(args):
        key = args[idx]
        if not _starts_with_any(key, key_markers):
            raise RuntimeError, "Could not parse key arg %s"%(str(key))
        next_item = args[idx + 1]
        if _starts_with_any(next_item, key_markers):
            if valid_flags is not None and key not in valid_flags:
                raise RuntimeError, "Invalid flag :%s. Flags must be one of %s."%(str(key), str(valid_flags))
            retval[key] = True 
        else:
            if valid_kv_settings is not None and key not in valid_kv_settings:
                raise RuntimeError, "Invalid parameter %s with value %s. The parameters must be one of %s."%(str(key), str(next_item), str(valid_kv_settings))
            retval[key] = next_item
            idx += 1
        idx += 1
    return retval

def _starts_with_any(item, prefix_list):
    prefix_checker = lambda prefix: item.startswith(prefix)
    return any(map(prefix_checker, prefix_list))


#Matches all non-bracket strings between brackets.
#Building the regex: 
# '[^}]' matches a single character not equal to '}', returning the boolean True on match. 
# '[^}]*' matches multiple characters not equal to '}', returning the boolean True on match. 
# '([^}]*)' matches multiple characters not equal to '}', returning the matching characters.
# '{([^}]*)}' matches multiple characters between '{' and '}' not themselves equal to '}', returning the matching characters.
import re 
exp_matcher = re.compile('{([^}]*)}') 

# Takes a GlideTester format string and the local variable map and builds the runtime value of the string. 
def construct_from_format(format_str, var_map):
    #type: (str, tp.Dict[str, tp.Any]) -> str 
    exp_list = exp_matcher.findall(format_str) #type: tp.List[str]
    exp_runner = lambda exp: str(eval(exp, None, var_map)) #type: tp.Callable[[str], str]
    repl_list = []
    err_list = {}
    for exp in exp_list: 
        try:
            repl_list.append(exp_runner(exp))
        except Exception as e: 
            err_list[exp] = e
    out_format, exp_count = exp_matcher.subn('%s', format_str.replace('%', '%%'))
    if len(err_list) > 0:
        msg = '['
        for exp in err_list:
            err = err_list[exp]
            msg += "'{}' : '{}',".format(exp, err)
        msg += ']'
        raise ValueError(msg)    
    assert len(repl_list) == exp_count
    return out_format%tuple(repl_list)