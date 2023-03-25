import argparse
from subprocess import run as shell_exec
from sa_parser import *

parser = argparse.ArgumentParser(description='sard compiler')
parser.add_argument('source')
parser.add_argument('-o','--out',dest="output")
parser.add_argument('-e','--entry',dest="entry",default="main")
parser.add_argument('-l','--library', dest="is_lib",action='store_true')
parser.add_argument('-Fargs','--fix-arguments',dest="argsfix",action='store_true')
parser.add_argument('-a','--only-asm',dest="only_asm",action='store_true')

args = parser.parse_args()
ParseOptions.argsfix = args.argsfix
ParseOptions.is_lib = args.is_lib

src = args.source
out = src.replace('.sard','').replace('.srd','')
asm = out + '.asm'
obj = out + '.o'
fasm_format = f"format ELF64{'' if args.is_lib else ' executable'}"

ParseOptions.current_file = src
#ParseOptions.ignored_files.append(src)
ParseOptions.entry = args.entry

if not args.is_lib:
    Data.code = "segment readable executable\n"
    Data.code += f"entry {args.entry}\n"
    Data.data = "segment readable executable\n"

sa_include(src)

with open(asm,"w") as f:
    f.write(f"{fasm_format}\n{Data.data}\n{Data.code}")

if args.only_asm:
    print(f"assembly written to `{asm}`")
    exit(0)

shell_exec(["fasm", asm],check=True)

if args.is_lib:
    if args.output and args.output != obj:
            shell_exec(["mv",obj,args.output])

    print(f"library written to `{args.output if args.output else obj}`")
else:
    shell_exec(["chmod","+x",out])
    if args.output and args.output != out:
        shell_exec(["mv",out,args.output])

    print(f"executable written to `{args.output if args.output else out}`")

shell_exec(["rm",asm], check=True)
print(f"removed compilation-time assembly ({asm})")
