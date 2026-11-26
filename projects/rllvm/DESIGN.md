# razm and rllvm — relocatable ELF

Two programs replace the host tools that turn this tree's code into relocatable ELF64. [razm](#razm) replaces `as --64`. [rllvm](#what-rllvm-replaces) replaces `clang -c` on the `.ll` this tree already emits. Both write objects today's linkers already accept: hosted `clang` or `gcc` (`link_hosted`), and freestanding `ld.lld` (`link_freestanding_elf`). Neither links.

The native linker is [rld](#rld), a later project. This document specifies it. Nothing here is implemented yet.

Pipeline facts below are from `projects/ritz/build_pipeline.py` (`compile_ll_to_obj`, `OBJ_CLANG_FLAGS`, `freestanding_target`, `link_hosted`, `link_freestanding_elf`, `assemble_objects`, `ensure_runtime_object`) and from `projects/ritz/runtime/ritz_start.x86_64.ll` and `ritz_start.harland.x86_64.ll`.

## Project split

| Project | Path | Status | Owns |
|---|---|---|---|
| razm | `projects/razm` | first implementation | AT&T text → relocatable ELF64, and the one ELF writer |
| rllvm | `projects/rllvm` | after razm encodes | `.ll` → instructions, encoded by razm |
| rld | `projects/rld` | after both objects link with today's linkers | ELF objects + linker scripts → Linux and Harland executables |

razm is the assembler, as a library and a driver. Indium has no GNU `as`. The kernel's `.s` files (`assemble_objects` runs `as --64`) have to assemble on Indium, and that program has to be written in Ritz. razm is that program. It is the short one: it encodes instructions the text already chose. It does not select them, allocate registers, or parse LLVM IR.

rllvm is the compiler. It lowers LLVM IR to instructions and calls razm to encode them and write the object. Inline asm is text in razm's dialect, parsed by razm, not a second assembler inside rllvm. rllvm does not write ELF bytes itself.

`razm.llvm` and `razm.gas` are not backends of one tool. The `.s` path is razm. The `.ll` path is a compiler that uses razm. Putting instruction selection inside razm would make the tool Indium runs to assemble `boot.s` carry the LLVM lowerer, and it would make the short project the long one. There is one encoder and one ELF writer, both in razm. rllvm links razm as a library. The `razm` binary is only the `.s` driver.

rld is a separate project because its inputs are relocatable ELF objects from three producers (razm, rllvm through razm, `clang -c` of the `ritz_start` shims) and the linker scripts the tree already uses, and its output is an executable. This goal adds no `projects/razm`, `projects/rllvm` sources, or `projects/rld` directory.

UEFI COFF is not a third project. It stays on `clang --target=x86_64-unknown-windows-gnu` and `lld-link`. See [UEFI](#uefi).

## razm

razm replaces this invocation, run from the package directory so `.incbin` paths resolve:

```
as --64 -o <file>.o <file>.s
```

```
razm --64 -o OUT FILE.s
```

`--64` is required. The object is always ELF64 (`e_machine` EM_X86_64, `e_type` ET_REL). `--32` is an error. `.code16` and `.code32` in the file change the instruction encoding, not the ELF class. `boot.s` is assembled this way today even though its header comment still says `as --32`.

The ELF layout, symbol binding, and relocation types are the [object contract](#object-contract). razm is the only writer of those bytes. A section keeps the name the file gave it, including `.multiboot`, `.boot`, `.boot.data`, `.boot.bss`, and `.ap_trampoline`.

### Text razm accepts

The dialect is what the tree's `.s` files use, plus the inline-asm templates rllvm hands over. A directive, prefix, or mnemonic outside this set is an error, and that file stays on `as --64` until the set grows.

Directives and assignments:

- `.section name` and `.section name, "flags"` with an optional `, @nobits`. Flag letters are `a` (alloc), `w` (write), `x` (exec). `@nobits`, and the name `.bss`, are `SHT_NOBITS`. Anything else is `SHT_PROGBITS`. With no flags string, four names get GNU as's implicit flags: `.text` is `AX`, `.data` and `.bss` are `WA`, `.rodata` is `A`. Any other name with no flags string has no flags, as with `as`. A section's alignment is the largest `.align` in it, and 1 when it has none.
- `.code16`, `.code32`, `.code64`. The mode starts at `.code64`.
- `.global`, `.extern` (accepted, and an undefined symbol is already an undefined `STB_GLOBAL` reference), `.type name, @function` (`STT_FUNC`; no other `.type` kind), `.size`.
- `.align N` is alignment to N bytes, which is how `as` reads it for x86-64 ELF. `.align 8` is 8 bytes. `.align 4096` is 4096 bytes.
- `.set`, `.equ`, and `name = expr`.
- `.byte`, `.word`, `.long`, `.quad`, `.ascii`, `.asciz`, `.space`.
- `.macro` / `.endm` with `\param` and a macro body that calls another macro. `.rept` / `.endr` with a constant count.
- `.incbin "path"`, relative to the working directory.
- `#` through end of line is a comment. A label is `name:` or `.Lname:`. A numeric local label is `N:` and a reference is `Nb` / `Nf`.

Expressions are integer literals (decimal and `0x`), symbol names, `.` for the current location, parentheses, unary `-`, and the binary operators `*`, `/`, `<<`, `|`, `+`, `-`. That is the set the corpus uses: the multiboot checksum `-(0xE85250D6 + 0 + (multiboot_header_end - multiboot_header))`, `$(1 << 31)`, `$(4096 * 4 / 4)`, `$(KERNEL_CS | (SYSRET_BASE << 16))`, and `.space PERCPU_SIZE * PERCPU_SLOTS`. Precedence is GNU as's, highest first: unary `-`; then `*`, `/`, `<<`; then `|`; then `+`, `-`. Binary operators are left-associative. Arithmetic is 64-bit two's complement. `/` is signed and truncates toward zero; division by zero is an error. Note that under these rules `a + b | c` is `a + (b | c)`.

An expression evaluates to one of three kinds:

- Absolute: no symbol, or a difference `a - b` of two symbols defined in the same section, combined with constants by any operator.
- Relocatable: one symbol plus or minus an absolute value. This becomes a relocation against that symbol (against the section symbol plus offset when the symbol is local, as `as` does).
- Anything else is an error: a difference across sections, a product or shift involving a relocatable value, or two symbols added.

The operands of `.space`, `.rept`, `.align`, `.set`/`.equ`/`=` used in those operands, and `.incbin` must be absolute, with every symbol defined earlier in the file.

Relocation types follow from the field and the mode, matching GNU as:

| Field | `.code64` | `.code32` | `.code16` |
|---|---|---|---|
| `.byte` / `.word` / `.long` / `.quad` | `R_X86_64_8` / `16` / `32` / `64` | same | same |
| `.long sym - .` | `R_X86_64_PC32` | same | same |
| `$imm` with 16-bit operand size (`movw $sym, %ax`) | `R_X86_64_16` | `R_X86_64_16` | `R_X86_64_16` |
| `$imm` with 32-bit operand size (`movl $sym, %esi`) | `R_X86_64_32` | `R_X86_64_32` | — |
| `$imm` with 64-bit operand size (`movq $sym, %rax`) | `R_X86_64_32S` | — | — |
| Absolute memory operand (`movq sym, %rax`, `lgdt sym`) | `R_X86_64_32S` | `R_X86_64_32` | — |
| `movabsq $sym` | `R_X86_64_64` | — | — |
| `sym(%rip)` | `R_X86_64_PC32` | — | — |
| `call` / `jmp` / `jcc` to a symbol that is global, undefined, or in another section | `R_X86_64_PLT32` | `R_X86_64_PC32` | `R_X86_64_PC16` |

A `jmp`, `jcc`, or `call` to a local label in the same section needs no relocation. `jmp` and `jcc` to such a label use the short (rel8) form when the displacement fits and the near form otherwise, decided by iterating until no branch grows, as `as` does. `call` is always rel32. `loop` is rel8 only, and an out-of-range `loop` is an error. Alignment fill in an executable section is GNU as's multi-byte `nop` sequence, and zero bytes elsewhere.

Prefixes, only in front of an instruction: `lock`, `rep`.

Mnemonics, the union of those `.s` files and the inline-asm templates:

`addl`, `addq`, `andb`, `andl`, `andq`, `btl`, `call`, `callq`, `cld`, `clflush`, `cli`, `cmpl`, `cmpq`, `cpuid`, `decl`, `decq`, `hlt`, `inb`, `incl`, `incq`, `inl`, `invlpg`, `inw`, `iretq`, `ja`, `jb`, `jc`, `je`, `jmp`, `jmpq`, `jnc`, `jne`, `jnz`, `jz`, `lea`, `leaq`, `lfence`, `lgdt`, `lidt`, `lodsb`, `ltr`, `loop`, `lretq`, `mfence`, `movabsq`, `movb`, `movl`, `movq`, `movw`, `movzbl`, `nop`, `nopl`, `orb`, `orl`, `orq`, `outb`, `outl`, `outw`, `pause`, `popfl`, `popfq`, `popl`, `popq`, `pushfl`, `pushfq`, `pushl`, `pushq`, `rdmsr`, `rdrand`, `rdtsc`, `ret`, `retq`, `sarq`, `sfence`, `shll`, `shlq`, `shrq`, `std`, `sti`, `stosl`, `stosw`, `subq`, `swapgs`, `syscall`, `sysretq`, `testb`, `testl`, `testq`, `ud2`, `wrmsr`, `xchgq`, `xgetbv`, `xorb`, `xorl`, `xorq`, `xorw`.

`jmp` and `jmpq` are the same instruction, and so are `call`/`callq`, `ret`/`retq`, and `lea`/`leaq`. The current `.code16` / `.code32` / `.code64` selects the default operand size.

Operands are a GPR at any width; `%cr0`, `%cr2`, `%cr3`, `%cr4`; the segment registers `%cs`, `%ds`, `%es`, `%fs`, `%gs`, `%ss`; an immediate `$expr`; `*%reg`; AT&T memory `disp(%base,%index,scale)` with any part omitted; `sym(%rip)`; and an absolute memory operand whose address is an expression (`lgdt gdt64_ptr`, `lgdt (ap_gdt32_ptr - ap_trampoline_start + AP_TRAMPOLINE_BASE)`). In a macro body, `\param` substitutes into any token, including an identifier (`isr_stub_\num:`) and an immediate (`pushq $\num`).

### Library

razm is a library with three parts. rllvm uses all three. The `razm` binary is the text driver over them.

- `encode`: a structured instruction (mnemonic, operand size, operands) to bytes plus fixups. A fixup is (offset in the instruction, width, kind, target symbol, addend), where kind is absolute, absolute sign-extended, PC-relative, PLT, or GOTPCRELX. It accepts the encoder set below.
- `parse`: AT&T text to structured instructions and directives. It accepts only the [text dialect](#text-razm-accepts). A mnemonic the encoder knows but the dialect does not list is a parse error.
- `Object`: the ELF writer, holding sections, symbols, COMDAT groups, and fixups. It applies a PC-relative fixup to a local label in the same section itself, and turns every other fixup into a relocation, against the section symbol plus offset when the target is local.

rllvm passes structured instructions to `encode` directly. It does not print text and parse it back. Inline-asm templates go through `parse`, then `encode`. Branch sizing for rllvm's own branches uses the same iteration as razm's text.

The encoder set is the text dialect plus what rllvm selects. rllvm selects from baseline x86-64 (SSE2) plus the features in the function's `"target-features"`. It never selects `popcnt`, `lzcnt`, `tzcnt`, BMI, SSSE3, SSE4, or AVX. So `ctpop`, `ctlz`, and `cttz` are inline sequences, and vector operations SSE2 lacks (a `<4 x i32>` multiply, per-element variable shifts, vector division, a `<2 x i64>` compare) are sequences or split per element. Beyond the text dialect, the encoder set is:

- GPR: `mov` at every width, `movzx`/`movsx`/`movslq`, `lea`, `add`/`sub`/`and`/`or`/`xor`/`cmp`/`test`, `adc`/`sbb`, `neg`/`not`, `imul` (one-, two-, and three-operand), `mul`/`div`/`idiv`, `cbw`/`cwd`/`cdq`/`cqo`, `shl`/`shr`/`sar`/`rol`/`ror` by immediate and by `%cl`, `shld`/`shrd`, `bsf`/`bsr`, `bswap`, `setcc`, `cmovcc`, `jcc`, direct and indirect `jmp` and `call`, `push`/`pop`, `ret`, `xchg`, `lock xadd`, `lock cmpxchg`, the `lock` ALU forms, `mfence`, `ud2`.
- SSE and SSE2: `movss`/`movsd`/`movaps`/`movups`/`movdqa`/`movdqu`/`movd`/`movq`; scalar and packed `add`/`sub`/`mul`/`div` in single and double; `ucomiss`/`ucomisd`; `cmpss`/`cmpsd` and the packed forms; `andps`/`andpd`/`andnps`/`orps`/`xorps`/`xorpd`; `cvtsi2ss`/`cvtsi2sd`/`cvttss2si`/`cvttsd2si`/`cvtss2sd`/`cvtsd2ss`; `padd`/`psub` at b/w/d/q; `pmullw`/`pmuludq`; `pand`/`pandn`/`por`/`pxor`; `pcmpeq`/`pcmpgt` at b/w/d; `psll`/`psrl`/`psra` by immediate and by register; `pshufd`/`pshuflw`/`pshufhw`/`shufps`; `punpck*`; `packss*`/`packus*`; `pextrw`/`pinsrw`; `pmovmskb`; `psadbw`.
- x87, for [returns](#abi) only: `flds`, `fldl`, `fstps`, `fstpl`.
- Gated by `"target-features"`: `sha256rnds2`, `sha256msg1`, `sha256msg2` (`+sha`); `aesenc`, `aesenclast`, `aesdec`, `aesdeclast`, `aesimc`, `aeskeygenassist` (`+aes`); `pclmulqdq` (`+pclmul`).

Every encoder-only form has a unit test that compares razm's bytes with `as --64` on the same instruction text. That test calls `encode` directly; the text parser still rejects the form.

### What razm checks

The corpus is the eight `.s` files, frozen under `projects/razm/tests/corpus/` when the implementation exists: `kernel/boot.s`, `kernel/isr_stubs.s`, `kernel/ap_trampoline.s`, `kernel/syscall_entry.s`, `kernel/proc_switch.s`, `kernel/user_program.s`, `kernel/driver_stub.s`, and `boot/uefi_entry.s`. One synthetic fixture uses `.incbin`; no tracked `.s` file does today. The oracle on Linux is `as --64`.

For each file, the check is exact on everything a final link and a loader consume:

- Every section: name, type, flags, alignment, size, and contents byte for byte. Contents include instruction encodings, branch sizes, and alignment fill, because the rules above make them match `as`. Relocated fields hold zero in both objects (RELA keeps the addend in the relocation), so the bytes compare directly. This covers the multiboot checksum and the mixed-mode trampoline bytes.
- Every relocation, per section: offset, type, and addend, with the target normalized. A global or undefined target is compared by name. A local target is compared as (section, offset), so a section-symbol-plus-addend and a local-symbol reference that land on the same byte are equal.
- Every symbol razm and `as` both write (`.L` and numeric local labels are not written): name, section, value, size, type, and binding.
- Final link: the kernel files link with `ld.lld -T kernel/linker.ld --unresolved-symbols=ignore-all --strip-all`, once from the `as` objects and once from the razm objects. The two outputs are `cmp`-identical, which checks every resolved value.

The `.o` files as a whole are not compared with `cmp`; symbol-table order and string-table layout differ and are not part of the contract.

`uefi_entry.s` is in the corpus as ELF text. razm does not write COFF, and the UEFI link stays on `lld-link`.

The driver shells out to `as` and `ld.lld`. It does not import `build_pipeline.py`. The run is `./rz test razm` and no other project. That is not `matrix-full` and not `./rz build --all`.

## What rllvm replaces

`compile_ll_to_obj` runs `clang` on one `.ll` and writes one `.o`. Hosted flags are `OBJ_CLANG_FLAGS`:

```
clang -c -O2 -fPIC -ffreestanding -fno-builtin <file>.ll -o <file>.o
```

Freestanding ELF flags come from `freestanding_target`. The default triple is `x86_64-none-elf`. There is no `-O2`.

```
clang -c --target=<triple> -ffreestanding -fno-builtin -march=native -msha
      [-fPIC] [-mcmodel=<model>] [-mno-red-zone] <file>.ll -o <file>.o
```

`-fPIC` is added when the bin sets `pic` or the triple ends in `-linux`. `-mcmodel=` is added when the bin sets `code-model`, except `pic` together with `large` (that pair is not passed). `-mno-red-zone` is added when the bin sets `no-red-zone`.

`ensure_runtime_object` compiles the shim with bare `clang -c -o <shim>.o <shim>.ll` (no `-O2`, no `-fPIC`).

rllvm is the program those three invocations call for ELF. razm writes the object. The argv below is the contract, so a later swap in `build_pipeline.py` is a change of program name.

| Flag | Effect |
|---|---|
| `-c` | Required. One relocatable object. rllvm does not link. |
| `-o PATH` | Output path. Default is the input name with `.o`. |
| `-fPIC` | Small PIC relocations. |
| `-mcmodel=small` | Small code model. This is the default. |
| `-mcmodel=kernel` | Kernel code model. |
| `-mcmodel=large` | Large code model. |
| `-O0` `-O1` `-O2` `-O3` `-Os` `-Oz` | Accepted. v1 codegen does not change with the level. See [Optimization](#optimization-bar). |
| `-ffreestanding` `-fno-builtin` | Accepted and ignored. They are frontend flags. On `.ll` input they do not change codegen, and they are not what keeps libc calls out of the object. The IR's `"no-builtins"` attribute is. |
| `-mno-red-zone` | Accepted and ignored. It is a frontend flag and does nothing on `.ll` input. The IR's `noredzone` attribute is what the kernel uses (`--no-red-zone` on ritz). |
| `-march=native` `-msha` `-maes` `-mpclmul` | Accepted and ignored. Instruction selection of SHA, AES, and CLMUL follows the function's `"target-features"`, not the host CPU. |
| `-g` | Accepted and ignored. v1 objects have no DWARF. |
| `--target=<triple>` | Selects ELF vs rejection. See triples below. Absent: use the module triple, or `x86_64-unknown-linux-gnu` when the module has none. |

Any other flag is an error. `-mcmodel=large` together with `-fPIC` is an error. The pipeline never passes that pair (`pic` and `large` drops `-mcmodel=large` and compiles small PIC). rllvm does not silently drop it.

## Triples

All four ELF triples are the same SysV AMD64 ABI. Objects from any mix of them link. The Linux shim's module triple is `x86_64-pc-linux-gnu`. ritz1's module triple is `x86_64-unknown-linux-gnu` (`emitter.ritz` writes that string; `--target` on ritz changes trap lowering, not this default line). Hosted `clang -c` passes no `--target`, and clang 21 overrides that module triple with the host triple `x86_64-pc-linux-gnu` (`-Woverride-module`). The override does not change the ABI. Harland's shim is `x86_64-unknown-none`. The kernel bin is `x86_64-none-elf`. Indium userspace is `x86_64-unknown-none`. ELF has no triple field; rllvm records the ABI as EM_X86_64, SysV.

| Triple | rllvm |
|---|---|
| `x86_64-unknown-linux-gnu` | ELF, SysV |
| `x86_64-pc-linux-gnu` | ELF, SysV |
| `x86_64-none-elf` | ELF, SysV |
| `x86_64-unknown-none` | ELF, SysV |
| `x86_64-unknown-windows-gnu`, any triple containing `uefi` or `windows` | error, exit non-zero. That `.ll` stays on clang. |

A missing or empty `target datalayout` means the x86-64 ELF layout below. Any other datalayout is an error.

## Object contract

ELF64, little-endian, `e_machine` EM_X86_64, `e_type` ET_REL. The file has a section header table. A program header is optional and v1 writes none.

Data layout, when the module does not name one: little-endian; `i8` align 1, `i16` align 2, `i32` and `float` align 4, `i64`, `double`, `ptr`, and a typed pointer align 8; aggregate align is the max field align, size rounded up to that align; `packed` structs align to 1; `<16 x i8>`, `<8 x i16>`, `<4 x i32>`, `<2 x i64>` align 16; `<8 x i32>`, `<4 x i64>` align 32. Pointers are 64-bit. A typed pointer is that same value.

### Sections

| Section | Contents |
|---|---|
| `.text` | Functions with no `comdat`. `SHF_ALLOC \| SHF_EXECINSTR`. |
| `.text.<name>` | One per function with a `comdat`, holding only that function. `SHF_ALLOC \| SHF_EXECINSTR \| SHF_GROUP`. |
| `.rodata` | Constants, including `private unnamed_addr` strings. `SHF_ALLOC`. |
| `.data` | Initialized globals. `SHF_ALLOC \| SHF_WRITE`. |
| `.bss` | Zero-initialized globals. `SHF_ALLOC \| SHF_WRITE`, `SHT_NOBITS`. |
| `.rela.*` | Relocations against the matching section. `.rela.text.<name>` carries `SHF_GROUP`. |
| `.group` | One `GRP_COMDAT` group per COMDAT function. `sh_link` is `.symtab`, `sh_info` is the signature symbol. Members are `.text.<name>` and, when it exists, `.rela.text.<name>`. |
| `.symtab` `.strtab` `.shstrtab` | Symbols and names. |

These names hold in every code model, including large. Clang's large model writes `.ltext`, `.ldata`, `.lbss`, and `.lrodata`; rllvm does not, so `indium/user/linker.ld`, which names only `.text`, `.rodata`, `.data`, and `.bss`, places a large-model rllvm object as written.

No `.eh_frame`. No DWARF. This is a known difference from clang's objects, which carry `.eh_frame`. The kernel script and `linker_pie.ld` discard `.eh_frame`, and the other scripts take clang's as an orphan section, so an object without one links under every script. rllvm does not emit calls to `memcpy`, `memset`, `memmove`, `bcmp`, or `strlen`. Copies and fills are inline, or they are calls to symbols the IR already names (`__ritz_sret_copy`, `__ritz_sret_zero`).

### Symbols

| LLVM linkage | ELF |
|---|---|
| `define` / `global` (external) | `STB_GLOBAL` |
| `internal`, `private` | `STB_LOCAL` |
| `weak`, `weak_odr` on a global | `STB_WEAK`, no COMDAT group |
| `weak` on a function with no `comdat` | `STB_WEAK`, no COMDAT group |
| `weak_odr` on a function that has `comdat` | `STB_WEAK` in a COMDAT group whose signature is that comdat name |
| `linkonce_odr` on a function that has `comdat` | `STB_WEAK` in a COMDAT group, same rule |
| `available_externally` | No symbol and no body. The defining object owns the symbol. |
| `declare`, `external global` | Undefined `STB_GLOBAL` reference. |

COMDAT follows the IR. ritz1 puts `$name = comdat any` on ODR functions (`linkonce_odr` async poll fns, `weak_odr` generated `E__from`) and does not put a comdat on `weak_odr` globals. A `weak_odr` global with a comdat would collapse same-named globals across modules. rllvm implements the IR it is given: a symbol whose definition has `comdat` gets a group; a `weak` function or global with no `comdat` does not. `define weak` with no comdat is how both shims and `emit_platform_hooks` define `ritz_platform_page_map`, `ritz_platform_page_unmap`, and `ritz_platform_fatal`. They stay out of a group so a strong `ritzlib.sys` definition of the same name overrides them.

A COMDAT function gets its own section because a linker discards a whole group, and it cannot discard one function out of a shared `.text`. This is the layout clang writes (`.text.f` and `.rela.text.f` in group `f`). In v1 a comdat has exactly one member: a function whose comdat name equals its own name, which is what ritz1 emits (`define linkonce_odr ... comdat`). Two IR objects naming the same comdat, a comdat on a global, and a comdat whose name differs from its function are errors. A constant rllvm materializes for a COMDAT function (a float literal, a `fabs` mask) goes in the shared `.rodata`, not in the group. When the linker discards a duplicate group, that constant is left unreferenced, which is harmless.

### Relocations

The code model and `-fPIC` choose the set. rllvm uses the relocations clang 21 writes for the same IR and flags, so relocation comparisons against the oracle need no exceptions. Every relocation below is one the existing linkers already accept (`clang`/`gcc` for hosted, `ld.lld` and GNU `ld` for freestanding ELF).

ritz1 marks no symbol `dso_local`, so every non-local global is preemptible to the code generator, even under the static relocation model. The linker relaxes `R_X86_64_REX_GOTPCRELX` to a direct address when the symbol resolves locally.

| Profile | When | External data | `internal` / `private` data | Calls |
|---|---|---|---|---|
| Small PIC | `-fPIC`, model `small` | `R_X86_64_REX_GOTPCRELX` | `R_X86_64_PC32` | `R_X86_64_PLT32` |
| Small PIE | no `-fPIC`, model `small`: the bare `clang -c` of either shim. clang 21 defaults to PIE. | `R_X86_64_REX_GOTPCRELX` | `R_X86_64_PC32` | `R_X86_64_PLT32` |
| Kernel | `-mcmodel=kernel`, no `-fPIC` | `R_X86_64_REX_GOTPCRELX` | `R_X86_64_32S` (sign-extended, VMAs in the high 2 GiB) | `R_X86_64_PLT32` |
| Large | `-mcmodel=large`, no `-fPIC` | `R_X86_64_64` | `R_X86_64_64` | `movabs` of the address (`R_X86_64_64`) and an indirect call |

In every profile a pointer in a data initializer is `R_X86_64_64`, and a call to a function in the same section needs no relocation. No rllvm profile writes `R_X86_64_32`: the hosted link is PIE, and it would reject one. razm writes the relocation the text asks for, so `.long sym` in a kernel `.s` file is still `R_X86_64_32`.

Small PIC is the hosted default (`-fPIC` is in `OBJ_CLANG_FLAGS`) and every indium bin with `pic = true`. Indium's `minimal_syscall` and `portable_getpid` set `code-model = "large"` and do not set `pic`. The pipeline drops `-mcmodel=large` when `pic` is also set; no in-tree bin sets both. Kernel is `projects/harland/ritz.toml` (`code-model = "kernel"`, `no-red-zone`, `stack-protector`, triple `x86_64-none-elf`), linked at `KERNEL_VIRT_BASE = 0xFFFFFFFF80000000`.

Small PIC objects, small PIE objects (the `clang -c` shim), razm objects, and objects `as --64` already produced link in one hosted invocation. rllvm objects use the relocation set for the flags they were given, so that mix keeps linking.

### ABI

rllvm lowers calls the way LLVM's x86-64 backend lowers the same IR types. That is the contract, not the C ABI's classification, because ritz1 passes and returns structs under 256 bytes and arrays as first-class IR aggregates (`%T`, `[N x T]`). LLVM splits those per element; it does not pack them into eightbytes the way the C ABI would. rllvm objects and clang objects call each other in both directions, so rllvm matches LLVM exactly. Every rule below was measured against clang 21.

Flattening. An argument or return value is flattened in order into its scalar and vector elements. Struct and array nesting is removed, padding is not passed, and each element keeps its own type (`{ i32, i32 }` is two `i32`s, not one eightbyte).

Classes:

- Integer: `i1` through `i64` and pointers.
- Float: `float` and `double`.
- Vector: the 128-bit types. A 256-bit vector is two 128-bit halves, low half first, each a vector element. This is LLVM's lowering without AVX (`<8 x i32> %a, <8 x i32> %b` arrive in `xmm0`/`xmm1` and `xmm2`/`xmm3`).

Arguments:

- Integer elements take `rdi`, `rsi`, `rdx`, `rcx`, `r8`, `r9`. Float and vector elements take `xmm0`–`xmm7`.
- An element whose class has no register left goes to the next stack slot. One aggregate can straddle registers and stack: `{ i64, i64 }` after five `i64` arguments is `r9` plus the first stack slot.
- Stack slots start at `%rsp` at the `call` instruction, which is `8(%rsp)` at callee entry. Each element is placed at the next offset aligned to the larger of 8 and its own alignment, and occupies a multiple of 8 bytes.
- `i1`, `i8`, and `i16` arguments are not extended. ritz1 emits no `zeroext` or `signext`, so the upper bits of the register or slot are unspecified. A callee does not rely on them, and a caller does not have to set them.
- `ptr byval(T) align A` takes no register. The caller copies `T` into the stack argument area at the next offset aligned to the larger of 8 and A. The callee's IR pointer is the address of that copy (`byval({ i64, i64, i64 })` has its second field at `16(%rsp)` on entry). When A is more than 16, the caller aligns its outgoing area to A.
- `ptr sret(T)` is an ordinary first argument (`rdi`). The callee returns that pointer in `rax`.
- A `declare` may end in `...`. Definitions are not variadic. A call is lowered from the argument types on the call instruction. When the callee is variadic, `%al` holds the number of vector registers used, 0 to 8.

Returns:

- Integer elements: `rax`, `rdx`, `rcx`, at the element's width (`al`, `dx`, `ecx` for `{ i8, i16, i32 }`).
- Vector elements: `xmm0`–`xmm3`, in order.
- Float elements share that `xmm` sequence, but only `xmm0` and `xmm1`. A float element that finds both taken goes to x87, `st0` then `st1`: a returned `{ double, double, double }` is `xmm0`, `xmm1`, `st0`. The callee loads x87 values with `fldl`/`flds`. The caller pops `st0` and then `st1` with `fstpl`/`fstps`, so the x87 stack is empty at every call boundary.
- Demotion: when any element finds no register, the whole return is demoted. The caller passes a hidden pointer in `rdi`, which shifts the other arguments by one, and the callee writes the value there and returns the pointer in `rax`. `{ i64 x4 }`, `{ double x5 }`, and five `<4 x i32>` are demoted.

Stack alignment: at callee entry `%rsp + 8` is 16-byte aligned, because `call` pushed the return address. At every `call` rllvm emits, `%rsp` is 16-byte aligned, or aligned to the outgoing area's alignment when a `byval` needs more. `alignstack(16)` is that same alignment and adds no realignment code. A `naked` function has no frame; its template keeps its own alignment (both shims do `andq $-16, %rsp` before `call main`).

256-bit vectors at a boundary. Clang's lowering of a 256-bit vector depends on AVX: with `-march=native` on an AVX host, it is one `ymm` register. Freestanding objects are compiled with `-march=native`, so the clang side of a call can disagree with rllvm. rllvm therefore rejects a 256-bit vector, alone or inside an aggregate, in the signature of any non-`internal`/`private` definition, of any `declare`, and of any indirect call. Such a file stays on clang. A file that declares such a function is rejected too, so both sides of the call stay on clang. `internal` and `private` functions may pass 256-bit vectors, since only rllvm code calls them.

- `win64cc` is an error. It appears on the UEFI bins, which stay on clang.
- A function with `noredzone` does not address memory below `%rsp`. Any other function may use the 128-byte red zone. The kernel IR carries `noredzone` on every non-naked function. The Linux and Harland shims are `naked` and have no prologue.
- `sspstrong` loads the global `__stack_chk_guard`, stores it in the frame, and on mismatch calls `__stack_chk_fail`. This is the `*-none-*` global, which is what the kernel defines. Hosted IR does not carry `sspstrong` today. The attribute is still in the subset, because the kernel emits it.
- `naked`: no prologue and no epilogue. The body is inline asm and then `unreachable`.

## LLVM IR subset

v1 parses and lowers the IR ritz1 emits, plus the two hand-written shims. Anything outside this subset is an error naming the construct. That file stays on clang. Growing the subset is a later change with a corpus entry, not a silent accept. The subset is closed.

### Module

`target triple`, optional `target datalayout` (empty or absent only), `comdat any`, comments, and `; ModuleID`. Named and literal struct types, packed structs, arrays `[N x T]`, vectors. Metadata (`!dbg` and other `!` records) is skipped. v1 does not emit DWARF from it.

Types: `i1`, `i8`, `i16`, `i32`, `i64`, `float`, `double`, `ptr`, `i8*`, `i8**`, `[1 x i8]*`, `[N x T]`, structs, `<16 x i8>`, `<8 x i16>`, `<4 x i32>`, `<2 x i64>`, `<8 x i32>`, `<4 x i64>`.

Typed pointers are the same 64-bit value as `ptr`. The shims spell them `i8*`, `i8**`, and `[1 x i8]*`: `@__ritz_envp` is `weak global i8**`, `main` takes `i8**` for `argv` and `envp`, `ritz_platform_page_map` returns `i8*` (`inttoptr` to `i8*`, `ret i8*`), `ritz_platform_page_unmap` and `ritz_platform_fatal` take `i8*`, and `ptrtoint` of `@__ritz_platform_nl` takes `[1 x i8]*`. ritz1's own emission of those hooks uses opaque `ptr`. An address space on either spelling is an error.

### Instructions

Terminators: `ret`, `br`, `unreachable`.

Memory: `alloca`, `load`, `store`, `getelementptr`, `load volatile`, `store volatile`, `load atomic` / `store atomic` with `seq_cst` and an explicit alignment, `cmpxchg` with `seq_cst seq_cst`, `atomicrmw` of `xchg`, `add`, `sub`, `and`, `or`, `xor` at `seq_cst`, `fence seq_cst`.

Integer, on scalars and on the vector types: `add`, `sub`, `mul`, `udiv`, `sdiv`, `urem`, `srem`, `shl`, `lshr`, `ashr`, `and`, `or`, `xor`. `icmp` with any predicate. `trunc`, `zext`, `sext`.

Float, on `float` and `double`: `fneg`, `fadd`, `fsub`, `fmul`, `fdiv`, `fcmp` with any predicate, `fptrunc`, `fpext`, `sitofp`, `uitofp`, `fptosi`.

Casts and aggregates: `bitcast`, `inttoptr`, `ptrtoint`, `extractvalue`, `insertvalue`, `extractelement`, `insertelement`, `shufflevector`, `select`, `phi`. `undef` as an `insertvalue` base. Constants: integers, floats, `null`, `zeroinitializer`, `c"..."` bytes, aggregate constants, `getelementptr` in a constant initializer.

`call`, including `call asm sideeffect`. Parameter attributes that appear: `sret`, `byval`. Function attributes that appear: `alignstack(16)`, `"no-builtins"`, `sspstrong`, `noredzone`, `naked`, `cold`, `noinline`, `inlinehint`, `alwaysinline`, `noreturn`, `nounwind`, `"target-cpu"="x86-64"`, `"target-features"` whose members are a subset of `+aes`, `+pclmul`, `+sha`.

Not in the subset, and an error if present: `switch`, `invoke`, `landingpad`, `resume`, `indirectbr`, `catchswitch`, `frem`, `fptoui`, `freeze`, `va_arg`, `atomicrmw` ops other than the six named, orderings other than `seq_cst`, address spaces, `i128`, `x86_fp80`, `win64cc`, and every intrinsic not named in the next section. The file that contains one stays on clang.

### Intrinsics

| Intrinsic | Lowering |
|---|---|
| `llvm.x86.sha256rnds2` | `sha256rnds2` |
| `llvm.x86.sha256msg1` | `sha256msg1` |
| `llvm.x86.sha256msg2` | `sha256msg2` |
| `llvm.x86.aesni.aesenc` | `aesenc` |
| `llvm.x86.aesni.aesenclast` | `aesenclast` |
| `llvm.x86.aesni.aesdec` | `aesdec` |
| `llvm.x86.aesni.aesdeclast` | `aesdeclast` |
| `llvm.x86.aesni.aesimc` | `aesimc` |
| `llvm.x86.aesni.aeskeygenassist` | `aeskeygenassist` |
| `llvm.x86.sse2.psad.bw` | `psadbw` |
| `llvm.x86.pclmulqdq` | `pclmulqdq` |
| `llvm.trap` | `ud2`. The call is followed by `unreachable`, as `emit_unwrap_tag_trap` writes it. |
| `llvm.{s,u}{add,sub,mul}.with.overflow.iN` | `{ iN, i1 }`: the result and the overflow flag. `N` is 8, 16, 32, or 64. Signed overflow is `OF`; unsigned is `CF`. Multiply at `i8` uses the one-operand `imul`/`mul` on `al`, since x86 has no two- or three-operand 8-bit multiply. Unsigned multiply at every width uses one-operand `mul`. |
| `llvm.fshl.iN` / `llvm.fshr.iN` | Three `iN` operands, `N` in 8, 16, 32, 64. The count is taken modulo `N`, and a count of 0 returns the first operand (`fshl`) or the second (`fshr`). ritz passes the same value as the first two (a rotate), lowered to `rol`/`ror` by `%cl`, which reduce the count modulo the width at every size. Distinct operands are a funnel shift. At 32 and 64 bits that is `shld`/`shrd`, which mask the count to the width. At 16 bits the count is reduced modulo 16 first, because `shld`/`shrd` on a 16-bit operand leave counts 16 to 31 undefined. At 8 bits there is no `shld`: the two bytes are combined into 16 bits, shifted by the count modulo 8, and the result byte is extracted. |
| `llvm.ctlz.iN` / `llvm.cttz.iN` | `(iN, i1)`. The `i1` is `false` in the IR ritz emits: a zero input returns `N`, not poison. `bsr`/`bsf` leave the destination undefined on zero, so the zero case is an explicit test (`cmov` of `N`). At 8 and 16 bits the operand is zero-extended first, and `ctlz` subtracts the extra width. No `lzcnt`/`tzcnt`, which are not baseline. No `__clz*` / `__ctz*` compiler-rt call. |
| `llvm.ctpop.iN` | Population count, `N` in 8, 16, 32, 64. An inline shift-and-mask sequence, because `popcnt` is not baseline x86-64. No `__popcount*` compiler-rt call. |
| `llvm.bswap.iN` | `N` is 16, 32, or 64. `bswap` at 32 and 64. At 16 bits it is `rolw $8`, because `bswap` has no defined 16-bit form. ritz does not emit `i8` (`swap_bytes` of a byte is the identity). |
| `llvm.fabs.f32` / `llvm.fabs.f64` | Clear the sign bit (`andps` / `andpd`). No libcall. |
| `llvm.fptosi.sat.iN.f32` / `.f64`, `llvm.fptoui.sat.iN.f32` / `.f64` | Saturating convert. `N` is 8, 16, 32, or 64. Out of range becomes the integer minimum or maximum. NaN becomes 0 (an unordered `ucomis*` test). The range check compares the float against the bounds before converting, so `cvtt*2si`'s out-of-range value never reaches the result. `fptoui.sat.i64` subtracts 2^63 before converting values at or above 2^63. |

The x86 rows are the intrinsics ritz1 declares (`emit_x86_simd_intrinsic`) and tags with `"target-features"`. `llvm.x86.sse2.psad.bw` is baseline x86-64 and carries no feature tag. A function tagged `+sha`, `+aes`, or `+pclmul` is lowered with that feature even when the host lacks it. rllvm does not consult the host CPU.

The scalar rows are the other `llvm.*` calls ritz1 emits: unwrap (`emitter_call_lower.ritz`), checked `+` `-` `*` (`emitter_expr_arith.ritz`), `rotl` / `rotr` / `clz` / `ctz` / `popcnt` / `swap_bytes` and `abs` (`emitter_expr_call.ritz`), and `x as iN` from a float (`emit_float_to_int_sat`).

`llvm.memcpy`, `llvm.memset`, `llvm.memmove`, `llvm.lifetime.*`, `llvm.dbg.*`, `llvm.floor`, `llvm.ceil`, and any other `llvm.*` name are errors. ritz1 does not emit the memory intrinsics; codegen of them introduces libc or compiler-rt calls. A `.ll` that contains one stays on clang.

### Inline asm

`emitter_asm.ritz` lowers every `asm x86_64` block, and the hand-written helpers lower their own. v1 accepts that IR. razm parses the template. rllvm does not encode it a second way, and rllvm does not read `.s` files.

The call:

```
%reg = call <type> asm sideeffect "<template>", "<constraints>"(<operands>)
```

`<type>` is `void`, one of `i8` / `i16` / `i32` / `i64` / `ptr`, or a literal struct of those when the block has several outputs. `xgetbv` returns `{ i32, i32 }` (`emitter_expr_call.ritz`). `cpuid` (`cryptosec/lib/cpuid.ritz`) returns four `i32`s. Each output is stored back with `extractvalue` when there is more than one.

AT&T. The template is an LLVM string constant. Lines are separated by `\0A` escapes (ritz1) or by literal newlines inside the quotes (both `runtime/ritz_start*.ll` shims), and the parser accepts both. `$$` is a literal `$`. Operand placeholders are `$N` and `${N}`. A numeric local label `N:` and a reference `Nb` / `Nf` are in the template (`test_asm.ritz`). A `#` starts an AT&T comment that runs through the end of that template line. The comment is not a mnemonic. The Harland shim's `_start` template (`ritz_start.harland.x86_64.ll`) opens with three such lines.

Constraints, all of them:

| Kind | Form | Where |
|---|---|---|
| Pinned output | `={reg}` | `emitter_asm.ritz` |
| Early-clobber pinned output | `=&{reg}` | `emitter_print.ritz`, `emitter_expr_arith.ritz` |
| Unpinned output | `=&r` | `emitter_asm.ritz` |
| Pinned input | `{reg}` | `emitter_asm.ritz` |
| Tied `inout` | the output's number | `emitter_asm.ritz` |
| Unpinned input | `r` | `emitter_asm.ritz` |
| Clobber | `~{reg}`, `~{memory}`, `~{dirflag}`, `~{fpsr}`, `~{flags}` | `emitter_asm.ritz` and the hand-written templates |

`reg` in a constraint is a GPR: `rax`/`eax`/`ax`/`al` through `r15`, and `sil`/`dil`/`bpl`/`spl`. `xgetbv` pins `ax` and `dx`. Integer and pointer operands only. The two shims and `emitter.ritz` pin `syscall` with `={rax}`, not `=&{rax}`, and their clobber lists are `~{reg}` and `~{memory}` only.

After placeholder substitution the operand forms are a GPR, `%cr2`, `%cr3`, `*%reg` (`jmpq *%rax`), an immediate, `(%reg)`, `disp(%reg)`, `disp(%base,%index)`, `disp(%base,%index,scale)`, a bare symbol (`call main`), and `symbol(%rip)`. A `symbol(%rip)` in the template is `R_X86_64_PC32` in every code model. A `call symbol` or `jmp symbol` in the template is `e8`/`e9` rel32 with `R_X86_64_PLT32` in every code model, including large. That is what clang's integrated assembler writes for the same template. rllvm does not rewrite a template into the code model's address form: the large model's `movabs` and indirect call is a compiler sequence, and a literal `call symbol` cannot become one by changing its relocation. In the large model the linker range-checks the rel32. It always fits within one image smaller than 2 GiB, which is every large-model bin (`indium/user/linker.ld` places the whole image from 4 GiB). A target out of range is a link error, not a silent truncation.

Mnemonics in a template are the razm set. The ones these blocks and the shims actually contain:

`addq`, `addl`, `andq`, `call`, `clflush`, `cli`, `cpuid`, `decq`, `hlt`, `inb`, `inl`, `invlpg`, `inw`, `jmpq`, `jnz`, `leaq`, `lfence`, `lidt`, `ltr`, `mfence`, `movb`, `movl`, `movq`, `movw`, `nop`, `nopl`, `outb`, `outl`, `outw`, `pause`, `popq`, `pushfq`, `rdmsr`, `rdtsc`, `retq`, `sfence`, `shlq`, `sti`, `syscall`, `wrmsr`, `xgetbv`, `xorl`, `xorq`.

That includes the kernel and userspace blocks, not only the shims: port I/O (`harland/boot_abi/src/portio.ritz`, `harland/kernel/src/io.ritz`), `cpuid` and `xgetbv` (`cryptosec/lib/cpuid.ritz`), `pause`, `cli` / `hlt` / `sti`, `pushfq` / `popq`, `lfence` / `sfence`, `rdtsc`, `rdmsr` / `wrmsr`, `invlpg`, `clflush`, `lidt`, `ltr`, and the `syscall` blocks in `ritzlib/sys.ritz`. A mnemonic outside the razm set is an error, and that `.ll` stays on clang. `jmpq` occurs in the UEFI boot source; the file is rejected earlier by the Windows triple, and the mnemonic is still in the set.

## Optimization bar

Hosted objects are produced by `clang -c -O2`. Freestanding objects are produced with no optimization flag, which is clang's `-O0`.

v1's lowering is the `-O0` lowering for every profile, including hosted. `-O2` on the command line does not turn on LLVM's pass pipeline. rllvm does not run inlining, SROA, GVN, LICM, or vectorization. `available_externally` bodies are dropped, not inlined.

That is the bar against `-O2`: the hosted oracle is still a `clang -O2` object, and the rllvm object must match it in behavior after linking and running. It does not have to match it in size, instruction selection, or bytes. Freestanding's oracle is `clang -c` with the freestanding flags and no `-O` flag. Those entries are link tests. The freestanding compiler does not optimize.

`"no-builtins"` is preserved by not running a pass that invents libc calls, and by not emitting those calls in the lowerer. `-ffreestanding` is not the mechanism.

## Equivalence bar

The oracle is link-and-behavior on the fixed corpus. For each corpus entry, rllvm's object and clang's object are linked with the same linker, the same shim, and the same extra objects. Every entry compares link status. Every hosted entry marked "run" in the [table](#tests) executes twice, once as the oracle binary (clang's `-O2` objects, clang-built shim, the same razm object, same `clang -nostdlib` link) and once with rllvm's objects in their place. Exit status and stdout bytes must match. Until razm's corpus is green, the extra object is built with `as --64`.

Every entry also checks relocation types. Each relocation in rllvm's object has a type that the entry's profile row in [Relocations](#relocations) allows for that use. Data initializers are `R_X86_64_64`, and references to `.rodata` constants use the profile's internal-data type. The check is against the table, not against clang's object, because clang at `-O2` folds away references that an `-O0` lowering keeps.

Semantics are proven by running code where the host can run it. Disassembly checks are kept only for what the host cannot execute: privileged instructions, port I/O, `ud2`, and SHA/AES/CLMUL on a host that may lack them.

Object files are not compared with `cmp`. Text sections are not compared. A byte-identical `.o` against `clang -O2` is not a goal. Clang's instruction selection at `-O2` and an `-O0` lowerer do not produce the same bytes, and the pipeline's hosted path is `-O2`.

## Tests

rllvm's tests are a fixed `.ll` corpus and a driver that runs clang and the existing linker. They are not a column of `matrix-full`, and they do not run `./rz build --all`. `ritz1_selfhosted` may be used by a person to regenerate a fixture. The regenerated text is committed. CI does not invoke ritz1, ritz0, or the stack matrix to test rllvm.

Corpus path, when the implementation exists: `projects/rllvm/tests/corpus/`. Each entry is a frozen `.ll` plus a one-line profile: `hosted`, `small-pic`, `kernel`, or `large`. Clang is the oracle, invoked with that profile's flags from the table above.

| Entry | Profile | Clang flags | Link | Run |
|---|---|---|---|---|
| `hosted/hello.ll` | hosted | `-c -O2 -fPIC -ffreestanding -fno-builtin` | `clang -nostdlib`, the clang-built `ritz_start.x86_64.o`, the rllvm object, and one razm object | yes |
| `hosted/asm.ll` | hosted | same | same shape as `hello`, link only; `objdump -d` must show each mnemonic in the closed set | no |
| `hosted/simd.ll` | hosted | same | link only; `objdump -d` must show each x86 row: `sha256rnds2`, `sha256msg1`, `sha256msg2`, `aesenc`, `aesenclast`, `aesdec`, `aesdeclast`, `aesimc`, `aeskeygenassist`, `psadbw`, `pclmulqdq` | no |
| `hosted/intrin.ll` | hosted | same | link only; `objdump -d` must show `ud2`, `bswap`, `andps`, `andpd`; the object references none of `__clz`, `__ctz`, `__popcount`, `memcpy`, `memset`, `memmove`, `floor`, `ceil` | no |
| `hosted/intrin_run.ll` | hosted | same | same shape as `hello` | yes |
| `hosted/asm_run.ll` | hosted | same | same shape as `hello` | yes |
| `hosted/abi_a.ll` + `hosted/abi_b.ll` | hosted | same | `hello` shape, linked twice: `a` from rllvm with `b` from clang, then `a` from clang with `b` from rllvm | yes, both links |
| `hosted/comdat_a.ll` + `hosted/comdat_b.ll` | hosted | same | `hello` shape with both objects, linked three times: both rllvm, both clang, one of each | yes; `nm` shows one definition of each comdat function |
| `hosted/weak_strong.ll` | hosted | same | `hello` shape with the rllvm-built shim (weak `ritz_platform_fatal`) and this object's strong definition | yes; the strong definition runs |
| `hosted/shim.ll` | the Linux shim, copied from `runtime/ritz_start.x86_64.ll` | `clang -c` with no `-O2` and no `-fPIC`, as `ensure_runtime_object` | linked into `hello` in place of the clang-built shim, once | yes, same stdout and status as the clang-built shim |
| `freestanding/pic.ll` | small PIC, triple `x86_64-unknown-none` | `-c --target=x86_64-unknown-none -ffreestanding -fno-builtin -march=native -msha -fPIC` | `ld.lld --pie --no-dynamic-linker` with the clang-built `ritz_start.harland.x86_64.o` and one razm object | no |
| `freestanding/kernel.ll` | kernel, functions carry `noredzone` and `sspstrong` | `-c --target=x86_64-none-elf -ffreestanding -fno-builtin -march=native -msha -mcmodel=kernel -mno-red-zone` | `ld.lld -T` a corpus script whose VMA is `0xFFFFFFFF80000000`, plus one razm object that provides `__stack_chk_guard` and `__stack_chk_fail` | no |
| `freestanding/large.ll` | large, triple `x86_64-unknown-none` | `-c --target=x86_64-unknown-none -ffreestanding -fno-builtin -march=native -msha -mcmodel=large` | `ld.lld -T` a corpus copy of `indium/user/linker.ld`, the script the large-model bins link with | no |
| `freestanding/harland_start.ll` | the Harland shim, copied from `runtime/ritz_start.harland.x86_64.ll` | `clang -c` with no extra flags | linked in `pic.ll`'s link in place of the clang-built shim | no |

Each runnable entry prints its results to stdout and returns a status, so the oracle and the rllvm binary are compared on output, not on code. Every observable value is defined by the IR (no reads of uninitialized memory, no poison), so `-O0` and `-O2` agree.

`hello` is integer arithmetic, a write, and `main`'s return code.

`intrin_run.ll` runs every scalar intrinsic row except `llvm.trap` at every width the row names, on edge values, and prints each result:

- `with.overflow`: 0, 1, -1, the minimum, the maximum, and pairs that overflow by one in each direction.
- `fshl`/`fshr`: as a rotate and as a funnel shift, with counts 0, 1, `N - 1`, `N`, `N + 1`, and `2N - 1`.
- `ctlz`/`cttz`: 0, 1, the top bit alone, and all ones.
- `ctpop`: 0, all ones, and alternating bits.
- `bswap`: at 16, 32, and 64.
- `fabs`: `-0.0`, NaN, and both infinities.
- `fptosi.sat`/`fptoui.sat`: NaN, both infinities, the exact bounds, one ulp past each bound, `-0.0`, and 2^63 for `fptoui.sat.i64`.

`asm_run.ll` runs inline asm that is safe on the host (`addq`, `xchgq`, `leaq`, `shlq`, `xorq`, `bswap` through a template, `rdtsc` only for its constraints). It covers a tied `inout`, an early-clobber unpinned output (`=&r`) beside inputs that would otherwise share its register, pinned inputs and outputs, a multi-output literal-struct return, and `$$`.

`abi_a.ll` and `abi_b.ll` call each other in both directions. Every [ABI](#abi) rule has a call:

- an aggregate straddling the last register and the stack, in both classes
- `{ i32, i32 }` and `{ i8, i64, float }` arguments and returns
- returns at each register limit: three integers, two floats, x87 `st0` and `st1`, four 128-bit vectors
- each demotion
- `byval` at align 8 and align 32
- `sret`
- an `internal` 256-bit vector call inside each file
- a variadic call
- a callee that checks `%rsp` alignment at entry through inline asm

Each side prints what it received.

`comdat_a.ll` and `comdat_b.ll` each define the same `linkonce_odr` and `weak_odr` functions in comdats, the way ritz1 emits them, and both call them. The link must succeed with one copy kept.

`weak_strong.ll` defines a strong `ritz_platform_fatal` that exits with status 7 and calls it. Linked with the rllvm-built shim, whose definition is weak, the binary exits 7.

`asm.ll` is one block per mnemonic in the closed set. It includes a four-`i32` `cpuid`, a `syscall` constrained `=&{rax}`, a move of `%cr3`, `jmpq *%reg`, the port instructions (`inb`, `inw`, `inl`, `outb`, `outw`, `outl`), and the Linux shim's `addq` / `shlq` / `leaq` / `call` / `symbol(%rip)` sequence. It is not executed: `hlt`, `cli`, and port I/O are not host-safe.

`simd.ll` is not executed. The check is that the object contains each x86 intrinsic's instruction. Running SHA-NI on a host without it would SIGILL, and the build already treats those intrinsics as compile-time, not run-time, requirements.

`intrin.ll` contains every scalar row at every width that row names: `llvm.trap`, all six `with.overflow` ops at `N` of 8, 16, 32, and 64, `fshl` and `fshr` both as a rotate and as a funnel shift, `ctlz` and `cttz` with the `i1` false, `ctpop`, `bswap` at 16, 32, and 64, `fabs.f32` and `fabs.f64`, and all sixteen `fptosi.sat` / `fptoui.sat` combinations. It is not executed (`ud2`). It stays separate from `intrin_run.ll` so the trap never sits in a binary that runs. Its job is the disassembly and the absence of compiler-rt and libc references; `intrin_run.ll` proves the values.

Freestanding entries are link tests. The Harland shim exits with syscall 20, and the kernel VMA is not a Linux mapping, so they are not run on the host. Link success against `ld.lld`, the clang-built shim, and one razm object is the contract those entries prove. Until razm's corpus is green, that object is built with `as --64`.

A UEFI `.ll` is not in the corpus.

The driver lives next to the corpus and shells out to `clang`, `razm` (or `as` until razm is swapped in), and `ld.lld`. It does not import `build_pipeline.py` and it does not build ritz. The rllvm phase runs it with `./rz test rllvm` and no other project. That invocation is not `matrix-full` and not `./rz build --all`.

## Ritz

Later goals write razm, rllvm, and rld in idiomatic Ritz. These rules bind all three.

- String literals are raw strings. A `"..."` literal is a `StrView`. IR text, paths, section names, and symbol names are `StrView` or `String`: a span of bytes plus a length. Callers pass that span. They do not pass a NUL-terminated `*u8`.
- A NUL-terminated `*u8`, including a `c"..."` literal, exists only at a documented FFI boundary (STANDARD.md S-TEXT-1). v1 has no C callee, so v1 has no FFI boundary and no `c"..."`. If a later phase calls a C symbol, that one declaration is the boundary, the comment on it says so, and every call site stays a `StrView`.
- File IO, heap vectors, and formatting come from ritzlib. The ELF writer does not reimplement a vector, a string, or a file layer.
- Failure is `Result` or `Option`. A status `i32` plus an out-parameter is not an API.

Comments stay short. A module or a type may carry a comment that states its purpose. A field may carry a brief note on the same line. A comment is not a narrative: it does not tell the story of a change, name a task, or restate the code. Git history is the record.

## UEFI

UEFI is deferred. The first compiler does not write COFF, does not lower `win64cc`, and does not speak `lld-link`.

Today those bins (`bootx64`, `hwinv`, target `x86_64-unknown-uefi`) compile with `--target=x86_64-unknown-windows-gnu -fshort-wchar -mno-red-zone -fno-stack-protector -ffreestanding` and link with `lld-link /subsystem:efi_application /entry:<entry>`. They stay on that path. rllvm exits non-zero if asked for a Windows or UEFI triple, or if the IR contains `win64cc`.

## rld

rld is `projects/rld`. It is implemented after rllvm's objects link and run under the existing linkers. It is not started in the rllvm implementation phase.

### Inputs

- Relocatable ELF64 x86-64 objects: razm's, rllvm's (written by razm), and `clang -c` of either `ritz_start` shim. An object `as --64` already produced still links.
- A GNU linker script, in the subset [below](#linker-scripts).
- Every allocated input section, under the name the object gave it. razm objects contribute `.multiboot`, `.boot`, `.boot.data`, `.boot.bss`, and `.ap_trampoline` (`projects/harland/kernel/boot.s`, `ap_trampoline.s`). rld does not drop a section because rllvm did not invent the name.
- The entry symbol. With no script, the entry is `_start`. With a script, the entry is the script's `ENTRY`.

rld does not garbage-collect sections (the pipeline passes no `--gc-sections`) and does not merge strings. A `SHN_COMMON` symbol is an error; no producer in the tree emits one.

rld relaxes `R_X86_64_GOTPCRELX` and `R_X86_64_REX_GOTPCRELX` exactly as `ld.lld` does. In an executable, a GOT load of a symbol defined in the image becomes a direct `lea` (or the direct form of the instruction), and no GOT entry is made for it. This is required, not an optimization. ritz1 marks no symbol `dso_local`, so every external data reference arrives as a GOT load. Unrelaxed, each would need a GOT entry with a load-time `R_X86_64_RELATIVE`, which the Harland loader does not apply (see [Outputs](#outputs)). Relaxed, the image has no such entries, as with `ld.lld` today.

### Linker scripts

The scripts are `harland/kernel/linker.ld` and indium's `user/linker_pie.ld` (33 bins), `linker_pie.ld` (3), `user/linker.ld` (2, the large-model bins), `user/user.ld`, and `user/linker_spawned.ld`. `ENTRY` is `_start` in the kernel script, `linker_pie.ld`, and `user/linker.ld`, and `main` in `user/user.ld` and `user/linker_spawned.ld`. `harland/boot/linker.ld` belongs to the UEFI bin and is not an rld input.

Accepted, and nothing else:

- Top level: `OUTPUT_FORMAT(elf64-x86-64)`, quoted or not; `OUTPUT_ARCH(i386:x86-64)`; `ENTRY(sym)`; `NAME = expr;`; `PROVIDE(NAME = expr);`; one `SECTIONS { }`.
- In `SECTIONS`: `. = expr;`, `NAME = expr;`, output section statements, and `/DISCARD/ : { patterns }`.
- An output section statement is `NAME [ALIGN(n)] [(NOLOAD)] : [AT(expr)] { items }`. Items are `NAME = .;`, an input pattern `*(pat pat ...)`, `KEEP(*(pat ...))`, and `*(COMMON)`.
- A pattern is a literal section name or a name ending in `*` (`.text.*`, `.note*`, `.eh_frame*`, `.text*`). The file part is always `*`.
- Expressions: integers (decimal, `0x`, and a `K` or `M` suffix, as in `4K`), symbols, `.`, `+`, `-`, `ALIGN(n)`, `ADDR(section)`.

Semantics, matching `ld.lld`:

- Placement is first match. Output section statements are visited in script order, and within each statement its patterns in order. Each pattern claims every input section it matches that no earlier pattern claimed, in command-line object order and section order within each object. So in the kernel script `.boot`'s `*(.boot .boot.*)` claims `.boot.data` and `.boot.bss`, which leaves the later `.boot.data` and `(NOLOAD) .boot.bss` statements empty. `ld.lld` and GNU `ld` both do this today, and rld does the same.
- `/DISCARD/` drops what its patterns claim, under the same first-match order.
- An allocated orphan (matched by no pattern) is placed after the last output section with the same flags (alloc, write, exec, `NOBITS`), or at the end of the image when no such section exists. rld prints one line per orphan. `.eh_frame` from clang objects under `user/linker.ld` is the orphan the tree has today.
- `KEEP` is accepted and changes nothing, because nothing is collected.
- `(NOLOAD)` makes the output section `SHT_NOBITS`. It takes address space and no file bytes.
- `AT(expr)` sets the section's load address. A later section with no `AT` keeps the same VMA-to-LMA offset as the section before it. With no `AT` anywhere, load address equals VMA.
- `.got`, `.got.plt`, `.rela.dyn`, and `.rela.plt` patterns name sections the linker makes. rld puts its GOT in the output section whose pattern names `.got`, and its dynamic relocations in the one that names `.rela.dyn`. Without such a pattern, they are orphans.
- `PROVIDE(sym = expr)` defines `sym` only when an input references it and no input defines it.
- Segments: a new `PT_LOAD` starts when permissions change or when the VMA-to-LMA offset changes. `p_paddr` is the load address, `p_align` is `0x1000`, and file offset equals VMA modulo `0x1000`. A `NOBITS` section at the end of a segment adds to `p_memsz` only.

### Outputs

| Output | Replaces | Shape |
|---|---|---|
| Linux executable | `link_hosted`: `clang` or `gcc`, `-nostdlib`, the runtime object first, then module objects. The link line also passes `-march=native`, `-msha`, `-O{level}`, optional `-g`, optional `-flto`. On plain ELF objects those flags do not change the file `clang` writes (`-flto` still accepts a non-bitcode `.o`). rld does not take them. | ET_DYN, `DF_1_PIE`, `PT_INTERP` `/lib64/ld-linux-x86-64.so.2`, entry `_start`, no `DT_NEEDED`. This is the file `clang -nostdlib` writes on the hosted toolchain (clang 21, default PIE). It runs on Linux. |
| Freestanding PIE | `link_freestanding_elf` for a `pic` bin: `ld.lld --pie --no-dynamic-linker`, with `-T` (every `pic` bin has a script) | ET_DYN, `DF_1_PIE`, no `PT_INTERP`, `PT_DYNAMIC` |
| Freestanding executable with a script | `link_freestanding_elf` with `-T` and no `pic` (the kernel, `minimal_syscall`, `portable_getpid`) | ET_EXEC at the script's addresses, entry from `ENTRY`, no `PT_INTERP`, no `PT_DYNAMIC` |
| Freestanding executable with no script | `link_freestanding_elf` with neither (`rzrz`, `rzsh.linux`, target `x86_64-unknown-linux-gnu`) | ET_EXEC, base `0x200000`, then read-only, executable, and writable output sections, each starting a new `PT_LOAD` on a new page, entry `_start`. This is `ld.lld`'s default layout without its RELRO split; exact addresses are not part of the contract. These bins run on Linux with no interpreter. |

Load-time relocations. Both PIE outputs write what `ld.lld` and `clang -nostdlib` write today, which was checked on an initialized pointer (`@tab = global ptr @x`):

- one `R_X86_64_RELATIVE` per absolute address in writable data, in `.rela.dyn`
- `DT_RELA`, `DT_RELASZ`, `DT_RELAENT`, `DT_RELACOUNT`, `DT_SYMTAB`, `DT_SYMENT`, `DT_STRTAB`, `DT_STRSZ`, `DT_GNU_HASH`, `DT_DEBUG`, and `DT_FLAGS_1` with `DF_1_PIE`, plus `DT_HASH` in the freestanding PIE (the hosted link is `clang`'s `--hash-style=gnu`). The symbol tables behind them are empty.
- no `DT_NEEDED`

A GOT entry that survives relaxation, for a symbol defined in the image, is an `R_X86_64_RELATIVE` too. A symbol still undefined after the link is an error; rld writes no `GLOB_DAT` or `JUMP_SLOT`.

Who applies those relocations:

- Hosted: `ld.so`, named by `PT_INTERP`.
- Freestanding PIE: the Harland loader, which loads ET_DYN at `USER_IMAGE_BASE` (`0x100000000`). Today that loader (`harland/kernel/src/loader/`) applies the load bias to segments and the entry point, but it applies no `.rela.dyn` entries. So an initialized pointer in a Harland PIE holds its link-time value, not its loaded address, whichever linker wrote the file. rld writes the relocations either way. Applying them is a Harland loader change, outside this document.

rld does not produce PE/COFF. UEFI stays on `lld-link`.

### CLI

```
rld --hosted [-o OUT] OBJ...
rld [-o OUT] [--pie --no-dynamic-linker] [-T SCRIPT] OBJ...
```

The mode is explicit:

- `--hosted` is the Linux executable. It replaces `link_hosted`, whose runtime object stays the first input. It takes no `-T` and no `--pie`.
- Without `--hosted`, the link is freestanding. `--pie --no-dynamic-linker` is the freestanding PIE, `-T` alone is the scripted executable, and neither is the no-script executable.
- `--pie` without `--no-dynamic-linker`, `--no-dynamic-linker` without `--pie`, and `--hosted` with either `--pie` or `-T` are errors. A freestanding link that wants an interpreter is not a mode the tree has.

### rld tests

rld's tests reuse the rllvm and razm corpora. Each link is done twice, once by today's linker and once by rld:

- Hosted entries that run under both linkers must match on stdout and exit status.
- Kernel: the seven kernel `.s` objects plus `freestanding/kernel.ll`, through the real `harland/kernel/linker.ld`. The two outputs must agree on:
  - entry address
  - the `PT_LOAD` table: virtual address, physical address, permissions, file size, memory size
  - section-to-segment mapping
  - the bytes of every segment
  - the Multiboot2 header's file offset, within the first 32 KiB and 8-byte aligned

  rld relaxes GOT loads as `ld.lld` does, so segment bytes compare exactly, with no masks.
- Freestanding PIE: `freestanding/pic.ll` through `user/linker_pie.ld`, with the initialized-pointer fixture above. The two outputs must agree on the `PT_LOAD` table, on the dynamic tags present, and on the multiset of dynamic relocations as (offset, type, addend).
- No-script executable: a corpus entry in the `rzrz` shape, linked both ways and run on Linux. Output and status must match.

rld's tests do not add a stack-matrix column.

## Phases

1. **This document.** No compiler, no assembler, no linker, no `ritz.toml`, no `rz` wiring.
2. **razm.** Implement the text dialect, the ELF writer, and the `.s` corpus. `as --64` is the oracle on Linux. `clang -c` still compiles `.ll`. `as` still builds the tree. Tests are `./rz test razm` only. Not a `matrix-full` column.
3. **rllvm.** Implement the IR subset on top of razm. razm encodes every instruction, including inline asm. Tests are the `.ll` corpus. Not a `matrix-full` column.
4. **Swap the ELF steps.** `assemble_objects` calls razm. `compile_ll_to_obj` and `ensure_runtime_object` call rllvm for the ELF profiles. UEFI still calls clang and `lld-link`. This phase edits `build_pipeline.py`. It waits until phases 2 and 3 are green, and it is a separate change. Its entry criteria, routing, and cache rules are in [Cutover](#cutover).
5. **rld.** Implement the linker above. Then `link_hosted` and `link_freestanding_elf` call it. UEFI still calls `lld-link`.
6. **Run the tools on Indium.** razm first: Indium has no GNU `as`, and the kernel `.s` files are its input. rllvm after phase 3 is green. Out of scope until phases 2–5 produce objects and executables on Linux. Harland-targeted objects are in scope from phase 2; executing either program under Indium is not.

## Cutover

Phase 4 rules. Routine razm and rllvm work never runs these; they apply to the one change that edits `build_pipeline.py`.

### Coverage before the switch

The frozen corpus stays the routine test. Before the switch, a survey runs rllvm on real emitted IR for every ELF profile:

- hosted: ritzlib and test modules
- kernel: `harland`
- small PIC: an indium `pic` bin
- large: `minimal_syscall`

`./rz test rllvm --survey DIR` runs rllvm on every `.ll` under `DIR`, which is the IR a `--debug` build keeps under `build/`. It builds nothing itself. For each file it reports accepted, or the construct outside the subset. The cutover change records the counts per profile. Every rejected construct is either added to the subset, with a corpus entry, or listed in the change with the files it keeps on clang.

### Routing unsupported input

Clang fallback is intended, and it is explicit:

- rllvm exits 0 on success. It exits 2 when the input is outside the subset, and stderr names the file, line, and construct. It exits 1 on any other failure.
- On exit 2, the pipeline compiles that file with clang using the same flags and prints one line naming the file and construct. Exit 1, a signal, or a timeout is a build failure with no fallback, under AGAST #1731's rule that object failures are never silent.
- The 256-bit-vector boundary rule in [ABI](#abi) makes the fallback safe: a signature that clang and rllvm lower differently keeps both sides of the call on clang.
- `RITZ_OBJ_PRODUCER=clang` sends every file to clang. It is the switch to back out. `assemble_objects` has the same switch, `RITZ_ASM_PRODUCER=as`, and no per-file fallback: razm accepts the whole corpus or the switch stays off.
- `ensure_runtime_object` routes the shims the same way.

### Cache identity

A warm build must exercise the selected tool, so the producer is part of every cache key:

- `cas_module_key` adds `producer` to its flags. With routing on, that is the sha256 of the rllvm binary, the sha256 of the razm library it was built with, and the first line of `clang --version`, the last because exit 2 sends a file to clang. With `RITZ_OBJ_PRODUCER=clang`, it is clang's line alone. A hash, not a version string: during fast iteration the binary changes far more often than any version number.
- `freestanding_provenance` records the razm binary's sha256 next to each `.s` file, so a rebuilt razm relinks.
- `ensure_runtime_object` keeps its mtime check and adds a stamp file, `<obj>.producer`, holding the same producer identity. A missing or different stamp rebuilds the shim. The object is still built into a private temp file and published with `os.replace`. The stamp is written after the object is replaced, so a concurrent reader at worst sees a new object with an old stamp and rebuilds it again, and never sees an old object with a new stamp.
- `compile_ll_to_obj` keeps its cleanup: a failed compile, by rllvm or by the clang fallback, unlinks the partial object. rllvm runs under the same timeout and address-space bounds as clang.

## Out of scope

- Byte-identical objects against `clang -O2`.
- A full LLVM IR language, other architectures, debug info, LTO.
- A general GNU `as`. razm assembles the dialect in this document, not every gas directive.
- Editing the ritz1 emitter or the IR it emits.
- UEFI COFF in rllvm or rld.
- Registering rllvm on the stack matrix, or requiring `./rz build --all` for an rllvm change.
