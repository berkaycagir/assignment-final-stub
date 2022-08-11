import ast
from type_check_Lwhile import TypeCheckLwhile
import utils


class TypeCheckLtup(TypeCheckLwhile):
    def check_type_equal(self, t1, t2, e):
        match t1:
            case utils.TupleType(ts1):
                match t2:
                    case utils.TupleType(ts2):
                        for (ty1, ty2) in zip(ts1, ts2):
                            self.check_type_equal(ty1, ty2, e)
                    case _:
                        raise Exception(
                            "error: "
                            + repr(t1)
                            + " != "
                            + repr(t2)
                            + " in "
                            + repr(e)
                            + (
                                ("\nAST info 1: " + utils.ast_loc(e))
                                if isinstance(e, ast.AST)
                                else ""
                            )
                        )
            case _:
                super().check_type_equal(t1, t2, e)

    def type_check_exp(self, e, env):
        match e:
            case ast.Compare(left, [cmp], [right]) if isinstance(cmp, ast.Is):
                l = self.type_check_exp(left, env)
                r = self.type_check_exp(right, env)
                self.check_type_equal(l, r, e)
                return utils.BoolType()
            case ast.Tuple(es, ast.Load()):
                ts = [self.type_check_exp(e, env) for e in es]
                e.has_type = utils.TupleType(ts)  # type: ignore
                return e.has_type  # type: ignore
            case ast.Subscript(tup, ast.Constant(index), ast.Load()):
                tup_ty = self.type_check_exp(tup, env)
                index_ty = self.type_check_exp(ast.Constant(index), env)
                self.check_type_equal(index_ty, utils.IntType(), index)
                match tup_ty:
                    case utils.TupleType(ts):
                        return ts[index]
                    case _:
                        raise Exception(
                            "subscript expected a tuple, not "
                            + repr(tup_ty)
                            + "\nAST info 1: "
                            + utils.ast_loc(e)
                            + " & AST info 2: "
                            + utils.ast_loc(tup)
                        )
            case ast.Call(ast.Name("len"), [tup]):
                tup_t = self.type_check_exp(tup, env)
                match tup_t:
                    case utils.TupleType(ts):
                        return utils.IntType()
                    case utils.Bottom():
                        return utils.Bottom()
                    case _:
                        raise Exception(
                            "len expected a tuple, not "
                            + repr(tup_t)
                            + "\nAST info 1: "
                            + utils.ast_loc(e)
                            + " & AST info 2: "
                            + utils.ast_loc(tup)
                        )
            # after expose_allocation
            case utils.GlobalValue(name):
                return utils.IntType()
            case utils.Allocate(length, typ):
                return typ
            case _:
                return super().type_check_exp(e, env)

    def type_check_stmts(self, ss, env):
        if len(ss) == 0:
            return
        match ss[0]:
            case utils.Collect(size):
                return self.type_check_stmts(ss[1:], env)
            case ast.Assign(
                [ast.Subscript(tup, ast.Constant(index), ast.Store())], value
            ):
                tup_t = self.type_check_exp(tup, env)
                value_t = self.type_check_exp(value, env)
                match tup_t:
                    case utils.TupleType(ts):
                        self.check_type_equal(ts[index], value_t, ss[0])
                    case utils.Bottom():
                        pass
                    case _:
                        raise Exception(
                            "type_check_stmts: expected a tuple, not "
                            + repr(tup_t)
                            + (
                                ("\nAST info 1: " + utils.ast_loc(ss[0]))
                                if isinstance(ss[0], ast.AST)
                                else "\n"
                            )
                            + "AST info 2: "
                            + utils.ast_loc(tup)
                            + (
                                (" & AST info 3: " + utils.ast_loc(index))
                                if isinstance(index, ast.AST)
                                else ""
                            )
                            + " & AST info 4: "
                            + utils.ast_loc(value)
                        )
                return self.type_check_stmts(ss[1:], env)
            case _:
                return super().type_check_stmts(ss, env)


if __name__ == "__main__":
    t1 = ast.Tuple([ast.Constant(1), ast.Constant(2)], ast.Load())
    t1_at_0 = ast.Subscript(t1, ast.Constant(0), ast.Load())
    pr = ast.Expr(ast.Call(ast.Name("print"), [t1_at_0]))
    p = ast.Module([pr])
    TypeCheckLtup().type_check(p)
