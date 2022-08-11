from ast import *
from cProfile import label
from typing import Optional
from register_allocation import build_interference, color_graph
from register_allocation import color_to_register, all_argument_passing_registers, callee_saved_registers
from utils import *
from x86_ast import *
from dataclasses import dataclass, field
from pprint import pprint

Binding = tuple[Name, expr]
Temporaries = list[Binding]

@dataclass
class Compiler:
    stack_space: int = 0
    root_stack_space: int = 0
    used_callee : list[location] = field(default_factory=list)

    ############################################################################
    # Shrink
    ############################################################################

    def shrink_exp(self, e: expr) -> expr:
        match e:
            # L_fun
            case Call(exp, exprs):
                return Call(self.shrink_exp(exp), [self.shrink_exp(exp) for exp in exprs])
            # L_tup
            case Tuple(exprs, Load()):
                return Tuple([self.shrink_exp(e) for e in exprs], Load())
            case Subscript(exp, Constant(int), Load()):
                return Subscript(self.shrink_exp(exp), Constant(int), Load())
            case Call(Name('len'), [exp]):
                return Call(Name('len'), [self.shrink_exp(exp)])
            # L_if
            case BoolOp(And(), [exp1, exp2]):
                return IfExp(self.shrink_exp(exp1), self.shrink_exp(exp2), Constant(False))
            case BoolOp(Or(), [exp1, exp2]):
                return IfExp(self.shrink_exp(exp1), Constant(True), self.shrink_exp(exp2))
            case IfExp(exp1, exp2, exp3):
                return IfExp(self.shrink_exp(exp1), self.shrink_exp(exp2), self.shrink_exp(exp3))
            case Compare(left, [cmp], [right]):
                return Compare(self.shrink_exp(left), [cmp], [self.shrink_exp(right)])
            # L_var
            case BinOp(left, op, right):
                return BinOp(self.shrink_exp(left), op, self.shrink_exp(right))
            case UnaryOp(op, e):
                return UnaryOp(op, self.shrink_exp(e))
            case _:
                return e

    def shrink_stmt(self, s: stmt) -> stmt:
        match s:
            # L_fun
            case Return(e):
                return Return(self.shrink_exp(e))
            # L_if
            case If(e, stmts1, stmts2):
                return If(self.shrink_exp(e), [self.shrink_stmt(s) for s in stmts1], [self.shrink_stmt(s) for s in stmts2])
            # L_var
            case Expr(Call(Name('print'), [e])):
                return Expr(Call(Name("print"), [self.shrink_exp(e)]))
            case Expr(e):
                return Expr(self.shrink_exp(e))
            case Assign([Name(var)], e):
                return Assign([Name(var)], self.shrink_exp(e))
            case _:
                return s

    def shrink_def(self, d: FunctionDef):
        match d:
            case FunctionDef(name, params, bod, dl, returns, comment):
                new_bod = []
                for s in bod:
                    new_bod.append(self.shrink_stmt(s))
                return FunctionDef(name, params, new_bod, dl, returns, comment)
            case _:
                raise Exception("Wrong call to shrink_def" + "\nAST info 1: " + ast_loc(d))

    def shrink(self, p: Module) -> Module:
        match p:
            case Module(body):
                new_body = []
                main_body = []
                for elm in body:
                    match elm:
                        case FunctionDef(name, params, bod, dl, returns, comment):
                            new_body.append(self.shrink_def(elm))
                        case _:
                            main_body.append(self.shrink_stmt(elm))
                main_body.append(Return(Constant(0)))
                main_def = FunctionDef('main', [], main_body, None, IntType(), None)
                new_body.append(main_def)
                return Module(new_body)

    ############################################################################
    # Reveal Functions
    ############################################################################

    def reveal_exp(self, e: expr, funs) -> expr:
        match e:
            # L_fun
            case Call(e, args): 
                return Call(self.reveal_exp(e, funs), [self.reveal_exp(e, funs) for e in args])
            case Name(var) if var in funs:
                return FunRef(var, funs[var])
            # L_tup
            case Tuple(exprs, Load()):
                return Tuple([self.reveal_exp(e, funs) for e in exprs], Load())
            case Subscript(exp, Constant(int), Load()):
                return Subscript(self.reveal_exp(exp, funs), Constant(int), Load())
            case Call(Name('len'), [exp]):
                return Call(Name('len'), [self.reveal_exp(exp, funs)])
            # L_if
            case IfExp(exp1, exp2, exp3):
                return IfExp(self.reveal_exp(exp1, funs), self.reveal_exp(exp2, funs), self.reveal_exp(exp3, funs))
            case Compare(left, [cmp], [right]):
                return Compare(self.reveal_exp(left, funs), [cmp], [self.reveal_exp(right, funs)])
            # L_var
            case BinOp(left, op, right):
                return BinOp(self.reveal_exp(left, funs), op, self.reveal_exp(right, funs))
            case UnaryOp(op, e):
                return UnaryOp(op, self.reveal_exp(e, funs))
            case _:
                return e

    def reveal_stmt(self, s: stmt, funs) -> stmt:
        match s:
            # L_fun
            case Return(e):
                return Return(self.reveal_exp(e, funs))
            # L_if
            case If(e, stmts1, stmts2):
                return If(self.reveal_exp(e, funs), [self.reveal_stmt(s, funs) for s in stmts1], [self.reveal_stmt(s, funs) for s in stmts2])
            # L_var
            case Expr(Call(Name('print'), [e])):
                return Expr(Call(Name("print"), [self.reveal_exp(e, funs)]))
            case Expr(e):
                return Expr(self.reveal_exp(e, funs))
            case Assign([Name(var)], e):
                return Assign([Name(var)], self.reveal_exp(e, funs))
            case _:
                return s

    def reveal_functions(self, p: Module) -> Module:
        match p:
            case Module(body):
                global_funcs: dict[str, int] = {}
                for elm in body:
                    match elm:
                        case FunctionDef(name, params, bod, dl, returns, comment):
                            global_funcs[name] = len(params)
                new_body = []
                for elm in body:
                    match elm:
                        case FunctionDef(name, params, bod, dl, returns, comment):
                            fun_body = []
                            for s in bod:
                                fun_body.append(self.reveal_stmt(s, global_funcs))
                            new_func = FunctionDef(name, params, fun_body, dl, returns, comment)
                            new_body.append(new_func)
                return Module(new_body)

    ############################################################################
    # Limit functions
    ############################################################################

    def limit_exp(self, e: expr, repl: dict[str, expr]) -> expr:
        match e:
            # L_fun
            case Call(var, args):
                if len(args) > 6:
                    limit_args = [self.limit_exp(a, repl) for a in args]
                    return Call(var, limit_args[:5] + [Tuple([limit_args[i] for i in range(5, len(args))], Load())])
                else:
                    limit_args = [self.limit_exp(a, repl) for a in args]
                    return Call(var, limit_args)
            case Name(var) if var in repl:
                return repl[var]
            # L_tup
            case Tuple(exprs, Load()):
                return Tuple([self.limit_exp(e, repl) for e in exprs], Load())
            case Subscript(exp, Constant(n), Load()):
                return Subscript(self.limit_exp(exp, repl), Constant(n), Load())
            # L_if
            case IfExp(exp1, exp2, exp3):
                return IfExp(self.limit_exp(exp1, repl), self.limit_exp(exp2, repl), self.limit_exp(exp3, repl))
            case Compare(left, [cmp], [right]):
                return Compare(self.limit_exp(left, repl), [cmp], [self.limit_exp(right, repl)])
            # L_var
            case BinOp(left, op, right):
                return BinOp(self.limit_exp(left, repl), op, self.limit_exp(right, repl))
            case UnaryOp(op, e):
                return UnaryOp(op, self.limit_exp(e, repl))
            case _:
                return e

    def limit_stmt(self, s: stmt, repl: dict[str, expr]) -> stmt:
        match s:
            # L_fun
            case Return(e):
                return Return(self.limit_exp(e, repl))
            # L_if
            case If(e, stmts1, stmts2):
                return If(self.limit_exp(e, repl), [self.limit_stmt(s, repl) for s in stmts1], [self.limit_stmt(s, repl) for s in stmts2])
            # L_var
            case Expr(Call(Name('print'), [e])):
                return Expr(Call(Name("print"), [self.limit_exp(e, repl)]))
            case Expr(e):
                return Expr(self.limit_exp(e, repl))
            case Assign([Name(var)], e):
                return Assign([Name(var)], self.limit_exp(e, repl))
            case _:
                return s

    def limit_functions(self, p: Module) -> Module:
        match p:
            case Module(body):
                new_body = []
                for elm in body:
                    match elm:
                        case FunctionDef(name, params, bod, dl, returns, comment):
                            repl = {}
                            if len(params) > 6:
                                for i in range(5):
                                    repl[params[i][0]] = Name(params[i][0])
                                for i in range(5, len(params)):
                                    repl[params[i][0]] = Subscript(Name("tup"), Constant(i - 5), Load())
                                params_tuple_type = TupleType([params[i][1] for i in range(5, len(params))])
                                params = params[:5] + [("tup", params_tuple_type)]
                            fun_body = [self.limit_stmt(s, repl) for s in bod]
                            new_body.append(FunctionDef(name, params, fun_body, dl, returns, comment))
                return Module(new_body)

    ############################################################################
    # Expose Allocation
    ############################################################################

    def expose_exp(self, e: expr) -> expr:
        match e:
            # L_fun
            case Call(var, args):
                return Call(var, [self.expose_exp(exp) for exp in args])
            # L_tup
            case Tuple(es, Load()):
                beginbody: list[stmt] = []
                tmps = []
                for exp in es:
                    fresh_tmp = generate_name('expose')
                    tmps.append(fresh_tmp)
                    beginbody.append(Assign([Name(fresh_tmp)], self.expose_exp(exp)))
                bytesreq = (len(tmps) + 1) * 8
                beginbody.append(If(Compare(
                                     BinOp(GlobalValue(label_name("free_ptr")), Add(), Constant(bytesreq)),
                                     [Lt()],
                                     [GlobalValue(label_name("fromspace_end"))]),
                                 [Expr(Constant(0))],
                                 [Collect(bytesreq)]))
                fresh_tmp = generate_name('expose')
                fresh_tmp_name = Name(fresh_tmp)
                beginbody.append(Assign([fresh_tmp_name], Allocate(len(tmps), e.has_type)))
                for i in range(len(tmps)):
                    beginbody.append(Assign([Subscript(Name(fresh_tmp), Constant(i), Store())], Name(tmps[i])))
                return Begin(beginbody, Name(fresh_tmp))
            case Subscript(e, Constant(n), Load()):
                return Subscript(self.expose_exp(e), Constant(n), Load())
            # L_if
            case IfExp(exp1, exp2, exp3):
                return IfExp(self.expose_exp(exp1), self.expose_exp(exp2), self.expose_exp(exp3))
            case Compare(left, [cmp], [right]):
                return Compare(self.expose_exp(left), [cmp], [self.expose_exp(right)])
            # L_var
            case BinOp(left, op, right):
                return BinOp(self.expose_exp(left), op, self.expose_exp(right))
            case UnaryOp(op, e):
                return UnaryOp(op, self.expose_exp(e))
            case _:
                return e

    def expose_stmt(self, s: stmt) -> stmt:
        match s:
            # L_fun
            case Return(e):
                return Return(self.expose_exp(e))
            # L_if
            case If(e, stmts1, stmts2):
                return If(self.expose_exp(e), [self.expose_stmt(s) for s in stmts1], [self.expose_stmt(s) for s in stmts2])
            # L_var
            case Expr(Call(Name('print'), [e])):
                return Expr(Call(Name("print"), [self.expose_exp(e)]))
            case Expr(e):
                return Expr(self.expose_exp(e))
            case Assign([Name(var)], e):
                return Assign([Name(var)], self.expose_exp(e))
            case _:
                return s

    def expose_allocation(self, p: Module) -> Module:
        match p:
            case Module(body):
                new_body = []
                for elm in body:
                    match elm:
                        case FunctionDef(name, params, bod, dl, returns, comment):
                            fun_body = []
                            for s in bod:
                                fun_body.append(self.expose_stmt(s))
                            new_body.append(FunctionDef(name, params, fun_body, dl, returns, comment))
                return Module(new_body)

    ############################################################################
    # Remove Complex Operands
    ############################################################################

    def rco_exp(self, e: expr, need_atomic: bool) -> tuple[expr, Temporaries]:
        match e:
            # L_fun
            case FunRef(var, arity):
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    return (Name(fresh_tmp), [(Name(fresh_tmp), e)])
                return e, []
            case Call(exp, args):
                atm1, tmps1 = self.rco_exp(exp, True)
                atm_args = []
                atm_tmps = []
                for arg_i in args:
                    atm, tmps = self.rco_exp(arg_i, True)
                    atm_args.append(atm)
                    atm_tmps += tmps
                ret_exp = Call(atm1, atm_args)
                ret_tmps = tmps1 + atm_tmps
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    ret_tmps.append((Name(fresh_tmp), ret_exp))
                    ret_exp = Name(fresh_tmp)
                return (ret_exp, ret_tmps)
            # L_tup
            case Allocate(n, typ):
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    return (Name(fresh_tmp), [(Name(fresh_tmp), e)])
                return (e, [])
            case GlobalValue(ident):
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    return (Name(fresh_tmp), [(Name(fresh_tmp), e)])
                return (e, [])
            case Begin(body, exp):
                atm, tmps = self.rco_exp(exp, False)
                new_body = []
                for s in body:
                    new_body += self.rco_stmt(s)
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    # The previous code did not handle complex exp.
                    return (Name(fresh_tmp), [(Name(fresh_tmp), Begin(new_body + make_assigns(tmps), atm))])
                return (Begin(new_body + make_assigns(tmps), atm), [])
            case Call(Name('len'), [exp]):
                atm1, tmps1 = self.rco_exp(exp, True)
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    return (Name(fresh_tmp), tmps1 + [(Name(fresh_tmp), Call(Name('len'), [atm1]))])
                return (Call(Name('len'), [atm1]), tmps1)
            case Subscript(exp1, exp2, Load()):
                atm1, tmps1 = self.rco_exp(exp1, True)
                atm2, tmps2 = self.rco_exp(exp2, True)
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    return (Name(fresh_tmp), tmps1 + tmps2 + [(Name(fresh_tmp), Subscript(atm1, atm2, Load()))])
                return (Subscript(atm1, atm2, Load()), tmps1 + tmps2)
            # L_if
            case IfExp(exp1, exp2, exp3):
                atm1, tmps1 = self.rco_exp(exp1, False)
                atm2, tmps2 = self.rco_exp(exp2, False)
                atm3, tmps3 = self.rco_exp(exp3, False)
                exp_then = make_begin(tmps2, atm2)
                exp_else = make_begin(tmps3, atm3)
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    return (Name(fresh_tmp), tmps1 + [(Name(fresh_tmp), IfExp(atm1, exp_then, exp_else))])
                return (IfExp(atm1, exp_then, exp_else), tmps1)
            case Compare(left, [cmp], [right]):
                latm, ltmps = self.rco_exp(left, True)
                ratm, rtmps = self.rco_exp(right, True)
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    return (Name(fresh_tmp), ltmps + rtmps + [(Name(fresh_tmp), Compare(latm, [cmp], [ratm]))])
                return (Compare(latm, [cmp], [ratm]), ltmps + rtmps)
            # L_var
            case Name(var):
                return (Name(var), [])
            case Constant(_):
                return (e, [])
            case Call(Name('input_int'), []):
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    return (Name(fresh_tmp), [(Name(fresh_tmp), e)])
                return (e, [])
            case UnaryOp(op, e1):
                atm, tmps = self.rco_exp(e1, True)
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    return (Name(fresh_tmp), tmps + [(Name(fresh_tmp), UnaryOp(op, atm))])
                return (UnaryOp(op, atm), tmps)
            case BinOp(e1, op, e2):
                atm1, tmps1 = self.rco_exp(e1, True)
                atm2, tmps2 = self.rco_exp(e2, True)
                if need_atomic:
                    fresh_tmp = generate_name('atom')
                    return (Name(fresh_tmp), tmps1 + tmps2 + [(Name(fresh_tmp), BinOp(atm1, op, atm2))])
                return (BinOp(atm1, op, atm2), tmps1 + tmps2)
            case _:
                pprint(e)
                raise Exception("Missed expression in rco_exp" + "\nAST info 1: " + ast_loc(e))


    def rco_stmt(self, s: stmt) -> list[stmt]:
        match s:
            # L_fun
            case Return(e):
                atm, tmps = self.rco_exp(e, False)
                return make_assigns(tmps) + [Return(atm)]
            # L_tup
            case Assign([Subscript(exp1, exp2, Store())], exp3):
                atm1, tmps1 = self.rco_exp(exp1, True)
                atm2, tmps2 = self.rco_exp(exp2, True)
                atm3, tmps3 = self.rco_exp(exp3, True)
                return (make_assigns(tmps1) + make_assigns(tmps2)
                        + make_assigns(tmps3) + [Assign([Subscript(atm1, atm2, Store())], atm3)])
            case Collect(n):
                return [s]
            # L_if
            case If(e, stmts1, stmts2):
                atm, tmps = self.rco_exp(e, False)
                astmts1 = []
                for s in stmts1:
                    astmts1 += self.rco_stmt(s)
                astmts2 = []
                for s in stmts2:
                    astmts2 += self.rco_stmt(s)
                return make_assigns(tmps) + [If(atm, astmts1, astmts2)]
            # L_var
            case Expr(Call(Name('print'), [e])):
                atm, tmps = self.rco_exp(e, True)
                return make_assigns(tmps) + [Expr(Call(Name('print'), [atm]))]
            case Expr(e):
                atm, tmps = self.rco_exp(e, False)
                return make_assigns(tmps) + [Expr(atm)]
            case Assign([Name(var)], e):
                atm, tmps = self.rco_exp(e, False)
                return make_assigns(tmps) + [Assign([Name(var)], atm)]
            case _:
                pprint(s)
                raise Exception("Missed statement in rco_stmt" + "\nAST info 1: " + ast_loc(s))

    def remove_complex_operands(self, p: Module) -> Module:
        match p:
            case Module(body):
                new_body = []
                for elm in body:
                    match elm:
                        case FunctionDef(name, params, bod, dl, returns, comment):
                            fun_body = []
                            for s in bod:
                                fun_body += self.rco_stmt(s)
                            new_body.append(FunctionDef(name, params, fun_body, dl, returns, comment))
                return Module(new_body)

    ############################################################################
    # Explicate Control
    ############################################################################

    # Extract side effects from expression statements (ignore results)
    def explicate_effect(self, e, cont, basic_blocks) -> list[stmt]:
        match e:
            # L_tup: unassigned allocations are ignored (catch-all)
            # Begin
            case Begin(body, result):
                result = self.explicate_effect(result, cont, basic_blocks)
                for s in reversed(body):
                    result = self.explicate_stmt(s, result, basic_blocks)
                return result
            # L_if
            case IfExp(test, body, orelse):
                goto_cnt = create_block(cont, basic_blocks)
                expl_body = self.explicate_effect(body, [goto_cnt], basic_blocks)
                expl_orelse = self.explicate_effect(orelse, [goto_cnt], basic_blocks)
                return self.explicate_pred(test, expl_body, expl_orelse, basic_blocks)
            case Call(func, args):
                return [Expr(e)] + cont
#            case Let(var, rhs, body):
#                expl_body = self.explicate_effect(body, cont, basic_blocks)
#                return self.explicate_assign(rhs, var, expl_body, basic_blocks)
            case _:
                # atm's don't have side-effects!
                return cont

    # Generate code for right-hand side of assignment
    def explicate_assign(self, rhs, lhs, cont, basic_blocks) -> list[stmt]:
        match rhs:
            # L_fun: covered by catch-all
            # L_tup: covered by the catch-all
            # Begin
            case Begin (body, result):
                ss = self.explicate_assign(result, lhs, cont, basic_blocks)
                for s in reversed(body):
                    ss = self.explicate_stmt(s, ss, basic_blocks)
                return ss
            # L_if
            case IfExp(test, body, orelse):
                goto_cnt = create_block(cont, basic_blocks)
                return self.explicate_pred(test,
                                           self.explicate_assign(body, lhs, [goto_cnt], basic_blocks),
                                           self.explicate_assign(orelse, lhs, [goto_cnt], basic_blocks),
                                           basic_blocks)
#            case Let(var, rhs, body):
#                return self.explicate_assign(rhs, var, self.explicate_assign(body, lhs, cont, basic_blocks), basic_blocks)
            case _:
                return [Assign([lhs], rhs)] + cont

    # Generate code for if expression or statement
    def explicate_pred(self, cnd, thn, els, basic_blocks) -> list[stmt]:
        match cnd:
            # L_fun
            case Call(name, args):
                result = generate_name("result")
                pred = self.explicate_pred(Name(result), thn, els, basic_blocks)
                return self.explicate_assign(cnd, Name(result), pred, basic_blocks)
            # L_tup
            case Subscript(tup, index, Load()):
                fresh_tmp = generate_name('expl')
                return self.explicate_assign(cnd, Name(fresh_tmp),
                                             self.explicate_pred(Name(fresh_tmp),
                                                                 thn,
                                                                 els,
                                                                 basic_blocks),
                                             basic_blocks)
            # Begin
            case Begin(body, result):
                ss = self.explicate_pred(result, thn, els, basic_blocks)
                for s in reversed(body):
                    ss = self.explicate_stmt(s, ss, basic_blocks)
                return ss
            # L_if
            case Compare(left, [op], [right]):
                goto_thn = create_block(thn, basic_blocks)
                goto_els = create_block(els, basic_blocks)
                return [If(cnd, [goto_thn], [goto_els])]
            case Constant(True):
                return thn
            case Constant(False):
                return els
            case UnaryOp(Not(), operand):
                return self.explicate_pred(operand, els, thn, basic_blocks)
            case IfExp(test, body, orelse):
                # Decrease duplication of code
                goto_thn = create_block(thn, basic_blocks)
                goto_els = create_block(els, basic_blocks)
                ep_body = self.explicate_pred(body, [goto_thn], [goto_els], basic_blocks)
                ep_orelse = self.explicate_pred(orelse, [goto_thn], [goto_els], basic_blocks)
                return self.explicate_pred(test, ep_body, ep_orelse, basic_blocks)
#            case Let(var, rhs, body):
#                new_body = self.explicate_pred(body, thn, els, basic_blocks)
#                return self.explicate_assign(rhs, var, new_body, basic_blocks)
            case _:
                return [If(Compare(cnd, [Eq()], [Constant(False)]),
                           [create_block(els, basic_blocks)],
                           [create_block(thn, basic_blocks)])]

    def is_primitive(self, e) -> bool:
        match e:
            case Name(x):
                return x in ['input_int', 'print', 'len']
            case _:
                return False

    def explicate_tail(self, e, basic_blocks) -> list[stmt]:
        match e:
            case Begin(stmts, result):
                expl_stmts = self.explicate_tail(result, basic_blocks)
                for s in reversed(stmts):
                    expl_stmts = self.explicate_stmt(s, expl_stmts, basic_blocks)
                return expl_stmts
            case IfExp(test, body, orelse):
                expl_body = self.explicate_tail(body, basic_blocks)
                expl_orelse = self.explicate_tail(orelse, basic_blocks)
                return self.explicate_pred(test, expl_body, expl_orelse, basic_blocks)
#            case Let(var, rhs, body):
#                new_body = self.explicate_tail(body, basic_blocks)
#                return self.explicate_assign(rhs, var, new_body, basic_blocks)
            case Call(var, args) if not self.is_primitive(var):
                return [TailCall(var, args)]
            case _:
                tmp_var = Name(generate_name('expl'))
                return self.explicate_assign(e, tmp_var, [Return(tmp_var)], basic_blocks)

    def explicate_stmt(self, s, cont, basic_blocks) -> list[stmt]:
        match s:
            # L_fun
            case Return(e):
                return self.explicate_tail(e, basic_blocks)
            # L_tup
            case Collect(n):
                return [s] + cont
            # L_if
            case Assign([lhs], rhs):
                return self.explicate_assign(rhs, lhs, cont, basic_blocks)
            case Expr(value):
                return self.explicate_effect(value, cont, basic_blocks)
            case If(test, body, orelse):
                goto_cnt = create_block(cont, basic_blocks)
                explicate_body = [goto_cnt]
                for s in reversed(body):
                    explicate_body = self.explicate_stmt(s, explicate_body, basic_blocks)
                explicate_orelse = [goto_cnt]
                for s in reversed(orelse):
                    explicate_orelse = self.explicate_stmt(s, explicate_orelse, basic_blocks)
                return self.explicate_pred(test, explicate_body, explicate_orelse, basic_blocks)
            case _:
                pprint(s)
                raise Exception("Missed statement in explicate_stmt" + (("\nAST info 1: " + ast_loc(s)) if isinstance(s, ast.AST) else ""))

    def explicate_def(self, df) -> FunctionDef:
        match df:
            case FunctionDef(name, params, body, dl, returns, comment):
                new_body = []
                basic_blocks = {}
                for s in reversed(body):
                    new_body = self.explicate_stmt(s, new_body, basic_blocks)
                basic_blocks[label_name(name + 'start')] = new_body
                return FunctionDef(name, params, basic_blocks, dl, returns, comment)
            case _:
                raise Exception("Statement outside of a function definition!" + ("\nAST info 1: " + ast_loc(df)) if isinstance(df, ast.AST) else "")

    def explicate_control(self, p):
        match p:
            case Module(body):
                defs = []
                for df in body:
                    defs.append(self.explicate_def(df))
                return CProgramDefs(defs)

    ############################################################################
    # Select Instructions
    ############################################################################

    def select_arg(self, e: expr) -> arg:
        match e:
            # L_if
            case Constant(True):
                return Immediate(1)
            case Constant(False):
                return Immediate(0)
            # L_var
            case Constant(n):
                return Immediate(n)
            case Name(var):
                return Variable(var)
            case _:
                pprint(e)
                raise Exception("Missing case in select_arg!" + ("\nAST info 1: " + ast_loc(e)) if isinstance(e, ast.AST) else "")

    def select_stmt(self, s: stmt, name: str) -> list[instr]:
        match s:
            case Expr(Call(Name("print"), [atm])):
                arg = self.select_arg(atm)
                return [Instr("movq", [arg, Reg("rdi")]), Callq(label_name("print_int"), 1)]
            case Expr(Call(Name("input_int"), [])):
                return [Callq(label_name("read_int"), 0)]
            # L_fun
            case Assign([Name(var)], FunRef(fun, arity)):
                return [Instr("leaq", [Global(label_name(fun)), Variable(var)])]
            case Assign([Name(var)], Call(Name(func), args)) if func != "input_int" and func != "len":
                output = []
                for i in range(len(args)):
                    output.append(Instr("movq", [self.select_arg(args[i]), all_argument_passing_registers[i]]))
                output.append(IndirectCallq(Variable(func), len(args)))
                output.append(Instr("movq", [Reg("rax"), Variable(var)]))
                return output
            case TailCall(Name(var), args):
                output = []
                for i in range(len(args)):
                    output.append(Instr("movq", [self.select_arg(args[i]), all_argument_passing_registers[i]]))
                output.append(TailJump(Variable(var), len(args)))
                return output
            case Return(atm):
                arg = self.select_arg(atm)
                return [Instr("movq", [arg, Reg("rax")]), Jump(label_name(name + "conclusion"))]
            case Expr(Call(Name(func), args)) if func != "input_int" and func != "len" and func != "print":
                output = []
                for i in range(len(args)):
                    output.append(Instr("movq", [self.select_arg(args[i]), all_argument_passing_registers[i]]))
                output.append(IndirectCallq(Variable(func), len(args)))
                return output
            # L_tup
            case Assign([Name(var)], Subscript(atm1, atm2, Load())):
                arg1 = self.select_arg(atm1)
                arg2 = self.select_arg(atm2)
                match arg2:
                    case Immediate(n):
                        n = n
                    case _:
                        raise Exception("Index in subscript not an immediate!"
                                        + "\nAST info 1: " + ast_loc(s)
                                        + " & AST info 2: " + ast_loc(atm1)
                                        + " & AST info 3: " + ast_loc(atm2)
                        )
                return [Instr("movq", [arg1, Reg("r11")]), Instr("movq", [Deref("r11", 8 * (n + 1)), Variable(var)])]
            case Assign([Subscript(atm1, atm2, Store())], atm3):
                arg1 = self.select_arg(atm1)
                arg2 = self.select_arg(atm2)
                arg3 = self.select_arg(atm3)
                match arg2:
                    case Immediate(n):
                        n = n
                    case _:
                        raise Exception("Index in subscript not an immediate!"
                                        + "\nAST info 1: " + ast_loc(s)
                                        + " & AST info 2: " + ast_loc(atm1)
                                        + " & AST info 3: " + ast_loc(atm2)
                                        + " & AST info 4: " + ast_loc(atm3)
                        )
                return [Instr("movq", [arg1, Reg("r11")]), Instr("movq", [arg3, Deref("r11", 8 * (n + 1))])]
            case Assign([Name(var)], Allocate(lgth, TupleType(ts))):
                pointer_mask = 0
                for i in range(0, len(ts)):
                    if isinstance(ts[i], TupleType):
                        pointer_mask += 1 << i
                tag = (lgth << 1) + (pointer_mask << 7) + 1
                varobj = Variable(var)
                return [Instr("movq", [Global(label_name("free_ptr")), Reg("r11")]),
                        Instr("addq", [Immediate(8 * (lgth + 1)), Global(label_name("free_ptr"))]),
                        Instr("movq", [Immediate(tag), Deref("r11", 0)]), Instr("movq", [Reg("r11"), varobj])]
            case Collect(n):
                return [Instr("movq", [Reg("r15"), Reg("rdi")]), Instr("movq", [Immediate(n), Reg("rsi")]),
                        Callq(label_name("collect"), 2)]
            case Assign([Name(var)], Call(Name("len"), [atm])):
                arg = self.select_arg(atm)
                return [Instr("movq", [arg, Reg("rax")]),
                        Instr("movq", [Deref("rax", 0), Reg("rax")]),
                        Instr("sarq", [Reg("rax")]),
                        Instr("andq", [Immediate(63), Reg("rax")]),  # 111111
                        Instr("movq", [Reg("rax"), Variable(var)])]
            case Assign([Name(var)], GlobalValue(gvar)):
                return [Instr("movq", [Global(gvar), Variable(var)])]
            # L_if
            case Goto(label):
                return [Jump(label_name(label))]
            case If(Compare(latm, [cmp], [ratm]), [Goto(label1)], [Goto(label2)]):
                larg = self.select_arg(latm)
                rarg = self.select_arg(ratm)
                output: list[instr] = [Instr("cmpq", [rarg, larg])]
                ccode = cmp_to_code(cmp)
                output.append(JumpIf(ccode, label_name(label1)))
                output.append(Jump(label_name(label2)))
                return output
            case Assign([Name(var)], UnaryOp(Not(), atm)):
                arg = self.select_arg(atm)
                match arg:
                    case Variable(var2) if var == var2:
                        return [Instr("xorq", [Immediate(1), Variable(var)])]
                return [Instr("movq", [arg, Variable(var)]), Instr("xorq", [Immediate(1), Variable(var)])]
            case Assign([Name(var)], Compare(latm, [cmp], [ratm])):
                larg = self.select_arg(latm)
                rarg = self.select_arg(ratm)
                output = [Instr("cmpq", [rarg, larg])]
                ccode = cmp_to_code(cmp)
                output.append(Instr(f"set{ccode}", [ByteReg('al')]))
                output.append(Instr("movzbq", [ByteReg("al"), Variable(var)]))
                return output
            # L_var
            case Assign([Name(var)], BinOp(atm1, Sub(), atm2)):
                arg1 = self.select_arg(atm1)
                arg2 = self.select_arg(atm2)
                match (arg1, arg2):
                    case (Variable(var2), _) if var == var2:
                        return [Instr("subq", [arg2, Variable(var)])]
                    case (_, Variable(var2)) if var == var2:
                        return [Instr("negq", [Variable(var2)]), Instr("addq", [arg1, Variable(var2)])]
                return [Instr("movq", [arg1, Variable(var)]), Instr("subq", [arg2, Variable(var)])]
            case Assign([Name(var)], BinOp(atm1, Add(), atm2)):
                arg1 = self.select_arg(atm1)
                arg2 = self.select_arg(atm2)
                match (arg1, arg2):
                    case (Variable(var2), _) if var == var2:
                        return [Instr("addq", [arg2, Variable(var)])]
                    case (_, Variable(var2)) if var == var2:
                        return [Instr("addq", [arg1, Variable(var)])]
                return [Instr("movq", [arg1, Variable(var)]), Instr("addq", [arg2, Variable(var)])]
            case Assign([Name(var)], UnaryOp(USub(), atm)):
                arg = self.select_arg(atm)
                return [Instr("movq", [arg, Variable(var)]), Instr("negq", [Variable(var)])]
            case Assign([Name(var)], Call(Name("input_int"), [])):
                return [Callq(label_name("read_int"), 0), Instr("movq", [Reg("rax"), Variable(var)])]
            case Assign([Name(var)], atm):
                arg = self.select_arg(atm)
                return [Instr("movq", [arg, Variable(var)])]
            case _:
                Exception("Missing case in select_stmt" + "\nAST info 1: " + ast_loc(s))

    def select_def(self, df: FunctionDef) -> FunctionDef:
        match df:
            case FunctionDef(name, params, fbody, dl, returns, comment):
                label_conclusion = label_name(name + 'conclusion')
                label_start = label_name(name + 'start')
                label_of_name = label_name(name)
                output = dict()
                output[label_conclusion] = [Instr("popq", [Reg("rbp")]), Instr("retq", [])] # will be filled later
                for block in fbody:
                    new_block = []
                    for stm in fbody[block]:
                        new_block += self.select_stmt(stm, name)
                    output[block] = new_block
                # Move parameters into local variables
                for i in range(len(params)):
                    param_name = params[i][0]
                    output[label_start].insert(0, Instr("movq", [all_argument_passing_registers[i], Variable(param_name)]))
                output[label_of_name] = [Instr("pushq", [Reg("rbp")]), Instr("movq", [Reg("rsp"), Reg("rbp")])]
                if name == "main":
                    # Temporary prologue for interp_x86, will be overwritten later
                    prologue = []
                    prologue.append(Instr("movq", [Immediate(16384), Reg("rdi")]))
                    prologue.append(Instr("movq", [Immediate(16384), Reg("rsi")]))
                    prologue.append(Callq(label_name("initialize"), 2))
                    prologue.append(Instr("movq", [Global(label_name("rootstack_begin")), Reg("r15")]))
                    prologue.append(Instr("movq", [Immediate(0), Deref("r15", 0)]))
                    prologue.append(Jump(label_name(name + "start")))
                    output[label_of_name] += prologue
                else:
                    output[label_of_name].append(Jump(label_name(name + "start")))

                result = FunctionDef(name, [], output, dl, returns, comment)
                result.var_types = df.var_types
                return result
            case _:
                raise Exception("THIS IS OUTRAGEOUS" + (("\nAST info 1: " + ast_loc(df)) if isinstance(df, ast.AST) else ""))

    def select_instructions(self, p: Module) -> X86ProgramDefs:
        output = []
        for df in p.defs:
            output.append(self.select_def(df))
        return X86ProgramDefs(output)

    ############################################################################
    # Allocate Registers
    ############################################################################

    def allocate_registers(self, p: FunctionDef):
        ifg = build_interference(p.body, p.var_types)
        coloring = color_graph(ifg)
        output = dict()
        color_to_location = color_to_register
        offset = 0 
        offset_root_stack = 0
        used_callee = set()
        rootstack_color_to_location = dict()

        for key, val in coloring.items():
            match key:
                case Variable(var):
                    match p.var_types[var]:
                        # This case has been forgot (and it would be weird to redo everything in compiler_Lexam
                        # just for that)
                        case ListType(ts) :
                            if val in rootstack_color_to_location:
                                location = rootstack_color_to_location[val]
                                output[key] = location
                            else:
                                offset_root_stack -= 8
                                rootstack_color_to_location[key] = Deref("r15", offset_root_stack)
                                output[key] = rootstack_color_to_location[key]
                        case TupleType(ts) :
                            if val in rootstack_color_to_location:
                                location = rootstack_color_to_location[val]
                                output[key] = location
                            else:
                                offset_root_stack -= 8
                                rootstack_color_to_location[key] = Deref("r15", offset_root_stack)
                                output[key] = rootstack_color_to_location[key]
                        case _:
                            if val in color_to_location:
                                location = color_to_location[val]
                                output[key] = location
                                if location in callee_saved_registers:
                                        used_callee.add(location)
                            else:
                                offset -= 8
                                color_to_location[key] = Deref("rbp", offset)
                                output[key] = color_to_location[key]

        callees_stack_space = len(used_callee) * 8
        for key, loc in output.items():
            match loc:
                case Deref("rbp", offset):
                    output[key] = Deref("rbp", offset - callees_stack_space)

        p.stack_space = -offset
        p.root_stack_space = -offset_root_stack
        p.used_callee = list(used_callee)

        return output

    ############################################################################
    # Assign Homes
    ############################################################################

    def assign_homes_arg(self, a: arg, home: dict[Variable, arg]) -> Optional[arg]:
        match a:
            case Variable(_):
                return home.get(a, None)
            case _:
                return a

    def assign_homes_instr(self, i: instr, home: dict[Variable, arg]) -> Optional[instr]:
        match i:
            case Instr(istr, [arg1, arg2]):
                assigned_arg1 = self.assign_homes_arg(arg1, home)
                assigned_arg2 = self.assign_homes_arg(arg2, home)
                if assigned_arg2 is None:
                    return None
                return Instr(istr, [assigned_arg1, assigned_arg2])
            case Instr(istr, [arg1]):
                return Instr(istr, [self.assign_homes_arg(arg1, home)])
            case IndirectCallq(l, i):
                return IndirectCallq(self.assign_homes_arg(l, home), i)
            case IndirectJump(l, i):
                return IndirectJump(self.assign_homes_arg(l, home), i)
            case TailJump(l, i):
                return TailJump(self.assign_homes_arg(l, home), i)
            case _:
                return i

    def assign_homes_instrs(
        self, ss: list[instr], home: dict[Variable, arg]
    ) -> list[instr]:
        output = []
        for istr in ss:
            assigned_istr = self.assign_homes_instr(istr, home)
            if assigned_istr is not None:
                output.append(assigned_istr)
        return output

    def assign_homes_def(self, p: FunctionDef) -> FunctionDef:
        match p:
            case FunctionDef(name, params, fbody, dl, returns, comment):
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
                raise Exception("THIS IS UNFAIR!" + (("\nAST info 1: " + ast_loc(p)) if isinstance(p, ast.AST) else ""))

    def assign_homes(self, p: X86ProgramDefs) -> X86ProgramDefs:
        output = []
        for df in p.defs:
            output.append(self.assign_homes_def(df))
        return X86ProgramDefs(output)

    ############################################################################
    # Patch Instructions
    ############################################################################

    def patch_instr(self, i: instr) -> list[instr]:
        match i:
            case Instr(istr, [Deref(reg, offset), Deref(reg2, offset2)]):
                if reg == reg2 and offset == offset2 and istr == "movq":
                    return []
                return [Instr("movq", [Deref(reg, offset), Reg("rax")]),
                        Instr(istr, [Reg("rax"), Deref(reg2, offset2)])]
            case Instr("cmpq", [arg1, Immediate(n)]):
                return [Instr("movq", [Immediate(n), Reg("rax")]),
                        Instr("cmpq", [arg1, Reg("rax")])]
            case Instr("movzbq", [arg1, Deref(reg, offset)]):
                return [Instr("movzbq", [arg1, Reg("rax")]),
                        Instr("movq", [Reg("rax"), Deref(reg, offset)])]
            case Instr("movq", [arg1, arg2]) if arg1 == arg2:
                    return []
            case Instr("leaq", [arg1, Deref(reg, offset)]):
                # Horrible mistake to replace leaq with movq here especially with the randomness of 
                # register allocations!
                return [Instr("leaq", [arg1, Reg("rax")]),
                        Instr("movq", [Reg("rax"), Deref(reg, offset)])]
            case TailJump(l, i) if l != Reg("rax"):
                return [Instr("movq", [l, Reg("rax")]),
                        TailJump(Reg("rax"), i)]
            case _:
                return [i]

    def patch_instrs(self, ss: list[instr]) -> list[instr]:
        output = []
        for s in ss:
            output += self.patch_instr(s)
        return output

    def patch_def(self, df: FunctionDef) -> FunctionDef:
        match df:
            case FunctionDef(name, params, fbody, dl, returns, comment):
                new_body = dict()
                for block_name, block_items in fbody.items():
                    new_body[block_name] = self.patch_instrs(block_items)
                result = FunctionDef(name, params, new_body, dl, returns, comment)
                result.stack_space = df.stack_space
                result.root_stack_space = df.root_stack_space
                result.used_callee = df.used_callee
                return result

    def patch_instructions(self, p: X86ProgramDefs) -> X86ProgramDefs:
        output = []
        for df in p.defs:
            output.append(self.patch_def(df))
        return X86ProgramDefs(output)

    ############################################################################
    # Prelude & Conclusion
    ############################################################################

    def prelude_and_conclusion_def(self, df: FunctionDef) -> FunctionDef:
        match df:
            case FunctionDef(name, params, fbody, dl, returns, comment):
                callees_stack_space = len(df.used_callee) * 8
                stack_space_mod16 = df.stack_space if (df.stack_space + callees_stack_space) % 16 == 0 else df.stack_space + 8
                # Translate TailJumps
                for (l, ss) in fbody.items():
                    new_ss = []
                    for s in ss:
                        match s:
                            case TailJump(le, i):
                                tailepilogue = [Instr("popq", [Reg("rbp")]), IndirectJump(le)]
                                for reg in df.used_callee:
                                    tailepilogue.insert(0, Instr("popq", [reg]))
                                if stack_space_mod16 > 0:
                                    tailepilogue.insert(0, Instr("addq", [Immediate(stack_space_mod16), Reg("rsp")]))
                                # This has been forgot previously.
                                if df.root_stack_space > 0:
                                    tailepilogue.insert(0, Instr("subq", [Immediate(df.root_stack_space), Reg("r15")]))
                                new_ss += tailepilogue
                            case _:
                                new_ss.append(s)
                    fbody[l] = new_ss
                prologue: list[instr] = [Instr("pushq", [Reg("rbp")]), Instr("movq", [Reg("rsp"), Reg("rbp")])]
                for reg in df.used_callee:
                    prologue.append(Instr("pushq", [reg]))
                if stack_space_mod16 > 0:
                    prologue.append(Instr("subq", [Immediate(stack_space_mod16), Reg("rsp")]))
                if name == "main":
                    prologue.append(Instr("movq", [Immediate(16384), Reg("rdi")]))
                    prologue.append(Instr("movq", [Immediate(16384), Reg("rsi")]))
                    prologue.append(Callq(label_name("initialize"), 2))
                    prologue.append(Instr("movq", [Global(label_name("rootstack_begin")), Reg("r15")]))
                for i in range(0, df.root_stack_space // 8):
                    prologue.append(Instr("movq", [Immediate(0), Deref("r15", 0)]))
                    prologue.append(Instr("addq", [Immediate(8), Reg("r15")]))
                fbody[label_name(name)] = prologue + [Jump(label_name(name + "start"))]
                epilogue: list[instr] = [Instr("popq", [Reg("rbp")]), Instr("retq", [])]
                for reg in df.used_callee:
                    epilogue.insert(0, Instr("popq", [reg]))
                if stack_space_mod16 > 0:
                    epilogue.insert(0, Instr("addq", [Immediate(stack_space_mod16), Reg("rsp")]))
                # This has been forgot previously... (Gives great segmentation faults)
                if df.root_stack_space > 0:
                    epilogue.insert(0, Instr("subq", [Immediate(df.root_stack_space), Reg("r15")]))
                fbody[label_name(name + "conclusion")] = epilogue
                return fbody

    def prelude_and_conclusion(self, p: X86ProgramDefs) -> X86Program:
        output = dict()
        for df in p.defs:
            output = output | self.prelude_and_conclusion_def(df)
        return X86Program(output)
