regs = lambda: ['rdi','rsi','rdx','rcx','r8','r9','r10','r11','r12','r13','r14','r15','xmm0','xmm1','xmm2','xmm3','xmm4','xmm5','xmm6','xmm7']

arguments_map = {}
labels = []
ALL_REGISTERS = regs()
ALL_REGISTERS.append('rax')
ALL_REGISTERS.append('rbx')
neg_ops = {'=':'jne','==':'jne','!=':'je','~=':'je','<>':'je','>':'jng','<':'jnl','>=':'jnge','<=':'jnle'}
pos_ops = {'=':'je','==':'je','!=':'jne','~=':'jne','<>':'jne','>':'jg','<':'jl','>=':'jge','<=':'jle'}

class Data:
    data="section '.data' writable\n"
    code="section '.text' executable\n"
    registers = regs()
    fns={}
    str_literals_count = 0
    ifs_count = 0
    loops_count = 0
    elsif_qneeded = True
    elsif_queue = []
    endif_queue = []
    endloop_queue = []
    enddowhile_queue = []
    endwhile_queue = []
    endfor_queue = []
    else_queue = []
    bss_buffers = {}
    data_buffers = []

def add_code(line):
    Data.code += line+'\n'

def add_data(line):
    Data.data += '    ' + line + '\n'

def add_bss(line):
    Data.bss += '    ' + line + '\n'

def fn(name, arguments, return_var = False):
    Data.fns[name] = len(arguments)

    if return_var:
        arguments_map[return_var] = 'rax'

    for i in arguments:
        arguments_map[i] = Data.registers.pop(0)

    add_code(f"{name}:")

def endfn():
    Data.registers = regs()
    labels.clear()
    arguments_map.clear()
    add_code('    ret\n')

def label(name):
    add_code(f"    .{name}:")
    labels.append(name)

def goto(name):
    add_code(f"    jmp .{name}")

def jif(line):
    src = line.split()
    add_code(f"    cmp {get_register(src[1])}, {get_register(src[3])}")
    add_code(f"    {pos_ops[src[2]]} .{src[0]}")

def jifn(line):
    src = line.split()
    add_code(f"    cmp {get_register(src[1])}, {get_register(src[3])}")
    add_code(f"    {neg_ops[src[2]]} .{src[0]}")

def sa_if(line, reverse=True):
    (jifn if reverse else jif)(f"c{Data.ifs_count}e {line}")
    Data.endif_queue.append(Data.ifs_count)
    if Data.elsif_qneeded:
        Data.elsif_queue.append([Data.ifs_count])

    Data.else_queue.append(False)
    Data.ifs_count += 1

def sa_else():
    goto(f"c{Data.ifs_count - 1}re")
    label(f"c{Data.endif_queue[-1]}e")
    Data.else_queue.pop()
    Data.else_queue.append(True)

def sa_elif(line, reverse=True):
    Data.elsif_qneeded = False
    sa_else()
    Data.elsif_queue[-1].append(Data.ifs_count)
    sa_if(line,reverse)
    Data.elsif_qneeded = True

def endif(val = True):
    if val:
        tmp = Data.elsif_queue.pop()
        tmp.reverse()
        if len(tmp) > 0:
            for i in tmp:
                endif(False)
        else:
            endif(False)
    else:
        #print(Data.endif_queue)
        i = Data.endif_queue.pop()
        #print(f"endif: {i}")
        label(f"c{i}{'r' if Data.else_queue.pop() else ''}e")

def sa_loop():
    label(f"l{Data.loops_count}")
    Data.endloop_queue.append(Data.loops_count)

def endloop():
    goto(f"l{Data.endloop_queue.pop()}")

def sa_dowhile(line):
    label(f"l{Data.loops_count}")
    Data.enddowhile_queue.append([Data.loops_count, line])
    Data.loops_count += 1

def enddowhile():
    tmp = Data.enddowhile_queue.pop()
    jif(f"l{tmp[0]} {tmp[1]}")

def sa_while(line):
    jifn(f"l{Data.loops_count}e {line}")
    label(f"l{Data.loops_count}")
    Data.endwhile_queue.append([Data.loops_count, line])
    Data.loops_count += 1

def sa_break():
    tmp = Data.endwhile_queue.pop()
    goto(f"l{tmp[0]}e")
    Data.endwhile_queue.append(tmp)

def sa_continue():
    tmp = Data.endwhile_queue.pop()
    goto(f"l{tmp[0]}")
    Data.endwhile_queue.append(tmp)

def endwhile():
    tmp = Data.endwhile_queue.pop()
    jif(f"l{tmp[0]} {tmp[1]}")
    label(f"l{tmp[0]}e")

def sa_for(line):
    src = line.split()
    varname = src[0]
    op      = src[1]

    if op == ":":
        initial = src[2]
        final   = src[3]
        step    = src[4]
    elif op == "->":
        initial = '0'
        final   = src[2]
        step    = '1'
    else:
        raise ValueError(f"operator {op} haven't any context in 'for' loops")

    mv(varname, initial)
    sa_while(f"{varname} < {final}")
    push(varname)

    Data.endfor_queue.append([varname, step])

def endfor():
    tmp = Data.endfor_queue.pop()
    pop(tmp[0])
    add(tmp[0],tmp[1])
    endwhile()

def get_register(name):
    if name in ALL_REGISTERS or name in Data.bss_buffers or name in Data.data_buffers:
        return name

    if name in arguments_map:
        return arguments_map[name]

    return name

def get_or_set_register(name):
    if name in ALL_REGISTERS or name in Data.bss_buffers or name in Data.data_buffers:
        return name

    if name in arguments_map:
        return arguments_map[name]

    arguments_map[name] = Data.registers.pop(0)
    #add_code(f";;  first definition of {name} (on {arguments_map[name]})")
    return arguments_map[name]

def mv(name, value):
    actual_name = get_or_set_register(name)

    if value == name or actual_name == value or actual_name == get_register(value):
        return

    if value not in {'0',0}:
        add_code(f"    mov {actual_name}, {get_register(value)}")
    else:
        add_code(f"    xor {actual_name}, {actual_name}")

def add(name, value):
    if value in {'1',1}:
        add_code(f"    inc {get_register(name)}")
        return

    if value in {'0',0}:
        return

    add_code(f"    add {get_register(name)}, {get_register(value)}")

def sub(name, value):
    if value in {'1',1}:
        add_code(f"    dec {get_register(name)}")
        return

    if value in {'0',0}:
        return

    add_code(f"    sub {get_register(name)}, {get_register(value)}")

def bit_or(name, value):
    add_code(f"    or {get_register(name)}, {get_register(value)}")

def bit_xor(name, value):
    add_code(f"    xor {get_register(name)}, {get_register(value)}")

def bit_and(name, value):
    add_code(f"    and {get_register(name)}, {get_register(value)}")

def mul(name, value):
    if value in {'1',1}:
        return

    if value in {'0',0}:
        mv(name,0)
        return

    add_code(f"    mul {get_register(name)}, {get_register(value)}")

def div(name, value):
    if value in {'1',1}:
        return

    if value in {'0',0}:
        mv(name,0)
        raise ValueError("can't divide by zero luluz")

    add_code(f"    div {get_register(name)}, {get_register(value)}")

def add_str_const(name, text):
    add_data(f"{name} db {text}")
    add_data(f"{name}_len = $-{name}")
    Data.data_buffers.append(name)

def new_str(text):
    add_str_const(f"str{Data.str_literals_count}",text.replace("\\n",'",10,13,"'))
    Data.str_literals_count += 1
    return f"str{Data.str_literals_count-1}"

def buf(name, length):
    add_bss(f"{name}: resb {length}")
    add_data(f"{name}_len: equ {length}")
    Data.bss_buffers[name] = length

def push(var):
    add_code(f"    push {get_register(var)}")

def pop(var):
    add_code(f"    pop {get_or_set_register(var)}")

def syscall(number):
    mv('rax',number)
    add_code('    syscall')
