# Ritz Runtime - Build entry point object files
#
# Creates pre-compiled object files for linking:
#   ritz_start.x86_64.o        - For programs with main(argc, argv)
#   ritz_start_noargs.x86_64.o - For programs with main()
#   ritz_start_envp.x86_64.o   - For programs with main(argc, argv, envp)

.PHONY: all clean

ARCH := $(shell uname -m)
CC := clang

all: ritz_start.$(ARCH).o ritz_start_noargs.$(ARCH).o ritz_start_envp.$(ARCH).o

# Use clang -c to compile .ll to .o (clang accepts LLVM IR directly)
ritz_start.x86_64.o: ritz_start.x86_64.ll
	$(CC) -c -o $@ $<

ritz_start_noargs.x86_64.o: ritz_start_noargs.x86_64.ll
	$(CC) -c -o $@ $<

ritz_start_envp.x86_64.o: ritz_start_envp.x86_64.ll
	$(CC) -c -o $@ $<

clean:
	rm -f *.o
