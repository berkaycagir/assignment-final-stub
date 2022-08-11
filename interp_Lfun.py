import ast
import utils
from interp_Ltup import InterpLtup


class Function:
    __match_args__ = ("name", "params", "body", "env")

    def __init__(self, name, params, body, env):
        self.name = name
        self.params = params
        self.body = body
        self.env = env

    def __repr__(self):
        return "Function(" + self.name + ", ...)"


class InterpLfun(InterpLtup):
    def apply_fun(self, fun, args, e):
        match fun:
            case Function(name, xs, body, env):
                new_env = {x: v for (x, v) in env.items()}
                for (x, arg) in zip(xs, args):
                    new_env[x] = arg
                return self.interp_stmts(body, new_env)
            case _:
                raise Exception("apply_fun: unexpected: " + repr(fun))

    def interp_exp(self, e, env):
        match e:
            case ast.Call(ast.Name(f), args) if (f == "input_int") or (f == "len") or (
                f == "print"
            ):
                return super().interp_exp(e, env)
            case ast.Call(func, args):
                f = self.interp_exp(func, env)
                vs = [self.interp_exp(arg, env) for arg in args]
                return self.apply_fun(f, vs, e)
            case utils.FunRef(id, arity):
                return env[id]
            case _:
                return super().interp_exp(e, env)

    def interp_stmts(self, ss, env):
        if len(ss) == 0:
            return
        match ss[0]:
            case ast.Return(value):
                return self.interp_exp(value, env)
            case ast.While(test, body, []):
                while self.interp_exp(test, env):
                    r = self.interp_stmts(body, env)
                    if r is not None:
                        return r
                return self.interp_stmts(ss[1:], env)
            case ast.FunctionDef(name, params, bod, dl, returns, comment):
                if isinstance(params, ast.arguments):
                    ps = [p.arg for p in params.args]
                else:
                    ps = [x for (x, t) in params]  # type: ignore
                env[name] = Function(name, ps, bod, env)
                return self.interp_stmts(ss[1:], env)
            case _:
                return super().interp_stmts(ss, env)

    def interp(self, p):
        match p:
            case ast.Module(ss):
                env = {}
                self.interp_stmts(ss, env)
                # trace('interp global env: ' + repr(env))
                if "main" in env.keys():
                    self.apply_fun(env["main"], [], None)
            case _:
                raise Exception(
                    "interp: unexpected "
                    + repr(p)
                    + (
                        ("\nAST info 1: " + utils.ast_loc(p))
                        if isinstance(p, ast.AST)
                        else ""
                    )
                )
