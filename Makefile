PYTHON3_10= python3.10

.PHONY: all clean distclean run-tests create-tests exam-tests

all: runtime.o mul-div-mod.s mul-div-mod requirements.installed run-tests

runtime.o: runtime.c runtime.h
	gcc -c -g -std=c99 runtime.c

requirements.installed: requirements.txt
	pip3 install -r requirements.txt
	echo > requirements.installed

run-tests:
	$(PYTHON3_10) run-tests.py -l var -c var tests/var
	$(PYTHON3_10) run-tests.py -l regalloc -c regalloc tests/regalloc
	$(PYTHON3_10) run-tests.py -l lif -c lif tests/lif
	$(PYTHON3_10) run-tests.py -l tuples -c tuples tests/tuples
	$(PYTHON3_10) run-tests.py -l fun -c fun tests/fun

mul-div-mod.s: mul-div-mod.c
	gcc -S mul-div-mod.c

mul-div-mod: mul-div-mod.c
	gcc -o mul-div-mod mul-div-mod.c

create-tests:
	cd tests/exam ; \
	for f in *.py ; do \
		bf=`basename $$f .py` ; \
		sed -ne 's/#in=//w'$$bf.in -e 's/#golden=//w'$$bf.golden $$f ; \
	done

## checks minimum requirements
## * all provided tests must be valid
## * all tests passed by the compiler
exam-tests:
	$(PYTHON3_10) run-exam-tests.py

clean:
	$(RM) tests/*/*.s
	$(RM) tests/*/*.out
	$(RM) a.out
	$(RM) -f mul-div-mod.o
	$(RM) -rf *.dSYM

distclean: clean
	$(RM) -f runtime.o
	$(RM) -rf __pycache__
