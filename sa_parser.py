import re
from sa_core import *

end_queue = []

class ParseOptions:
    argsfix = False
    is_lib = False
    current_dir = ""
    ignored_files = []
    current_file = ""
    entry = ""

class ParserData:
    lastfn_name = ""
    lastfn_exit = False

def dirname(filename):
    if "/" not in filename:
        return ParseOptions.current_dir

    tmp = filename.split('/')
    tmp.pop()

    return '/'.join(tmp) + '/'

def parse_fn(input_str):
    parts = input_str.strip().split()
    name = parts[1]
    arguments = []
    return_var = False
    ParserData.lastfn_name = name
    ParserData.lastfn_exit = False

    for part in parts[2:]:
        if part.startswith(":"):
            return_var = part[1:]
            break
        else:
            arguments.append(part)

    fn(name,arguments,return_var)

def parse_operation(input_str):
    inp = input_str.strip()
    parts = inp.split()
    val1 = parts[0]
    val2 = parts[2]

    # Extract the operator
    operator = parts[1]
    if operator == "+=":
        add(val1,val2)
    elif operator == "-=":
        sub(val1,val2)
    elif operator == "*=":
        #mul(val1,val2) # TODO
        pass
    elif operator == "/=":
        #div(val1,val2) # TODO
        pass
    elif operator == "|=":
        #bit_or(val1,val2) # TODO
        pass
    elif operator == "&=":
        #bit_and(val1,val2) # TODO
        pass
    elif operator == "^=":
        #bit_xor(val1,val2) # TODO
        pass
    elif operator == "<=>":
        push(val1)
        push(val2)
        pop(val1)
        pop(val2)
    elif operator in {'=',':='}:
        if "-" in input_str or "+" in input_str or "*" in input_str or "/" in input_str:
            expand_operation(input_str)
            return

        if '"' in input_str:
            s = new_str(inp[len(val1)+3:])
            mv(val1, s)
            arguments_map[f"{val1}.len"] = f"{s}_len"
            return

        mv(val1, val2)
    else:
        raise ValueError("Invalid operator")

def expand_operation(input_str):
    parts = input_str.strip().split()
    result = parts[0]
    val1 = parts[2]
    mv(result, val1)
    for i in range(4, len(parts), 2):
        operator = parts[i-1]
        val = parts[i]
        parse_operation(f"{result} {operator}= {val}")

def parse_call(inp):
    parts = re.findall(r'''("[^"]*"|'[^']*'|\S+)''', inp)
    first = parts.pop(0)
    fnargs = ALL_REGISTERS[0:Data.fns[first]]
    returns_to = False

    if not ParserData.lastfn_exit:
        print(end_queue)
        if ParserData.lastfn_name == ParseOptions.entry and first == "exit":
            if len(end_queue) == 0 or end_queue[-1] == endfn:
                ParserData.lastfn_exit = True

    for index,i in enumerate(parts):
        if '"' in i:
            i = new_str(i)
            parts[index] = i
            arguments_map[f"{i}.len"] = f"{i}_len"
        if len(parts) < Data.fns[first]:
            tmp = f"{i}.len"
            if tmp in arguments_map:
                parts.append(tmp)

    if ParseOptions.argsfix:
        parts.reverse()

        for i in parts:
            if i[0] == ":":
                continue
            push(i)

        for i in parts:
            if i[0] == ":":
                continue
            pop(fnargs.pop(0))
    else:
        for i in parts:
            if i[0] == ":":
                returns_to = i[1:]
                break
            mv(fnargs.pop(0),i)


    add_code(f"    call {first}")

    if returns_to != False:
        mv(get_or_set_register(returns_to), 'rax')

def sa_include(filename):
    file = ParseOptions.current_dir + filename
    if file in ParseOptions.ignored_files: return
    prev_filename = ParseOptions.current_file
    prev_dirname = ParseOptions.current_dir
    ParseOptions.current_dir = dirname(file)
    ParseOptions.current_file = file

    with open(prev_dirname + filename, "r") as f:
        for i in f.read().split('\n'):
            parse_line(i)

    ParseOptions.current_dir = prev_dirname
    ParseOptions.current_file = prev_filename

def parse_line(input_str):
    if len(input_str) == 0 or input_str[0] in {'#',';',''}: return

    inp = input_str.strip()

    parts = inp.split()
    if len(parts) < 1: return
    first = parts[0]

    if first == "fn":
        end_queue.append(endfn)
        if ParseOptions.is_lib:
            add_code(f"public {parts[1]}")

        parse_fn(input_str)
    elif first == "if" or first == "unless":
        end_queue.append(endif)
        sa_if(inp[3:], first == "if")
    elif first == "else":
        sa_else()
    elif first == "elif" or first == "elun":
        sa_elif(inp[5:], first == "elif")
    elif first == "loop":
        end_queue.append(endloop)
        sa_loop()
    elif first == "dowhile":
        end_queue.append(enddowhile)
        sa_dowhile(inp[8:])
    elif first == "while":
        end_queue.append(endwhile)
        sa_while(inp[6:])
    elif first == "for":
        end_queue.append(endfor)
        sa_for(inp[4:])
    elif first == "continue":
        sa_continue()
    elif first == "break":
        sa_break()
    elif first == "include":
        sa_include(inp[8:])
    elif first == "syscall":
        syscall(parts[1])
    elif first == "label":
        label(parts[1])
    elif first == "goto":
        goto(parts[1])
    elif first == "push":
        push(parts[1])
    elif first == "pop":
        pop(parts[1])
    elif first == "end":
        tmp = end_queue.pop()
        if tmp == endfn:
            if ParserData.lastfn_name == ParseOptions.entry:
                if not ParserData.lastfn_exit:
                    parse_call('exit 0')
        tmp()
    elif first == "once":
        ParseOptions.ignored_files.append(ParseOptions.current_file)
    elif first in Data.fns:
        parse_call(inp)
    else:
        parse_operation(inp)
