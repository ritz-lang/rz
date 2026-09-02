# Toolchain requirements

## The pin

**ritz requires clang/LLVM 21.** CI installs and pins exactly that version
(`.github/actions/install-toolchain`, driven by `CLANG_VERSION` in
`.github/workflows/main.yml` and `pr.yml`). Local development should match.

Check what you have:

```sh
clang --version        # expect: clang version 21.x
command -v opt         # needed for RITZ_VERIFY_IR; ubuntu ships it only
command -v llvm-as     # under /usr/lib/llvm-21/bin
```

On Debian/Ubuntu:

```sh
sudo apt-get install -y clang-21 lld-21 llvm-21
export PATH=/usr/lib/llvm-21/bin:$PATH
```

If your distro does not carry 21, use the upstream installer:

```sh
wget -qO- https://apt.llvm.org/llvm.sh | sudo bash -s 21
```

## Why the version is pinned at all

`build.py` shells out to bare `clang` to lower emitted `.ll` files to objects.
Nothing used to say *which* clang. CI got whatever `ubuntu-latest` shipped;
developers got whatever their distro shipped. For compiling ordinary C that
would be a non-issue.

It is an issue here because the regression gate
(`scripts/regression.sh`) is built around **allowlists** of examples a given
compiler is known not to be able to compile — and clang is the component that
decides what "cannot compile" means. An allowlist calibrated against one
LLVM verifier is noise when read by another.

The concrete damage (AGAST #1308). On commit `eef15af`, one machine and one
CI runner, same script:

```
LOCAL  (clang 21.1.8):  Stage 3: 42 passed, 35 skipped
CI     (runner clang):  Stage 3: 50 passed, 35 skipped
```

Eight examples "failed" locally and "passed" in CI. CI additionally printed
**fifteen** `on the allowlist but COMPILES — remove it` warnings on every
green run. Drift detection is the only force that makes the allowlist shrink
rather than accumulate, and a warning that fires unconditionally is a warning
nobody reads. The gate was green and meant steadily less. Two separate
local/CI splits were investigated and misattributed to "environment" before
the cause was understood.

## Why we pinned *forward*, not back

Pinning to the runner's older clang was the available alternative. It would
have been quieter, and it would have been wrong.

The eight examples are not "examples ritz1 cannot compile". They are examples
where **ritz1 emits malformed IR that an older LLVM verifier happens to wave
through.** The captured failure for `tier2_stdlib_16_tr` is:

```
clang linking failed: invalid LLVM IR input:
Instruction does not dominate all uses!
```

That is a genuine dominance violation in ritz1's output — the same family as
the PHI-placement bug fixed in AGAST #1267. A permissive verifier accepting
it does not make the IR valid. It makes a real codegen bug invisible until the
toolchain moves, at which point it resurfaces as an unexplained CI break far
from the commit that introduced it.

So the pin goes forward: to the newest clang we test against, which is the
one that tells the truth. Entries that were hiding as "compiler debt" are now
filed as the codegen bugs they are.

## `RITZ_VERIFY_IR` — the durable version

Pinning makes the allowlist mean one thing everywhere. It does not stop the
meaning from shifting again the next time we bump. `RITZ_VERIFY_IR=1` does:

```sh
RITZ_VERIFY_IR=1 make matrix-full
RITZ_VERIFY_IR=1 ./scripts/regression.sh
```

With it set, `build.py` runs the LLVM verifier (`opt -passes=verify`, or
`llvm-as` as a fallback) over every module we emit *before* handing it to
clang. Invalid IR then fails at the point of emission, naming the offending
function, instead of depending on whichever clang is installed to notice.

CI sets it for both bootstrap gate steps. It is off by default locally so
that ordinary `rz build` does not pay for a verifier pass on every module;
turn it on when you are working on codegen, and always when you are about to
add or remove an allowlist entry.

> **A green `RITZ_VERIFY_IR=1` run is not by itself evidence that anything was
> verified.** When neither `opt` nor `llvm-as` is on PATH, verification
> degrades to a one-line warning and returns success — deliberately, so
> developers who have not opted in are never blocked. Ubuntu installs both
> tools *only* under `/usr/lib/llvm-21/bin`, never as unsuffixed names, so a
> shell without the `export PATH` above takes that branch every time. The
> failure mode is silent and looks exactly like success.
>
> Confirm the verifier is reachable before quoting a run as evidence:
>
> ```sh
> command -v opt || echo 'NOT VERIFIED - put /usr/lib/llvm-21/bin on PATH'
> ```
>
> and check the build output contains no `RITZ_VERIFY_IR set but ... not
> verified` line. CI is protected structurally: `install-toolchain` fails the
> job when the pin does not put a verifier on PATH, precisely so a vacuous
> green cannot be mistaken for a real one.

The rule that follows: **an allowlist entry is a claim about the compiler.**
Before adding one, verify it fails for the reason you think it does. Before
trusting one, check it still fails at all.
