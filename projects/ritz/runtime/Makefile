# Ritz Runtime - Build entry point object files
#
# Every `*.ll` in this directory is an entry-point shim: it defines `_start`,
# marshals the kernel's exec stack into the shape `main` expects, and calls
# sys_exit with the result. It also defines, weak, ritzlib's core platform
# hooks (ritz_platform_*, AGAST #4119) for a program that links no ritzlib.sys. The `.o` files are gitignored build products.
#
# There is one entry path (docs/V1_ABI_CLEANUP.md, AGAST #200):
#   ritz_start.<arch>.o          - calls main(argc, argv, envp), Linux
#   ritz_start.harland.<arch>.o  - the same for Harland userspace
# A `main` of any accepted shape links against it; the compiler adapts a
# Ritz-native `main(args: Span<StrView>, ...)` (C's argc/argv `main` is
# refused, AGAST #204).
#
# The object list is DERIVED from the .ll files on disk rather than
# hand-maintained. The previous version listed six rules explicitly, so the
# two `start*.ll` shims added by the v1 ABI work (AGAST #198) had no rule at
# all and could never be built. Deriving means adding a shim is a one-file
# change, which is the whole point of putting them in their own directory.

.PHONY: all clean

CC := clang

# Every shim source in this directory, and the object each one lowers to.
SRCS := $(wildcard *.ll)
OBJS := $(SRCS:.ll=.o)

all: $(OBJS)

# clang accepts LLVM IR directly, so no separate llvm-as/llc step is needed.
# One pattern rule covers every arch/OS variant because the target triple and
# datalayout are declared inside each .ll.
%.o: %.ll
	$(CC) -c -o $@ $<

clean:
	rm -f *.o
