import ast
from type_check_Cfun import TypeCheckCfun
import utils


class TypeCheckCexam(TypeCheckCfun):
    def check_type_equal(self, t1, t2, e):
        match t1:
            case utils.ListType(ty1):
                match t2:
                    case utils.ListType(ty2):
                        self.check_type_equal(ty1, ty2, e)
                    case utils.Bottom():
                        pass
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
            case ast.List(es, ast.Load()):
                ts = [self.type_check_exp(e, env) for e in es]
                elt_ty = ts[0]
                for (ty, elt) in zip(ts, es):
                    self.check_type_equal(elt_ty, ty, elt)
                e.has_type = utils.ListType(elt_ty)  # type: ignore
                return e.has_type  # type: ignore
            case ast.Call(ast.Name("len"), [tup]):
                tup_t = self.type_check_exp(tup, env)
                tup.has_type = tup_t  # type: ignore
                match tup_t:
                    case utils.TupleType(_) | utils.ListType(_):
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
            case ast.Subscript(tup, index, ast.Load()):
                tup_ty = self.type_check_exp(tup, env)
                index_ty = self.type_check_exp(index, env)
                self.check_type_equal(index_ty, utils.IntType(), index)
                match tup_ty:
                    case utils.TupleType(ts):
                        match index:
                            case ast.Constant(i):
                                return ts[i]
                            case _:
                                raise Exception(
                                    "subscript required constant integer index"
                                    + "\nAST info 1: "
                                    + utils.ast_loc(e)
                                    + " & AST info 2: "
                                    + utils.ast_loc(tup)
                                    + (
                                        (" & AST info 3: " + utils.ast_loc(index))
                                        if isinstance(index, ast.AST)
                                        else ""
                                    )
                                )
                    case utils.ListType(ty):
                        return ty
                    case utils.Bottom():
                        return utils.Bottom()
                    case _:
                        raise Exception(
                            "subscript expected a tuple, not "
                            + repr(tup_ty)
                            + "\nAST info 1: "
                            + utils.ast_loc(e)
                            + " & AST info 2: "
                            + utils.ast_loc(tup)
                            + (
                                (" & AST info 3: " + utils.ast_loc(index))
                                if isinstance(index, ast.AST)
                                else ""
                            )
                        )
            case ast.BinOp(left, ast.Mult() | ast.FloorDiv() | ast.Mod(), right):
                l = self.type_check_exp(left, env)
                self.check_type_equal(l, utils.IntType(), left)
                r = self.type_check_exp(right, env)
                self.check_type_equal(r, utils.IntType(), right)
                return utils.IntType()
            case _:
                return super().type_check_exp(e, env)

    def type_check_stmt(self, s, env):
        match s:
            case ast.Assign([ast.Subscript(tup, index, ast.Store())], value):
                tup_t = self.type_check_exp(tup, env)
                value_t = self.type_check_exp(value, env)
                index_ty = self.type_check_exp(index, env)
                self.check_type_equal(index_ty, utils.IntType(), index)
                match tup_t:
                    case utils.ListType(ty):
                        self.check_type_equal(ty, value_t, s)
                    case _:
                        return super().type_check_stmt(s, env)
            case _:
                return super().type_check_stmt(s, env)
