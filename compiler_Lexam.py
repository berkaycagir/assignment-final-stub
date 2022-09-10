from priority_queue import PriorityQueue
from type_check_Cexam import TypeCheckCexam
from type_check_Lexam import TypeCheckLexam
from ast import *
from cProfile import label
from typing import Optional
from register_allocation import build_interference, color_graph
from register_allocation import color_to_register, all_argument_passing_registers, callee_saved_registers
from utils import *
from x86_ast import *
from ast import List
from dataclasses import dataclass, field
from pprint import pprint
from compiler import Compiler, Binding, Temporaries


@dataclass
class PreliminaryPatchUnreachableBlocks(Compiler):
    """
    Preliminary compiler version that removes all unreachable blocks in the assign_homes pass
    to avoid errors in the allocate_registers call.
    """

    def cleanup_blocks(self, basic_blocks: dict[str, list[instr]], start: str) -> dict[str, list[instr]]:
        """
        Returns a dict like basic_blocks, but with all blocks unreachable from start removed.
        """
        res: dict[str, list[instr]] = {}
        queue = PriorityQueue(lambda _, __: True)
        queue.push(start)
        while not queue.empty():
            next_block = queue.pop()
            block_instrs = basic_blocks[next_block]
            for i in block_instrs:
                match i:
                    case Jump(label) | JumpIf(_, label):
                        if label not in res:
                            res[label] = []
                            queue.push(label)
            res[next_block] = block_instrs
        return res

    def assign_homes_def(self, p: FunctionDef) -> FunctionDef:
        match p:
            case FunctionDef(name, params, fbody, dl, returns, comment):
                fbody = self.cleanup_blocks(fbody, Label(name + 'start'))
                p.body = fbody
                home = self.allocate_registers(p)
                new_body = dict()
                for block_name, block_items in fbody.items():
                    new_body[block_name] = self.assign_homes_instrs(block_items, home)
                result = FunctionDef(name, params, new_body, dl, returns, comment)
                result.stack_space = p.stack_space
                result.root_stack_space = p.root_stack_space
                result.used_callee = p.used_callee
                return result
            case _:
                raise Exception("THIS IS UNFAIR!")


@dataclass
class PreliminaryPatchImmediates(PreliminaryPatchUnreachableBlocks):
    """
    Preliminary compiler version that patches immediates so all values between
    -2^64 <= imm < 2^64 are translated to a valid program.
    """

    def shrink_exp(self, e: expr) -> expr:
        match e:
            case UnaryOp(USub(), Constant(n)):
                return Constant(-n)
            case _:
                return super().shrink_exp(e)

    def patch_instr(self, i: instr) -> list[instr]:
        match i:
            case Instr(istr, [Immediate(imm), arg2]) if imm > MAX_INT_32 or imm < MIN_INT_32:
                # patch immediates if imm >= 2^32 or imm < -2^32
                assert MIN_INT_64 <= imm <= MAX_INT_64, f'Immediate is not 64 bit encodable: {imm}'
                match arg2:
                    case Reg() if istr.startswith('mov'):
                        # valid 64-bit movq/movabsq instruction
                        return [i]
                    case Reg('rax'):
                        # use rdi as tmp register
                        return [
                            Instr('pushq', [Reg('rdi')]),
                            Instr('movabsq', [Immediate(imm), Reg('rdi')]),
                            Instr(istr, [Reg('rdi'), arg2]),
                            Instr('popq', [Reg('rdi')]),
                        ]
                    case _:
                        # use rax as tmp register
                        return [
                            Instr('pushq', [Reg('rax')]),
                            Instr('movabsq', [Immediate(imm), Reg('rax')]),
                            Instr(istr, [Reg('rax'), arg2]),
                            Instr('popq', [Reg('rax')]),
                        ]
            case Instr(istr, [Immediate(imm)]) if imm > MAX_INT_32 or imm < MIN_INT_32:
                assert MIN_INT_64 <= imm <= MAX_INT_64, f'Immediate is not 64 bit encodable: {imm}'
                return [
                    Instr('pushq', [Reg('rax')]),
                    Instr('movabsq', [Immediate(imm), Reg('rax')]),
                    Instr(istr, [Reg('rax')]),
                    Instr('popq', [Reg('rax')]),
                ]
            case _:
                return super().patch_instr(i)


@dataclass
class CompilerLexam1(PreliminaryPatchImmediates):
    """
    Compiler task 1: Implementation of operators on integers:
    - // (division)
    - %  (modulo)
    - *  (multiplication)
    """

    ############################################################################
    # shrink
    # reveal functions
    # limit functions
    # resolve
    # check bounds
    # expose allocation
    ############################################################################

    ############################################################################
    # remove complex operands
    ############################################################################

    def rco_exp(self, e: expr, need_atomic: bool) -> tuple[expr, Temporaries]:
        match e:
            case BinOp(e1, Mod() | FloorDiv() as op, Constant(c)):
                atm1, tmps1 = self.rco_exp(e1, True)
                # e1 // const => var = const; e1 // var
                divtmp = generate_name('divtmp')
                tmps2 = [(Name(divtmp), Constant(c))]
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    return (Name(fresh_tmp), tmps1 + tmps2 + [(Name(fresh_tmp), BinOp(atm1, op, Name(divtmp)))])
                return (BinOp(atm1, op, Name(divtmp)), tmps1 + tmps2)
            case _:
                return super().rco_exp(e, need_atomic)

    ############################################################################
    # explicate control
    ############################################################################

    ############################################################################
    # select instructions
    ############################################################################

    def select_stmt(self, s: stmt, name: str) -> list[instr]:
        match s:
            case Assign([Name(var)], BinOp(atm1, Mult(), atm2)):
                arg1 = self.select_arg(atm1)
                arg2 = self.select_arg(atm2)
                match (arg1, arg2):
                    case (Variable(var2), _) if var == var2:
                        return [Instr('imulq', [arg2, Variable(var)])]
                    case (_, Variable(var2)) if var == var2:
                        return [Instr('imulq', [arg1, Variable(var)])]
                return [Instr('movq', [arg1, Variable(var)]),
                        Instr('imulq', [arg2, Variable(var)])]
            case Assign([Name(var)], BinOp(atm1, Mod() | FloorDiv() as op, Name(_) as atm2)):
                arg1 = self.select_arg(atm1)
                arg2 = self.select_arg(atm2)
                res = Reg('rax') if type(op) is FloorDiv else Reg('rdx')
                return [
                    Instr('movq', [arg1, Reg('rax')]),
                    Instr('cqto', []),
                    Instr('idivq', [arg2]),
                    Instr('movq', [res, Variable(var)])
                ]
            case _:
                return super().select_stmt(s, name)

    ############################################################################
    # patch instructions
    ############################################################################

    def patch_instr(self, i: instr) -> list[instr]:
        match i:
            case Instr('imulq', [arg1, Deref() as dest]):
                return [Instr('movq', [dest, Reg('rax')]),
                        Instr('imulq', [arg1, Reg('rax')]),
                        Instr('movq', [Reg('rax'), dest])]
            case _:
                return super().patch_instr(i)

    ############################################################################
    # prelude and conclusion
    ############################################################################


@dataclass
class CompilerLexam2(CompilerLexam1):
    """
    Compiler task 1: Implementation of loops:
    - while statement
    - updated register allocation (also see register_allocation.py)
    """

    ############################################################################
    # shrink
    ############################################################################

    def shrink_stmt(self, s: stmt) -> stmt:
        match s:
            case While(cond, body, []):
                return While(self.shrink_exp(cond), [self.shrink_stmt(s) for s in body], [])
            case _:
                return super().shrink_stmt(s)

    ############################################################################
    # reveal functions
    ############################################################################

    def reveal_stmt(self, s: stmt, funs) -> stmt:
        match s:
            case While(cond, body, []):
                return While(self.reveal_exp(cond, funs), [self.reveal_stmt(s, funs) for s in body], [])
            case _:
                return super().reveal_stmt(s, funs)

    ############################################################################
    # limit functions
    ############################################################################

    def limit_stmt(self, s: stmt, repl: dict[str, expr]) -> stmt:
        match s:
            case While(cond, body, []):
                return While(self.limit_exp(cond, repl), [self.limit_stmt(s, repl) for s in body], [])
            case _:
                return super().limit_stmt(s, repl)

    ############################################################################
    # resolve
    # check bounds
    ############################################################################

    ############################################################################
    # expose allocation
    ############################################################################

    def expose_stmt(self, s: stmt) -> stmt:
        match s:
            case While(cond, body, []):
                return While(self.expose_exp(cond), [self.expose_stmt(s) for s in body], [])
            case _:
                return super().expose_stmt(s)

    ############################################################################
    # remove complex operands
    ############################################################################

    def rco_stmt(self, s: stmt) -> list[stmt]:
        match s:
            case While(cond, body, []):
                exp, tmps = self.rco_exp(cond, False)
                # like If(...), the condition doesn't need to be atomic
                return [While(make_begin(tmps, exp), [s for s1 in body for s in self.rco_stmt(s1)], [])]
            case _:
                return super().rco_stmt(s)

    ############################################################################
    # explicate control
    ############################################################################

    def explicate_stmt(self, s, cont, basic_blocks) -> list[stmt]:
        match s:
            case While(cond, body, []):
                goto_cond = Goto(cond_name := generate_name('condition'))
                loop_body = [goto_cond]
                for s in reversed(body):
                    loop_body = self.explicate_stmt(s, loop_body, basic_blocks)
                condition = self.explicate_pred(cond, loop_body, cont, basic_blocks)
                basic_blocks[Label(cond_name)] = condition
                return [goto_cond]
            case _:
                return super().explicate_stmt(s, cont, basic_blocks)

    ############################################################################
    # select statements
    # assign homes
    # patch instructions
    # prelude and conclusion
    ############################################################################


@dataclass
class CompilerLexam3(CompilerLexam2):

    ############################################################################
    # shrink
    ############################################################################

    def shrink_exp(self, e: expr) -> expr:
        match e:
            case ast.List(exprs, Load()):
                return ast.List([self.shrink_exp(e) for e in exprs], Load())
            case Subscript(exp, index, Load()):
                return Subscript(self.shrink_exp(exp), self.shrink_exp(index), Load())
            case _:
                return super().shrink_exp(e)

    def shrink_stmt(self, s: stmt) -> stmt:
        match s:
            case Assign([Subscript(exp, index, Store())], value):
                return Assign([Subscript(self.shrink_exp(exp), self.shrink_exp(index), Store())], self.shrink_exp(value))
            case _:
                return super().shrink_stmt(s)

    ############################################################################
    # reveal functions
    ############################################################################

    def reveal_exp(self, e: expr, funs) -> expr:
        match e:
            case ast.List(exprs, Load()):
                return ast.List([self.reveal_exp(e, funs) for e in exprs], Load())
            case Subscript(exp, index, Load()) if type(exp.has_type) is ListType:
                return Subscript(self.reveal_exp(exp, funs), self.reveal_exp(index, funs), Load())
            case _:
                return super().reveal_exp(e, funs)

    def reveal_stmt(self, s: stmt, funs) -> stmt:
        match s:
            case Assign([Subscript(exp, index, Store())], value) if type(exp.has_type) is ListType:
                return Assign([Subscript(self.reveal_exp(exp, funs), self.reveal_exp(index, funs), Store())], self.reveal_exp(value, funs))
            case _:
                return super().reveal_stmt(s, funs)

    ############################################################################
    # limit functions
    ############################################################################

    def limit_exp(self, e: expr, repl: dict[str, expr]) -> expr:
        match e:
            case ast.List(exprs, Load()):
                return ast.List([self.limit_exp(e, repl) for e in exprs], Load())
            case Subscript(exp, index, Load()) if type(exp.has_type) is ListType:
                return Subscript(self.limit_exp(exp, repl), self.limit_exp(index, repl), Load())
            case _:
                return super().limit_exp(e, repl)

    def limit_stmt(self, s: stmt, repl: dict[str, expr]) -> stmt:
        match s:
            case Assign([Subscript(exp, index, Store())], value) if type(exp.has_type) is ListType:
                return Assign([Subscript(self.limit_exp(exp, repl), self.limit_exp(index, repl), Store())], self.limit_exp(value, repl))
            case _:
                return super().limit_stmt(s, repl)

    ############################################################################
    # resolve
    ############################################################################

    def resolve_exp(self, e: expr) -> expr:
        match e:
            # L_array
            case Call(Name('len'), [exp]) if type(exp.has_type) is ListType:
                return Call(Name('array_len'), [self.resolve_exp(exp)])
            case ast.List(exprs, Load()):
                return ast.List([self.resolve_exp(e) for e in exprs], Load())
            case Subscript(exp, index, Load()) if type(exp.has_type) is ListType:
                return Call(Name('array_load'), [self.resolve_exp(exp), self.resolve_exp(index)])
            # L_fun
            case Call(e, args):
                return Call(self.resolve_exp(e), [self.resolve_exp(e) for e in args])
            # L_tup
            case Tuple(exprs, Load()):
                return Tuple([self.resolve_exp(e) for e in exprs], Load())
            case Subscript(exp, Constant(int), Load()):
                return Subscript(self.resolve_exp(exp), Constant(int), Load())
            case Call(Name('len'), [exp]):
                return Call(Name('len'), [self.resolve_exp(exp)])
            # L_if
            case IfExp(exp1, exp2, exp3):
                return IfExp(self.resolve_exp(exp1), self.resolve_exp(exp2), self.resolve_exp(exp3))
            case Compare(left, [cmp], [right]):
                return Compare(self.resolve_exp(left), [cmp], [self.resolve_exp(right)])
            # L_var
            case BinOp(left, op, right):
                return BinOp(self.resolve_exp(left), op, self.resolve_exp(right))
            case UnaryOp(op, e):
                return UnaryOp(op, self.resolve_exp(e))
            case _:
                return e

    def resolve_stmt(self, s: stmt) -> stmt:
        match s:
            # L_array
            case Assign([Subscript(exp, index, Store())], value) if type(exp.has_type) is ListType:
                return Expr(Call(Name('array_store'), [self.resolve_exp(exp), self.resolve_exp(index), self.resolve_exp(value)]))
            # L_while
            case While(test, body, []):
                return While(self.resolve_exp(test), [self.resolve_stmt(s) for s in body], [])
            # L_fun
            case Return(e):
                return Return(self.resolve_exp(e))
            # L_if
            case If(e, stmts1, stmts2):
                return If(self.resolve_exp(e), [self.resolve_stmt(s) for s in stmts1], [self.resolve_stmt(s) for s in stmts2])
            # L_var
            case Expr(Call(Name('print'), [e])):
                return Expr(Call(Name('print'), [self.resolve_exp(e)]))
            case Expr(e):
                return Expr(self.resolve_exp(e))
            case Assign([Name(var)], e):
                return Assign([Name(var)], self.resolve_exp(e))
            case _:
                return s

    def resolve(self, p: Module) -> Module:
        match p:
            case Module(body):
                new_body = []
                for elm in body:
                    match elm:
                        case FunctionDef(name, params, bod, dl, returns, comment):
                            fun_body = []
                            for s in bod:
                                fun_body.append(self.resolve_stmt(s))
                            fun = FunctionDef(name, params, fun_body, dl, returns, comment)
                            new_body.append(fun)
                return Module(new_body)

    ############################################################################
    # check bounds
    ############################################################################

    ############################################################################
    # expose allocation
    ############################################################################

    def expose_exp(self, e: expr) -> expr:
        match e:
            # array_len, array_load, array_store covered in super().expose_exp(e)
            case ast.List(es, Load()):
                beginbody: list[stmt] = []
                tmps = []
                for exp in es:
                    fresh_tmp = generate_name('expose')
                    tmps.append(fresh_tmp)
                    beginbody.append(Assign([Name(fresh_tmp)], self.expose_exp(exp)))
                bytesreq = (len(tmps) + 1) * 8
                beginbody.append(If(Compare(
                    BinOp(GlobalValue(Label('free_ptr')), Add(), Constant(bytesreq)),
                    [Lt()],
                    [GlobalValue(Label('fromspace_end'))]),
                    [Expr(Constant(0))],
                    [Collect(bytesreq)]))
                fresh_tmp = generate_name('expose')
                fresh_tmp_name = Name(fresh_tmp)
                beginbody.append(Assign([fresh_tmp_name], AllocateArray(Constant(len(tmps)), e.has_type)))
                for i in range(len(tmps)):
                    beginbody.append(Assign([Subscript(Name(fresh_tmp), Constant(i), Store())], Name(tmps[i])))
                return Begin(beginbody, Name(fresh_tmp))
            case _:
                return super().expose_exp(e)

    ############################################################################
    # remove complex operands
    ############################################################################

    def rco_exp(self, e: expr, need_atomic: bool) -> tuple[expr, Temporaries]:
        match e:
            case AllocateArray(n, typ):
                atm, tmp = self.rco_exp(n, False)
                if need_atomic:
                    fresh_tmp = generate_name('allocarray')
                    return (Name(fresh_tmp), tmp + [(Name(fresh_tmp), AllocateArray(atm, typ))])
                return (AllocateArray(atm, typ), tmp)
            case _:
                return super().rco_exp(e, need_atomic)

    ############################################################################
    # remove complex operands
    ############################################################################

    ############################################################################
    # select instructions
    ############################################################################

    def select_stmt(self, s: stmt, name: str) -> list[instr]:
        match s:
            case Assign([Name(var)], Call(Name('array_load'), [exp1, exp2])):
                arg1 = self.select_arg(exp1)
                arg2 = self.select_arg(exp2)
                return [Instr('movq', [arg1, Reg('r11')]),
                        Instr('movq', [arg2, Reg('rax')]),
                        Instr('addq', [Immediate(1), Reg('rax')]),
                        # Addressing mode (%r11,%rax,8) not implemented, so calculate manually
                        Instr('salq', [Immediate(3), Reg('rax')]),
                        Instr('addq', [Reg('rax'), Reg('r11')]),
                        Instr('movq', [Deref('r11', 0), Variable(var)])]
            case Expr(Call(Name('array_store'), [exp1, exp2, exp3])):
                arg1 = self.select_arg(exp1)
                arg2 = self.select_arg(exp2)
                arg3 = self.select_arg(exp3)
                return [Instr('movq', [arg1, Reg('r11')]),
                        Instr('movq', [arg2, Reg('rax')]),
                        Instr('addq', [Immediate(1), Reg('rax')]),
                        # Addressing mode (%r11,%rax,8) not implemented, so calculate manually
                        Instr('salq', [Immediate(3), Reg('rax')]),
                        Instr('addq', [Reg('rax'), Reg('r11')]),
                        Instr('movq', [arg3, Deref('r11', 0)])]
            case Expr(Call(Name(func), args)) if func in ['array_load', 'array_len']:
                return []  # no side effects!
            case Assign([Name(var)], Call(Name('array_len'), [exp])):
                arg = self.select_arg(exp)
                return [Instr('movq', [arg, Reg('rax')]),
                        Instr('movq', [Deref('rax', 0), Reg('rax')]),
                        Instr('shlq', [Immediate(2), Reg('rax')]),
                        Instr('shrq', [Immediate(4), Reg('rax')]),  # shift (fill zeros!)
                        # Instr('andq', [Immediate(0x0FFFFFFFFFFFFFFF), Reg('rax')]), # doesn't work. immediate must be < 2^32
                        Instr('movq', [Reg('rax'), Variable(var)])]
            case Assign([Name(var)], AllocateArray(Constant(lgth), ListType(ts))):
                tag = (1 << 62) | (lgth << 2) | ((type(ts) in (TupleType, ListType)) << 1) | 1
                return [
                    Instr('movq', [Global(Label('free_ptr')), Reg('r11')]),
                    Instr('addq', [Immediate(8 * (lgth + 1)), Global(Label('free_ptr'))]),
                    Instr('movq', [Immediate(tag), Reg('rax')]),
                    Instr('movq', [Reg('rax'), Deref('r11', 0)]),
                    Instr('movq', [Reg('r11'), Variable(var)])]
            case Assign([Name(var)], AllocateArray(lgth, ListType(ts))):
                tag = (1 << 62) | ((type(ts) in (TupleType, ListType)) << 1) | 1
                return [
                    Instr('movq', [Global(Label('free_ptr')), Reg('r11')]),
                    Instr('movq', [self.select_arg(lgth), Reg('rax')]),
                    Instr('addq', [Immediate(1), Reg('rax')]),
                    Instr('salq', [Immediate(3), Reg('rax')]),
                    Instr('addq', [Reg('rax'), Global(Label('free_ptr'))]),
                    Instr('movq', [self.select_arg(lgth), Reg('rax')]),
                    Instr('shlq', [Immediate(2), Reg('rax')]),
                    Instr('movq', [Reg('rax'), Deref('r11', 0)]),
                    Instr('movq', [Immediate(tag), Reg('rax')]),
                    Instr('addq', [Reg('rax'), Deref('r11', 0)]),
                    Instr('movq', [Reg('r11'), Variable(var)])]
            case Assign([Name(var)], Allocate(lgth, TupleType(ts))):
                pointer_mask = 0
                for i in range(0, len(ts)):
                    if isinstance(ts[i], TupleType) or isinstance(ts[i], ListType):
                        pointer_mask += 1 << i
                tag = (lgth << 1) + (pointer_mask << 7) + 1
                varobj = Variable(var)
                return [Instr("movq", [Global(Label("free_ptr")), Reg("r11")]),
                        Instr("addq", [Immediate(8 * (lgth + 1)), Global(Label("free_ptr"))]),
                        Instr("movq", [Immediate(tag), Deref("r11", 0)]), Instr("movq", [Reg("r11"), varobj])]
            case _:
                return super().select_stmt(s, name)

    ############################################################################
    # Allocate Registers
    ############################################################################

    # ListType was added in Compiler.allocate_registers()!


@dataclass
class CompilerLexam(CompilerLexam3):
    """
    Compiler with the basic tasks:
    1. Division / Multiplication / Modulo
    2. While - statement
    3. Arrays
    """
    pass
