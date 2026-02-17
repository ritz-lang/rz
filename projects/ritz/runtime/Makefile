# Ritz Runtime - Build entry point object files
#
# Creates pre-compiled object files for linking:
#   ritz_start.x86_64.o        - For programs with main(argc, argv) [Linux]
#   ritz_start_noargs.x86_64.o - For programs with main() [Linux]
#   ritz_start_envp.x86_64.o   - For programs with main(argc, argv, envp) [Linux]
#   ritz_start.harland.x86_64.o        - For programs with main(argc, argv) [Harland]
#   ritz_start_noargs.harland.x86_64.o - For programs with main() [Harland]
#   ritz_start_envp.harland.x86_64.o   - For programs with main(argc, argv, envp) [Harland]

.PHONY: all clean

ARCH := $(shell uname -m)
CC := clang

# Linux runtime objects
LINUX_OBJS = ritz_start.$(ARCH).o ritz_start_noargs.$(ARCH).o ritz_start_envp.$(ARCH).o

# Harland runtime objects
HARLAND_OBJS = ritz_start.harland.$(ARCH).o ritz_start_noargs.harland.$(ARCH).o ritz_start_envp.harland.$(ARCH).o

all: $(LINUX_OBJS) $(HARLAND_OBJS)

# Use clang -c to compile .ll to .o (clang accepts LLVM IR directly)
# Linux runtimes
ritz_start.x86_64.o: ritz_start.x86_64.ll
	$(CC) -c -o $@ $<

ritz_start_noargs.x86_64.o: ritz_start_noargs.x86_64.ll
	$(CC) -c -o $@ $<

ritz_start_envp.x86_64.o: ritz_start_envp.x86_64.ll
	$(CC) -c -o $@ $<

# Harland runtimes
ritz_start.harland.x86_64.o: ritz_start.harland.x86_64.ll
	$(CC) -c -o $@ $<

ritz_start_noargs.harland.x86_64.o: ritz_start_noargs.harland.x86_64.ll
	$(CC) -c -o $@ $<

ritz_start_envp.harland.x86_64.o: ritz_start_envp.harland.x86_64.ll
	$(CC) -c -o $@ $<

clean:
	rm -f *.o
