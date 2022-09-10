import os
import sys
from pathlib import Path
from typing import Callable

import click

import compiler
from compiler_Lexam import CompilerLexam
import interp_Cfun
import interp_Lfun
import type_check_Cfun
import type_check_Lfun

import interp_Cexam
import interp_Lexam
import type_check_Lexam
import type_check_Cexam

from utils import enable_tracing, run_one_test, run_tests

# mapping of language names to type checkers and interpreters for that language
processors : dict[str, dict[str, Callable]] = {
    "exam":
    {
        "compiler": CompilerLexam(),
        "type_check_P": type_check_Lexam.TypeCheckLexam().type_check,
        "interp_P": interp_Lexam.InterpLexam().interp,
        "type_check_C": type_check_Cexam.TypeCheckCexam().type_check,
        "interp_C": interp_Cexam.InterpCexam().interp
    },
    "fun":
    {
        "compiler": compiler.Compiler(),
        "type_check_P": type_check_Lfun.TypeCheckLfun().type_check,
        "interp_P": interp_Lfun.InterpLfun().interp,
        "type_check_C": type_check_Cfun.TypeCheckCfun().type_check,
        "interp_C": interp_Cfun.InterpCfun().interp
    },
}

@click.command()
@click.option("-v", "--verbose",
     is_flag=True, show_default=True, default=False, help="Print progress messages"
)
@click.option("-l", "--lang", help="Lang to use", required=True, type=click.Choice(["fun", "exam"]))
@click.option("-c", "--compiler", help="Compiler to use", required=True, type=click.Choice(["fun", "exam"]))
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
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
def main(verbose, lang, compiler, trace, recursion_limit, paths):
    """
    Runs tests found in PATH. If PATH is a directory,
    script will try to find and run all the tests in it.
    If it is a single file, script will try to run only that single
    test.
    """
    sys.setrecursionlimit(recursion_limit)
    if trace:
        enable_tracing()
    for path in paths:
        if verbose:
            print("processing path " + path)
        p = Path(path)
        if Path.is_dir(p):
            run_tests(
                path=path,
                lang=lang,
                # compiler=_compiler,
                compiler_name=compiler,
                **processors[lang]
            )
        else:
            succ_passes, tot_passes, succ_test = run_one_test(
                test=p,
                lang=lang,
                # compiler=_compiler,
                compiler_name=compiler,
                **processors[lang]
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
