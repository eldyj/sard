from sa_core import *

end_queue = []

class ParseOptions:
    argsfix = False
    is_lib = False
    current_dir = ""

def dirname(filename):
    if "/" not in filename:
        return ParseOptions.current_dir

    tmp = filename.split('/')
    tmp.pop()

    return '/'.join(tmp)

def parse_fn(input_str):
    parts = input_str.strip().split()
    name = parts[1]
    arguments = []
    return_var = False

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
    parts = inp.split()
    first = parts.pop(0)
    fnargs = ALL_REGISTERS[0:Data.fns[first]]
    returns_to = False

    if len(parts) < Data.fns[first]:
        for i in parts:
            tmp = f"{i}.len"
            if tmp in arguments_map:
                parts.append(tmp)

    print(parts)

    if ParseOptions.argsfix:
        parts.reverse()
        #for i in parts:
        #    if i[0] == ":":
        #        returns_to = i[1:]
        #        continue
        #    if get_register(i) != "rax":
        #        push(i)

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

    #if ParseOptions.argsfix:
    #    parts.reverse()

    #    for i in parts:
    #        if get_register(i) != "rax":
    #            pop(i)

#def parse_call(inp):
#    parts = inp.split()
#    first = parts.pop(0)
#    fnargs = ALL_REGISTERS[0:Data.fns[first]]
#    returns_to = False
#
#    if ParseOptions.argsfix:
#        parts.reverse()
#        #for i in parts:
#        #    if i[0] == ":": returns_to = i[1:]
#        #    if i[0] == ":" or i.isnumeric(): continue
#        #    if get_register(i) != "rax": push(i)
#
#        for i in parts:
#            if i[0] == ":": continue
#            push(i)
#
#        for i in parts:
#            if i[0] == ":": continue
#            pop(fnargs.pop(0))
#    else:
#        for i in parts:
#            if i[0] == ":":
#                returns_to = i[1:]
#                break
#            mv(fnargs.pop(0),i)
#
#
#    add_code(f"    call {first}")
#
#    if returns_to != False:
#        mv(returns_to, 'rax')
#
#    #if ParseOptions.argsfix:
#    #    parts.reverse()
#
#    #    for i in parts:
#    #        if i[0] == ":" or i.isnumeric(): continue
#    #        if get_register(i) != "rax":
#    #            pop(i)

def sa_include(filename):
    prev_dirname = ParseOptions.current_dir
    ParseOptions.current_dir = dirname(filename)

    with open(prev_dirname + filename, "r") as f:
        for i in f.read().split('\n'):
            parse_line(i)

    ParseOptions.current_dir = prev_dirname

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
    elif first == "while":
        end_queue.append(endwhile)
        sa_while(inp[6:])
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
        end_queue.pop()()
    elif first in Data.fns:
        parse_call(inp)
    else:
        parse_operation(inp)
