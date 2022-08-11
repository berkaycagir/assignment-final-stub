import os
from pathlib import Path
import sys
import ast
from dataclasses import dataclass
from typing import Callable
from filecmp import cmp

################################################################################
# repr for classes in the ast module
################################################################################

indent_amount = 2


def indent_stmt():
    return " " * indent_amount


def indent():
    global indent_amount
    indent_amount += 2


def dedent():
    global indent_amount
    indent_amount -= 2


def str_Module(self):
    indent()
    body = "".join([str(s) for s in self.body])
    dedent()
    return body


ast.Module.__str__ = str_Module


def repr_Module(self):
    return "Module(" + repr(self.body) + ")"


ast.Module.__repr__ = repr_Module


def str_Expr(self):
    return indent_stmt() + str(self.value) + "\n"


ast.Expr.__str__ = str_Expr


def repr_Expr(self):
    return indent_stmt() + "Expr(" + repr(self.value) + ")"


ast.Expr.__repr__ = repr_Expr


def str_Assign(self):
    return indent_stmt() + str(self.targets[0]) + " = " + str(self.value) + "\n"


ast.Assign.__str__ = str_Assign


def repr_Assign(self):
    return (
        indent_stmt() + "Assign(" + repr(self.targets) + ", " + repr(self.value) + ")"
    )


ast.Assign.__repr__ = repr_Assign


def str_AnnAssign(self):
    return (
        indent_stmt()
        + str(self.target)
        + " : "
        + str(self.annotation)
        + " = "
        + str(self.value)
        + "\n"
    )


ast.AnnAssign.__str__ = str_AnnAssign


def repr_AnnAssign(self):
    return (
        indent_stmt()
        + "AnnAssign("
        + repr(self.target)
        + ", "
        + repr(self.annotation)
        + ", "
        + repr(self.value)
        + ")"
    )


ast.AnnAssign.__repr__ = repr_AnnAssign


def str_Return(self):
    return indent_stmt() + "return " + str(self.value) + "\n"


ast.Return.__str__ = str_Return


def repr_Return(self):
    return indent_stmt() + "Return(" + repr(self.value) + ")"


ast.Return.__repr__ = repr_Return


def str_Name(self):
    return self.id


ast.Name.__str__ = str_Name


def repr_Name(self):
    return "Name(" + repr(self.id) + ")"


ast.Name.__repr__ = repr_Name


def str_Constant(self):
    return str(self.value)


ast.Constant.__str__ = str_Constant


def repr_Constant(self):
    return "Constant(" + repr(self.value) + ")"


ast.Constant.__repr__ = repr_Constant

supported_ops = [
    (ast.Add, "+", "Add()"),
    (ast.Sub, "-", "Sub()"),
    (ast.Mult, "*", "Mult()"),
    (ast.FloorDiv, "//", "FloorDiv()"),
    (ast.Mod, "%", "Mod()"),
    (ast.And, "and", "And()"),
    (ast.Or, "or", "Or()"),
    (ast.USub, "-", "USub()"),
    (ast.Not, "not", "Not()"),
]

for op_cls, op_name, op_ast_name in supported_ops:
    op_cls.__str__ = (lambda op_name: lambda self: op_name)(op_name)
    op_cls.__repr__ = (lambda op_ast_name: lambda self: op_ast_name)(op_ast_name)


def str_BinOp(self):
    return "(" + str(self.left) + " " + str(self.op) + " " + str(self.right) + ")"


ast.BinOp.__str__ = str_BinOp


def repr_BinOp(self):
    return (
        "BinOp("
        + repr(self.left)
        + ", "
        + repr(self.op)
        + ", "
        + repr(self.right)
        + ")"
    )


ast.BinOp.__repr__ = repr_BinOp


def str_BoolOp(self):
    return (
        "(" + str(self.values[0]) + " " + str(self.op) + " " + str(self.values[1]) + ")"
    )


ast.BoolOp.__str__ = str_BoolOp


def repr_BoolOp(self):
    return repr(self.values[0]) + " " + repr(self.op) + " " + repr(self.values[1])


ast.BoolOp.__repr__ = repr_BoolOp


def str_UnaryOp(self):
    return str(self.op) + " " + str(self.operand)


ast.UnaryOp.__str__ = str_UnaryOp


def repr_UnaryOp(self):
    return "UnaryOp(" + repr(self.op) + ", " + repr(self.operand) + ")"


ast.UnaryOp.__repr__ = repr_UnaryOp


def str_Call(self):
    return str(self.func) + "(" + ", ".join([str(arg) for arg in self.args]) + ")"


ast.Call.__str__ = str_Call


def repr_Call(self):
    return "Call(" + repr(self.func) + ", " + repr(self.args) + ")"


ast.Call.__repr__ = repr_Call


def str_If(self):
    header = indent_stmt() + "if " + str(self.test) + ":\n"
    indent()
    thn = "".join(str(s) for s in self.body)
    els = "".join(str(s) for s in self.orelse)
    dedent()
    return header + thn + indent_stmt() + "else:\n" + els


ast.If.__str__ = str_If


def repr_If(self):
    return (
        "If("
        + repr(self.test)
        + ", "
        + repr(self.body)
        + ", "
        + repr(self.orelse)
        + ")"
    )


ast.If.__repr__ = repr_If


def str_IfExp(self):
    return (
        "("
        + str(self.body)
        + " if "
        + str(self.test)
        + " else "
        + str(self.orelse)
        + ")"
    )


ast.IfExp.__str__ = str_IfExp


def repr_IfExp(self):
    return (
        "IfExp("
        + repr(self.body)
        + ", "
        + repr(self.test)
        + ", "
        + repr(self.orelse)
        + ")"
    )


ast.IfExp.__repr__ = repr_IfExp


def str_While(self):
    header = indent_stmt() + "while " + str(self.test) + ":\n"
    indent()
    body = "".join(str(s) for s in self.body)
    dedent()
    return header + body


ast.While.__str__ = str_While


def repr_While(self):
    return (
        "While("
        + repr(self.test)
        + ", "
        + repr(self.body)
        + ", "
        + repr(self.orelse)
        + ")"
    )


ast.While.__repr__ = repr_While


def str_Compare(self):
    return str(self.left) + " " + str(self.ops[0]) + " " + str(self.comparators[0])


ast.Compare.__str__ = str_Compare


def repr_Compare(self):
    return (
        "Compare("
        + repr(self.left)
        + ", "
        + repr(self.ops)
        + ", "
        + repr(self.comparators)
        + ")"
    )


ast.Compare.__repr__ = repr_Compare


def str_Eq(self):
    return "=="


ast.Eq.__str__ = str_Eq


def repr_Eq(self):
    return "Eq()"


ast.Eq.__repr__ = repr_Eq


def str_NotEq(self):
    return "!="


ast.NotEq.__str__ = str_NotEq


def repr_NotEq(self):
    return "NotEq()"


ast.NotEq.__repr__ = repr_NotEq


def str_Lt(self):
    return "<"


ast.Lt.__str__ = str_Lt


def repr_Lt(self):
    return "Lt()"


ast.Lt.__repr__ = repr_Lt


def str_LtE(self):
    return "<="


ast.LtE.__str__ = str_Lt


def repr_LtE(self):
    return "LtE()"


ast.LtE.__repr__ = repr_LtE


def str_Gt(self):
    return ">"


ast.Gt.__str__ = str_Gt


def repr_Gt(self):
    return "Gt()"


ast.Gt.__repr__ = repr_Gt


def str_GtE(self):
    return ">="


ast.GtE.__str__ = str_GtE


def repr_GtE(self):
    return "GtE()"


ast.GtE.__repr__ = repr_GtE


def str_Tuple(self):
    return "(" + ", ".join(str(e) for e in self.elts) + ",)"


ast.Tuple.__str__ = str_Tuple


def repr_Tuple(self):
    return "Tuple(" + repr(self.elts) + ")"


ast.Tuple.__repr__ = repr_Tuple


def str_List(self):
    return "[" + ", ".join(str(e) for e in self.elts) + ",]"


ast.List.__str__ = str_List


def repr_List(self):
    return "List[" + repr(self.elts) + "]"


ast.List.__repr__ = repr_List


def str_Subscript(self):
    return str(self.value) + "[" + str(self.slice) + "]"


ast.Subscript.__str__ = str_Subscript


def repr_Subscript(self):
    return (
        "Subscript("
        + repr(self.value)
        + ", "
        + repr(self.slice)
        + ", "
        + repr(self.ctx)
        + ")"
    )


ast.Subscript.__repr__ = repr_Subscript


def str_FunctionDef(self):
    body = ""
    if isinstance(self.args, ast.arguments):
        params = ", ".join(a.arg + ":" + str(a.annotation) for a in self.args.args)
    else:
        params = ", ".join(x + ":" + str(t) for (x, t) in self.args)
    indent()
    if isinstance(self.body, list):
        body = "".join(str(s) for s in self.body)
    elif isinstance(self.body, dict):
        body = ""
        for (l, ss) in self.body.items():
            body += l + ":\n"
            indent()
            body += "".join(str(s) for s in ss)
            dedent()
    dedent()
    return (
        indent_stmt()
        + "def "
        + self.name
        + "("
        + params
        + ")"
        + " -> "
        + str(self.returns)
        + ":\n"
        + body
        + "\n"
    )


def repr_FunctionDef(self):
    return (
        "FunctionDef(" + self.name + "," + repr(self.args) + "," + repr(self.body) + ")"
    )


ast.FunctionDef.__str__ = str_FunctionDef
ast.FunctionDef.__repr__ = repr_FunctionDef


def str_Lambda(self):
    if isinstance(self.args, ast.arguments):
        params = ", ".join(a.arg for a in self.args.args)
    else:
        params = ", ".join(self.args)
    body = str(self.body)
    return "(lambda " + params + ": " + body + ")"


def repr_Lambda(self):
    return "Lambda(" + repr(self.args) + "," + repr(self.body) + ")"


ast.Lambda.__str__ = str_Lambda
ast.Lambda.__repr__ = repr_Lambda


################################################################################
# __eq__ and __hash__ for classes in the ast module
################################################################################


def eq_Name(self, other):
    if isinstance(other, ast.Name):
        return self.id == other.id
    else:
        return False


ast.Name.__eq__ = eq_Name


def hash_Name(self):
    return hash(self.id)


ast.Name.__hash__ = hash_Name

################################################################################
# map compare operators to their encoding
# could be done as a dictionary, but there is neither __hash__ nor __eq__
################################################################################


def cmp_to_code(cmp) -> str:
    match cmp:
        case ast.Eq():
            return "e"
        case ast.NotEq():
            return "ne"
        case ast.Lt():
            return "l"
        case ast.LtE():
            return "le"
        case ast.Gt():
            return "g"
        case ast.GtE():
            return "ge"
        case _:
            raise Exception("can't match cmp_to_code: " + cmp)


################################################################################
# Generating unique names
################################################################################

name_id = 0


def generate_name(name):
    global name_id
    ls = name.split(".")
    new_id = name_id
    name_id += 1
    return ls[0] + "." + str(new_id)


################################################################################
# AST classes
################################################################################

Binding = tuple[ast.Name, ast.expr]
Temporaries = list[Binding]


class Type:
    pass


# Obsolete, use Begin instead. -Jeremy
# @dataclass
# class Let(expr):
#     var : expr
#     rhs : expr
#     body : expr

#     def __str__(self):
#         return '(let ' + str(self.var) + ' = ' + str(self.rhs) + ' in ' \
#             + str(self.body) + ')'

# Obsolete, use Begin instead. -Jeremy
# def make_lets(bs: Temporaries, e: expr) -> expr:
#     result = e
#     for (x,rhs) in reversed(bs):
#         result = Let(x, rhs, result)
#     return result


def make_assigns(bs: Temporaries) -> list[ast.stmt]:
    return [ast.Assign([x], rhs) for (x, rhs) in bs]


def make_begin(bs: Temporaries, e: ast.expr) -> ast.expr:
    if len(bs) > 0:
        return Begin(make_assigns(bs), e)
    else:
        return e


# A lambda expression whose parameters are annotated with types.
@dataclass
class AnnLambda(ast.expr):
    params: list[tuple[str, Type]]
    returns: Type
    body: ast.expr

    def __str__(self):
        return (
            "lambda ["
            + ", ".join([x + ":" + str(t) for (x, t) in self.params])
            + "] -> "
            + str(self.returns)
            + ": "
            + str(self.body)
        )


# An uninitialized value of a given type.
# Needed for boxing local variables.
@dataclass
class Uninitialized(ast.expr):
    ty: Type

    def __str__(self):
        return "uninit[" + str(self.ty) + "]"


@dataclass
class CProgram:
    body: list[ast.stmt]

    def __str__(self):
        result = ""
        for l, ss in self.body:  # type: ignore
            result += l + ":\n"
            indent()
            result += "".join([str(s) for s in ss]) + "\n"
            dedent()
        return result


@dataclass
class CProgramDefs:
    defs: list[ast.stmt]

    def __str__(self):
        return "\n".join([str(d) for d in self.defs]) + "\n"


@dataclass
class Goto(ast.stmt):
    label: str

    def __str__(self):
        return indent_stmt() + "goto " + self.label + "\n"


@dataclass
class Allocate(ast.expr):
    length: int
    ty: Type

    def __str__(self):
        return "allocate(" + str(self.length) + "," + str(self.ty) + ")"


@dataclass
class AllocateClosure(ast.expr):
    length: int
    ty: Type
    arity: int

    def __str__(self):
        return (
            "alloc_clos("
            + str(self.length)
            + ","
            + str(self.ty)
            + ","
            + str(self.arity)
            + ")"
        )


@dataclass
class AllocateArray(ast.expr):
    length: ast.expr
    ty: Type

    def __str__(self):
        return "alloc_array(" + str(self.length) + "," + str(self.ty) + ")"


@dataclass
class Collect(ast.stmt):
    size: int

    def __str__(self):
        return indent_stmt() + "collect(" + str(self.size) + ")\n"


@dataclass
class CollectArray(ast.stmt):
    size: ast.expr

    def __str__(self):
        return indent_stmt() + "collect_array(" + str(self.size) + ")\n"


@dataclass
class Begin(ast.expr):
    body: list[ast.stmt]
    result: ast.expr

    def __str__(self):
        indent()
        stmts = "".join([str(s) for s in self.body])
        end = indent_stmt() + "produce " + str(self.result)
        dedent()
        return "{\n" + stmts + end + "}"


@dataclass
class GlobalValue(ast.expr):
    name: str

    def __str__(self):
        return str(self.name)


@dataclass(eq=True)
class IntType(Type):
    def __str__(self):
        return "int"


@dataclass(eq=True)
class BoolType(Type):
    def __str__(self):
        return "bool"


@dataclass(eq=True)
class VoidType(Type):
    def __str__(self):
        return "void"


@dataclass(eq=True)
class Bottom(Type):
    def __str__(self):
        return "bottom"


@dataclass(eq=True)
class TupleType(Type):
    types: list[Type]

    def __str__(self):
        return "tuple[" + ",".join(map(str, self.types)) + "]"


@dataclass(eq=True)
class FunctionType:
    param_types: list[Type]
    ret_type: Type

    def __str__(self):
        return (
            "Callable[["
            + ",".join(map(str, self.param_types))
            + "]"
            + ", "
            + str(self.ret_type)
            + "]"
        )


@dataclass(eq=True)
class ListType(Type):
    elt_ty: Type

    def __str__(self):
        return "list[" + str(self.elt_ty) + "]"


@dataclass
class FunRef(ast.expr):
    name: str
    arity: int

    def __str__(self):
        return "{" + self.name + "}"


@dataclass
class TailCall(ast.stmt):
    func: ast.expr
    args: list[ast.expr]

    def __str__(self):
        return (
            indent_stmt()
            + "tail "
            + str(self.func)
            + "("
            + ", ".join([str(e) for e in self.args])
            + ")\n"
        )


# like a Tuple, but also stores the function's arity
@dataclass
class Closure(ast.expr):
    arity: int
    args: list[ast.expr]
    __match_args__ = ("arity", "args")

    def __str__(self):
        return (
            "closure["
            + repr(self.arity)
            + "]("
            + ", ".join([str(e) for e in self.args])
            + ")"
        )


@dataclass
class Inject(ast.expr):
    value: ast.expr
    typ: Type
    __match_args__ = ("value", "typ")

    def __str__(self):
        return "inject(" + str(self.value) + ", " + str(self.typ) + ")"


@dataclass
class Project(ast.expr):
    value: ast.expr
    typ: Type
    __match_args__ = ("value", "typ")

    def __str__(self):
        return "project(" + str(self.value) + ", " + str(self.typ) + ")"


@dataclass
class TagOf(ast.expr):
    value: ast.expr
    __match_args__ = ("value",)

    def __str__(self):
        return "tagof(" + str(self.value) + ")"


@dataclass
class ValueOf(ast.expr):
    value: ast.expr
    typ: Type
    __match_args__ = ("value", "typ")

    def __str__(self):
        return "valueof(" + str(self.value) + ", " + str(self.typ) + ")"


@dataclass(eq=True)
class AnyType(Type):
    def __str__(self):
        return "any"


# Base class of runtime values
class Value:
    pass


block_id = 0


def create_block(
    stmts: list[ast.stmt], basic_blocks: dict[str, list[ast.stmt]]
) -> Goto:
    "stuff statments into a new basic block; return a jump to it"
    global block_id
    label = "block" + str(block_id)
    block_id += 1
    basic_blocks[label_name(label)] = stmts
    return Goto(label)


################################################################################
# Miscellaneous Auxiliary Functions
################################################################################


def input_int() -> int:
    return int(input())


def unzip(ls):
    xs, ys = [], []
    for (x, y) in ls:
        xs += [x]
        ys += [y]
    return (xs, ys)


def align(n: int, alignment: int) -> int:
    if 0 == n % alignment:
        return n
    else:
        return n + (alignment - n % alignment)


def bool2int(b):
    if b:
        return 1
    else:
        return 0


label_name: Callable[[str], str] = (
    (lambda n: "_" + n) if sys.platform == "darwin" else (lambda n: n)
)

# def label_name(n: str) -> str:
#     if sys.platform == "darwin":
#         return '_' + n
#     else:
#         return n


def ast_loc(obj: ast.AST):
    return (
        "beginning line: "
        + repr(obj.lineno)
        + " ending line: "
        + repr(obj.end_lineno)
        + " beginning column offset: "
        + repr(obj.col_offset)
        + " ending column offset: "
        + repr(obj.end_col_offset)
    )


tracing = False


def enable_tracing():
    global tracing
    tracing = True


def trace(msg):
    if tracing:
        print(msg, file=sys.stderr)


def is_python_extension(filename):
    s = filename.split(".")
    if len(s) > 1:
        return s[1] == "py"
    else:
        return False


def ensure_final_newline(filename: Path):
    # check whether file is empty
    if os.stat(filename).st_size != 0:
        with open(filename, "r+b") as f:
            # must open as b to seek from end; read last character
            f.seek(-1, 2)
            b = f.read(1)
            newline = bytes("\n", "utf-8")
            if b != newline:
                f.write(newline)


compare_files: Callable[[Path, Path], bool] = lambda file1, file2: cmp(
    file1, file2, shallow=False
)


# Given the `ast` output of a pass and a test program (root) name,
# runs the interpreter on the program and compares the output to the
# expected "golden" output.
def test_pass(passname, interp, program_root, _ast, compiler_name) -> int:
    input_file = Path(program_root + ".in")
    output_file = Path(program_root + ".out")
    golden_file = Path(program_root + ".golden")
    stdin = sys.stdin
    stdout = sys.stdout
    sys.stdin = open(input_file, "r")
    sys.stdout = open(output_file, "w")
    interp(_ast)
    sys.stdin = stdin
    sys.stdout = stdout
    ensure_final_newline(output_file)
    ensure_final_newline(golden_file)
    result = compare_files(output_file, golden_file)
    if result:
        trace(
            "compiler "
            + compiler_name
            + " success on pass "
            + passname
            + " on test\n"
            + program_root
            + "\n"
        )
        return 1
    else:
        print(
            "compiler "
            + compiler_name
            + " failed pass "
            + passname
            + " on test\n"
            + program_root
            + "\n"
        )
        output = open(output_file).read()
        expected = open(golden_file).read()
        print("Output: " + output)
        print("Expected: " + expected)
        return 0


def validate_tests(path: Path, lang: str, interp) -> bool:
    """check if all tests for `lang` work with `interp`"""
    test_count = 0
    success_count = 0
    tests = get_all_tests_for(path)
    for test_filename in tests:
        program_root = str(test_filename).split(".")[0]
        with open(test_filename) as source:
            program = ast.parse(source.read())
        test_count += 1
        success_count += test_pass("--", interp, program_root, program, lang)
    return test_count == success_count


def compile_and_test(
    program_filename: Path,
    compiler,
    compiler_name: str,
    type_check_P,
    interp_P,
    type_check_C,
    interp_C,
):
    def execute_pass(
        passname: str, program: ast.Module, interp=interp_P, type_check=None
    ):
        nonlocal total_passes, successful_passes
        if hasattr(compiler, passname):
            trace("\n#" + passname + "\n")
            if type_check:
                type_check(program)
            program_out = getattr(compiler, passname)(program)
            trace(program_out)
            trace("")
            total_passes += 1
            successful_passes += test_pass(
                passname, interp, program_root, program_out, compiler_name
            )
        else:
            program_out = program
        return program_out

    total_passes = 0
    successful_passes = 0
    from interp_x86.eval_x86 import interp_x86

    program_root = str(program_filename).split(".")[0]
    with open(program_filename) as source:
        program = ast.parse(source.read())

    trace("\n# source program\n")
    trace(program)
    trace("")

    program = execute_pass("shrink", program)
    program = execute_pass("reveal_functions", program, type_check=type_check_P)
    program = execute_pass("limit_functions", program, type_check=type_check_P)
    program = execute_pass("resolve", program, type_check=type_check_P)
    program = execute_pass("check_bounds", program, type_check=type_check_P)
    program = execute_pass("expose_allocation", program, type_check=type_check_P)
    program = execute_pass("remove_complex_operands", program)
    program = execute_pass("explicate_control", program, interp=interp_C)

    if type_check_C:
        trace("\n**********\n type check C \n**********\n")
        type_check_C(program)

    trace("\n**********\n select \n**********\n")
    pseudo_x86 = compiler.select_instructions(program)
    trace(pseudo_x86)
    trace("")
    total_passes += 1
    test_x86 = False  # doesn't know about GC!
    if test_x86:
        successful_passes += test_pass(
            "select instructions", interp_x86, program_root, pseudo_x86, compiler_name
        )

    trace("\n**********\n assign \n**********\n")
    almost_x86 = compiler.assign_homes(pseudo_x86)
    trace(almost_x86)
    trace("")
    total_passes += 1
    if test_x86:
        successful_passes += test_pass(
            "assign homes", interp_x86, program_root, almost_x86, compiler_name
        )

    trace("\n**********\n patch \n**********\n")
    x86 = compiler.patch_instructions(almost_x86)
    trace(x86)
    trace("")
    total_passes += 1
    if test_x86:
        successful_passes += test_pass(
            "patch instructions", interp_x86, program_root, x86, compiler_name
        )

    trace("\n# prelude and conclusion\n")
    final_program = compiler.prelude_and_conclusion(x86)
    trace(final_program)
    trace("")

    x86_filename = Path(program_root + ".s")
    with open(x86_filename, "w") as dest:
        dest.write(str(final_program))

    total_passes += 1

    input_file = Path(program_root + ".in")
    output_file = Path(program_root + ".out")
    golden_file = Path(program_root + ".golden")
    # Run the final x86 program
    emulate_x86 = False
    if emulate_x86:
        stdin = sys.stdin
        stdout = sys.stdout
        sys.stdin = open(input_file, "r")
        sys.stdout = open(output_file, "w")
        interp_x86(final_program)
        sys.stdin = stdin
        sys.stdout = stdout
    else:
        os.system("gcc runtime.o " + str(x86_filename))
        os.system("./a.out < " + str(input_file) + " > " + str(output_file))

    ensure_final_newline(output_file)
    ensure_final_newline(golden_file)
    result = compare_files(output_file, golden_file)
    if result:
        successful_passes += 1
        return (successful_passes, total_passes, 1)
    else:
        print(
            "compiler "
            + compiler_name
            + ", executable failed"
            + " on test "
            + program_root
        )
        return (successful_passes, total_passes, 0)


def trace_ast_and_concrete(_ast):
    trace("concrete syntax:")
    trace(_ast)
    trace("")
    trace("AST:")
    trace(repr(_ast))


# This function compiles the program without any testing
def compile(
    compiler,
    compiler_name: str,
    type_check_P,
    type_check_C,
    program_filename: Path,
):
    program_root = str(program_filename).split(".")[0]
    with open(program_filename) as source:
        program = ast.parse(source.read())

    trace("\n# type check\n")
    type_check_P(program)
    trace_ast_and_concrete(program)

    if hasattr(compiler, "shrink"):
        trace("\n# shrink\n")
        program = compiler.shrink(program)
        trace_ast_and_concrete(program)

    if hasattr(compiler, "uniquify"):
        trace("\n# uniquify\n")
        program = compiler.uniquify(program)
        trace_ast_and_concrete(program)

    if hasattr(compiler, "reveal_functions"):
        trace("\n# reveal functions\n")
        type_check_P(program)
        program = compiler.reveal_functions(program)
        trace_ast_and_concrete(program)

    if hasattr(compiler, "convert_assignments"):
        trace("\n# assignment conversion\n")
        type_check_P(program)
        program = compiler.convert_assignments(program)
        trace_ast_and_concrete(program)

    if hasattr(compiler, "convert_to_closures"):
        trace("\n# closure conversion\n")
        type_check_P(program)
        program = compiler.convert_to_closures(program)
        trace_ast_and_concrete(program)

    if hasattr(compiler, "expose_allocation"):
        trace("\n# expose allocation\n")
        type_check_P(program)
        program = compiler.expose_allocation(program)
        trace_ast_and_concrete(program)

    trace("\n# remove complex\n")
    program = compiler.remove_complex_operands(program)
    trace_ast_and_concrete(program)

    if hasattr(compiler, "explicate_control"):
        trace("\n# explicate control\n")
        program = compiler.explicate_control(program)
        trace_ast_and_concrete(program)

    if type_check_C:
        type_check_C(program)

    trace("\n# select instructions\n")
    pseudo_x86 = compiler.select_instructions(program)
    trace_ast_and_concrete(pseudo_x86)

    trace("\n# assign homes\n")
    almost_x86 = compiler.assign_homes(pseudo_x86)
    trace_ast_and_concrete(almost_x86)

    trace("\n# patch instructions\n")
    x86 = compiler.patch_instructions(almost_x86)
    trace_ast_and_concrete(x86)

    trace("\n# prelude and conclusion\n")
    x86 = compiler.prelude_and_conclusion(x86)
    trace_ast_and_concrete(x86)

    # Output x86 program to the .s file
    x86_filename = Path(program_root + ".s")
    with open(x86_filename, "w") as dest:
        dest.write(str(x86))


# Given a test file name, the name of a language, a compiler, a type
# checker and interpreter for the language, and an interpeter for the
# C intermediate language, run all the passes in the compiler,
# checking that the resulting programs produce output that matches the
# golden file.
def run_one_test(
    test: Path,
    lang: str,
    compiler,
    compiler_name: str,
    type_check_P,
    interp_P,
    type_check_C,
    interp_C,
):
    # test_root = test.split(".")[0]
    # test_name = test_root.split("/")[-1]
    return compile_and_test(
        test, compiler, compiler_name, type_check_P, interp_P, type_check_C, interp_C
    )


# Given the name of a language, a compiler, the compiler's name, a
# type checker and interpreter for the language, and an interpreter
# for the C intermediate language, test the compiler on all the tests
# in the directory of for the given language, i.e., all the
# python files in ./tests/<language>.
def run_tests(
    path: Path,
    lang: str,
    compiler,
    compiler_name: str,
    type_check_P,
    interp_P,
    type_check_C,
    interp_C,
) -> None:
    tests = get_all_tests_for(path)

    # Compile and run each test program, comparing output to the golden file.
    successful_passes = 0
    total_passes = 0
    successful_tests = 0
    total_tests = 0
    for test in tests:
        print("test file: " + str(test))
        (succ_passes, tot_passes, succ_test) = run_one_test(
            test,
            lang,
            compiler,
            compiler_name,
            type_check_P,
            interp_P,
            type_check_C,
            interp_C,
        )
        successful_passes += succ_passes
        total_passes += tot_passes
        successful_tests += succ_test
        total_tests += 1

    # Report the pass/fails
    print(
        "tests: "
        + repr(successful_tests)
        + "/"
        + repr(total_tests)
        + " for compiler "
        + compiler_name
        + " on language "
        + lang
    )
    print(
        "passes: "
        + repr(successful_passes)
        + "/"
        + repr(total_passes)
        + " for compiler "
        + compiler_name
        + " on language "
        + lang
    )


def get_all_tests_for(path: Path):
    """Collect all the test program file names for language `lang`."""
    return list(path.glob("*.py"))
