import ast
from interp_Cfun import InterpCfun
from utils import *


class InterpCexam(InterpCfun):
    def interp_exp(self, e, env):
        match e:
            case AllocateArray(length, typ):  # FIXED
                length = self.interp_exp(length, env)
                return [None] * length
            case ast.List(es, ast.Load()):
                return [self.interp_exp(e, env) for e in es]
            case ast.BinOp(left, ast.Mult(), right):
                l = self.interp_exp(left, env)
                r = self.interp_exp(right, env)
                return l * r
            case ast.BinOp(left, ast.FloorDiv(), right):
                l = self.interp_exp(left, env)
                r = self.interp_exp(right, env)
                aq = abs(l) // abs(r)
                return aq if l * r >= 0 else -aq
            case ast.BinOp(left, ast.Mod(), right):
                l = self.interp_exp(left, env)
                r = self.interp_exp(right, env)
                ar = abs(l) % abs(r)
                return ar if l >= 0 else -ar
            case ast.BinOp(left, ast.LShift(), right):
                l = self.interp_exp(left, env)
                r = self.interp_exp(right,env)
                return l << r
            case ast.BinOp(left, ast.RShift(), right):
                l = self.interp_exp(left, env)
                r = self.interp_exp(right,env)
                return l >> r
            case ast.BinOp(left, ast.BitOr(), right):
                l = self.interp_exp(left, env)
                r = self.interp_exp(right, env)
                return l | r
            case ast.BinOp(left, ast.BitXor(), right):
                l = self.interp_exp(left, env)
                r = self.interp_exp(right,env)
                return l ^ r
            case ast.BinOp(left, ast.BitAnd(), right):
                l = self.interp_exp(left, env)
                r = self.interp_exp(right,env)
                return l & r
            case ast.Call(ast.Name("array_len"), [tup]):
                t = self.interp_exp(tup, env)
                return len(t)
            case ast.Call(ast.Name("array_load"), [tup, index]):
                t = self.interp_exp(tup, env)
                i = self.interp_exp(index, env)
                return t[i]
            case ast.Call(ast.Name("array_store"), [tup, index, value]):
                t = self.interp_exp(tup, env)
                i = self.interp_exp(index, env)
                v = self.interp_exp(value, env)
                t[i] = v
                return None
            case _:
                return super().interp_exp(e, env)

    def interp_stmts(self, ss, env):
        if len(ss) == 0:
            return
        match ss[0]:
            case ast.Assign([ast.Subscript(lst, index)], value):
                lst = self.interp_exp(lst, env)
                index = self.interp_exp(index, env)
                if index < 0:
                    raise IndexError("less than zero")
                lst[index] = self.interp_exp(value, env)
                return self.interp_stmts(ss[1:], env)
            case _:
                return super().interp_stmts(ss, env)
