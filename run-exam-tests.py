from type_check_Lexam import TypeCheckLexam
from interp_Lexam import InterpLexam
from type_check_Cexam import TypeCheckCexam
from interp_Cexam import InterpCexam
from utils import enable_tracing, run_tests, validate_tests
from compiler_Lexam import CompilerLexam
import sys


sys.setrecursionlimit(10000)

compiler = CompilerLexam()

if False:
    enable_tracing()

test_root = "tests/"
test_suites = ["exam-2", "exam", "mytests"]

if all(validate_tests(test_root + t, "exam", InterpLexam().interp) for t in test_suites):
    print("Congratulations, the interpreter verifies all tests!")
else:
    print("The interpreter failed on one or more tests.")

for test_suite in test_suites:
    run_tests(test_suite, "exam", compiler, "exam",
        type_check_P= TypeCheckLexam().type_check,
        interp_P= InterpLexam().interp,
        type_check_C= TypeCheckCexam().type_check,
        interp_C= InterpCexam().interp)
