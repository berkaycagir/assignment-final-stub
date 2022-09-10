import ast
from type_check_Lfun import TypeCheckLfun
import utils

class TypeCheckLexam(TypeCheckLfun):

  def parse_type_annot(self, annot):   # FIXED
      match annot:
        case utils.ListType(t):
          return utils.ListType(self.parse_type_annot(t))
        case ast.Subscript(ast.Name('list'), t):
            ty = self.parse_type_annot(t)
            return utils.ListType(ty)
        case _:
            return super().parse_type_annot(annot)

class TypeCheckLexam(TypeCheckLfun):
    def type_check_exp(self, e, env):
        match e:
            case utils.AllocateArray(length, typ):  # FIXED
                return typ
            case ast.List(es, ast.Load()):
                ts = [self.type_check_exp(e, env) for e in es]
                elt_ty = ts[0]
                for (ty, elt) in zip(ts, es):
                    self.check_type_equal(elt_ty, ty, elt)
                e.has_type = utils.ListType(elt_ty)  # type: ignore
                return e.has_type  # type: ignore
            case ast.Subscript(tup, ast.Slice(lower, upper), ast.Load()):
                tup_t = self.type_check_exp(tup, env)
                tup.has_type = tup_t
                lower_ty = self.type_check_exp(lower, env)
                upper_ty = self.type_check_exp(upper, env)
                self.check_type_equal(lower_ty, utils.IntType(), lower)
                self.check_type_equal(upper_ty, utils.IntType(), upper)
                match (tup_t, lower, upper):
                    case (utils.ListType(_), _, _):
                        e.has_type = tup_t
                        return tup_t
                    case (utils.TupleType(tys), ast.Constant(lower_v), ast.Constant(upper_v)):
                        ret_t = tys[lower_v: upper_v]
                        e.has_type = utils.TupleType(ret_t)
                        return e.has_type
                    case _:
                        raise Exception(
                            "untypable slicing expression: "
                            + repr(e)
                            + " with sequence type "
                            + repr(tup_t)
                            + "\nAST info 1: "
                            + utils.ast_loc(e)
                            + " & AST info 2: "
                            + utils.ast_loc(tup)
                        )
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
                            "len expected tuple or list, not "
                            + repr(tup_t)
                            + "\nAST info 1: "
                            + utils.ast_loc(e)
                            + " & AST info 2: "
                            + utils.ast_loc(tup)
                        )
            case ast.Call(ast.Name("array_len"), [tup]):
                tup_t = self.type_check_exp(tup, env)
                tup.has_type = tup_t  # type: ignore
                match tup_t:
                    case utils.ListType(_):
                        return utils.IntType()
                    case _:
                        raise Exception(
                            "array_len expected list, not "
                            + repr(tup_t)
                            + "\nAST info 1: "
                            + utils.ast_loc(e)
                            + " & AST info 2: "
                            + utils.ast_loc(tup)
                        )
            case ast.Call(ast.Name("array_load"), [tup, index]):
                tup_ty = self.type_check_exp(tup, env)
                tup.has_type = tup_ty  # type: ignore
                index_ty = self.type_check_exp(index, env)
                self.check_type_equal(index_ty, utils.IntType(), index)
                match tup_ty:
                    case utils.ListType(t):
                        return t
                    case _:
                        raise Exception(
                            "array_len expected list, not "
                            + repr(tup_ty)
                            + "\nAST info 1: "
                            + utils.ast_loc(e)
                            + " & AST info 2: "
                            + utils.ast_loc(tup)
                            + " & AST info 3: "
                            + utils.ast_loc(index)
                        )
            case ast.Call(ast.Name("array_store"), [tup, index, value]):
                tup_ty = self.type_check_exp(tup, env)
                tup.has_type = tup_ty  # type: ignore
                index_ty = self.type_check_exp(index, env)
                value_ty = self.type_check_exp(value, env)
                self.check_type_equal(index_ty, utils.IntType(), index)
                match tup_ty:
                    case utils.ListType(t):
                        self.check_type_equal(value_ty, t, value)
                        return utils.VoidType()
                    case _:
                        raise Exception(
                            "array_store expected list, not "
                            + repr(tup_ty)
                            + "\nAST info 1: "
                            + utils.ast_loc(e)
                            + " & AST info 2: "
                            + utils.ast_loc(tup)
                            + " & AST info 3: "
                            + utils.ast_loc(index)
                            + " & AST info 4: "
                            + utils.ast_loc(value)
                        )
            case ast.Subscript(tup, index, ast.Load()):
                tup_ty = self.type_check_exp(tup, env)
                tup.has_type = tup_ty  # type: ignore
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

    def type_check_stmts(self, ss, env):
        if len(ss) == 0:
            return utils.Bottom()
        match ss[0]:
            case ast.Assign([ast.Subscript(tup, index, ast.Store())], value):
                tup_ty = self.type_check_exp(tup, env)
                value_ty = self.type_check_exp(value, env)
                index_ty = self.type_check_exp(index, env)
                self.check_type_equal(index_ty, utils.IntType(), index)
                tup.has_type = tup_ty  # type: ignore
                match tup_ty:
                    case utils.ListType(ty):
                        self.check_type_equal(ty, value_ty, ss[0])
                    case _:
                        # fall back to check for tuples
                        return super().type_check_stmts(ss, env)
                        #    raise Exception('type_check_stmts: expected a list, not ' \
                        #                + repr(tup_t))
                return self.type_check_stmts(ss[1:], env)
            case _:
                return super().type_check_stmts(ss, env)
