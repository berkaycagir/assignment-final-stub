import ast
from interp_Cif import InterpCif
from utils import *


class InterpCtup(InterpCif):
    def interp_exp(self, e, env):
        match e:
            case ast.Tuple(es, ast.Load()):
                return tuple([self.interp_exp(e, env) for e in es])
            case ast.Subscript(tup, index, ast.Load()):
                t = self.interp_exp(tup, env)
                n = self.interp_exp(index, env)
                if n < 0:
                    raise IndexError("less than zero")
                return t[n]
            case Allocate(length, typ):
                array = [None] * length
                return array
            case Begin(ss, e):
                self.interp_stmts(ss, env)
                return self.interp_exp(e, env)
            case GlobalValue(name):
                return 0  # bogus
            case ast.Call(ast.Name("len"), [tup]):
                t = self.interp_exp(tup, env)
                return len(t)
            case _:
                return super().interp_exp(e, env)

    def interp_stmts(self, ss, env):
        if len(ss) == 0:
            return
        match ss[0]:
            case Collect(size):
                return self.interp_stmts(ss[1:], env)
            case ast.Assign([ast.Subscript(tup, index)], value):
                tup = self.interp_exp(tup, env)
                index = self.interp_exp(index, env)
                if index < 0:
                    raise IndexError("less than zero")
                tup[index] = self.interp_exp(value, env)
                return self.interp_stmts(ss[1:], env)
            case _:
                return super().interp_stmts(ss, env)
