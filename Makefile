PYTHON3_10= python3.10

.PHONY: all clean distclean run-tests create-tests exam-tests

all: runtime.o mul-div-mod.s mul-div-mod requirements.installed run-tests

runtime.o: runtime.c runtime.h
	gcc -c -g -std=c99 runtime.c

requirements.installed: requirements.txt
	pip3 install -r requirements.txt
	echo > requirements.installed

REGRESSION= tests/var tests/regalloc tests/lif  tests/tuples tests/fun

run-tests:
	$(PYTHON3_10) run-tests.py -v -l fun -c fun $(REGRESSION)
	$(PYTHON3_10) run-tests.py -v -l exam -c exam tests/exam

mul-div-mod.s: mul-div-mod.c
	gcc -S mul-div-mod.c

mul-div-mod: mul-div-mod.c
	gcc -o mul-div-mod mul-div-mod.c

create-tests:
	for d in exam exam-2 ; do \
		cd tests/$$d ; \
		for f in *.py ; do \
			bf=`basename $$f .py` ; \
			sed -ne 's/#in=//w'$$bf.in -e 's/#golden=//w'$$bf.golden $$f ; \
		done ; \
		cd ../.. ; \
	done

## checks minimum requirements
## * all provided tests must be valid
## * all tests passed by the compiler
exam-tests:
	$(PYTHON3_10) run-exam-tests.py
	$(PYTHON3_10) run-tests.py -v -l exam -c exam tests/exam-2

clean:
	$(RM) tests/*/*.s
	$(RM) tests/*/*.out
	$(RM) a.out
	$(RM) -f mul-div-mod.o
	$(RM) -rf *.dSYM

distclean: clean
	$(RM) -f runtime.o
	$(RM) -rf __pycache__
