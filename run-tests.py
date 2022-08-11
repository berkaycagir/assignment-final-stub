import os
import sys
from pathlib import Path

import click

import compiler
import interp_Cfun
import interp_Lfun
import type_check_Cfun
import type_check_Lfun
from utils import enable_tracing, run_one_test, run_tests

_compiler = compiler.Compiler()


@click.command()
@click.option("-l", "--lang", help="Lang to use", required=True, type=str)
@click.option("-c", "--compiler", help="Compiler to use", required=True, type=str)
@click.option(
    "--trace/--no-trace",
    default=False,
    show_default=True,
    help="Enable tracing",
    type=bool,
)
@click.option(
    "-r",
    "--recursion-limit",
    default=10000,
    show_default=True,
    help="Change the recursion limit",
    type=int,
)
@click.argument("path", type=click.Path(exists=True))
def main(lang, compiler, trace, recursion_limit, path):
    """
    Runs test(s) found in PATH. If PATH is a directory,
    script will try to find and run all the tests in it.
    If it's a file, script will try to run only that single
    test.
    """
    sys.setrecursionlimit(recursion_limit)
    if trace:
        enable_tracing()

    p = Path(path)
    if Path.is_dir(p):
        run_tests(
            path=p,
            lang=lang,
            compiler=_compiler,
            compiler_name=compiler,
            type_check_P=type_check_Lfun.TypeCheckLfun().type_check,
            interp_P=interp_Lfun.InterpLfun().interp,
            type_check_C=type_check_Cfun.TypeCheckCfun().type_check,
            interp_C=interp_Cfun.InterpCfun().interp,
        )
    else:
        succ_passes, tot_passes, succ_test = run_one_test(
            test=p,
            lang=lang,
            compiler=_compiler,
            compiler_name=compiler,
            type_check_P=type_check_Lfun.TypeCheckLfun().type_check,
            interp_P=interp_Lfun.InterpLfun().interp,
            type_check_C=type_check_Cfun.TypeCheckCfun().type_check,
            interp_C=interp_Cfun.InterpCfun().interp,
        )
        print("test file: " + str(p))
        # Report the pass/fails
        print(
            "tests: "
            + repr(succ_test)
            + " successful test for compiler "
            + compiler
            + " on language "
            + lang
        )
        print(
            "passes: "
            + repr(succ_passes)
            + "/"
            + repr(tot_passes)
            + " for compiler "
            + compiler
            + " on language "
            + lang
        )


if __name__ == "__main__":
    main()
