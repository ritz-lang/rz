# LARB Review: Cryptosec

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Cryptosec is a large, well-structured cryptography library implementing AES, ChaCha20, SHA-256/512, RSA, ECDSA (P-256, Ed25519), X25519, TLS 1.3, X.509, and related primitives. The test suite is comprehensive and correctly uses `[[test]]` attributes throughout. However, the library has systematic violations in two major areas: pervasive use of `&&` and `||` symbol operators instead of the required `and`/`or` keywords, and heavy use of raw `*T` pointer parameters in lib code that is not purely FFI/unsafe (this is a low-level crypto library but the pattern is architectural, not incidental). One additional critical finding is a `c"..."` string literal in application-level code with a documented workaround comment.

## Statistics

- **Files Reviewed:** 61 (25 lib, 29 test, 1 src/main, 6 tmp/other)
- **Total SLOC:** ~27,100
- **Issues Found:** 4 (Critical: 1, Major: 2, Minor: 1)

## Critical Issues

### CRIT-1: `c"..."` String Literal in Application Code

**File:** `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/tls13_handshake.ritz` line 732

```ritz
# Note: Using c"..." for now as method call on literal has codegen bug
let ctx: *u8 = c"TLS 1.3, server CertificateVerify"
```

The `c"..."` prefix is old syntax. Per the spec, this should be `"TLS 1.3, server CertificateVerify".as_cstr()`. The comment acknowledges a compiler bug as the reason for the workaround, but this is application-level string handling in a library function — not an FFI boundary where `c"..."` would be more acceptable. This is the only occurrence of the old string prefix across the entire codebase (all other string literals are correctly bare `"..."` or use `.as_ptr()`).

**Required fix:**
```ritz
let ctx: *u8 = "TLS 1.3, server CertificateVerify".as_cstr()
```

## Major Issues

### MAJ-1: Systematic Use of `&&` and `||` Instead of `and`/`or`

**Severity:** Major — affects code across nearly every file in the project.

The spec requires keyword operators (`and`, `or`, `not`) instead of symbol operators (`&&`, `||`, `!`). Cryptosec uses `&&` and `||` extensively throughout both lib and test code. This is the single most widespread issue in the project.

**Affected files (representative sample):**
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/test/test_cpuid.ritz` — 16 occurrences (lines 22, 29, 36, 43, 50, 57, 94, 103, 147, 190, 192, 194, 196, 198, 200)
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/x509_verify.ritz` — lines 133, 160, 183, 223, 253, 257
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/rsa.ritz` — lines 119, 167
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/ca_store.ritz` — lines 114, 190–196, 229, 291
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/pem.ritz` — lines 80, 82, 90, 92, 103, 107, 113, 161, 273–276, 302
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/bigint.ritz` — lines 98, 128, 131, 146, 149, 233, 235, 257, 259, 356
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/p256.ritz` — lines 217, 259, 331, 640, 737, 1489
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/tls13_handshake.ritz` — lines 528, 647
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/hkdf.ritz` — lines 34, 77
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/tls13_kdf.ritz` — lines 113, 138, 159
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/cpuid.ritz` — lines 150, 158
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/base64.ritz` — lines 18, 20, 22, 36
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/chacha20.ritz` — lines 145, 169
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/chacha20_avx2.ritz` — lines 231, 255
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/aes_gcm.ritz` — lines 444, 496, 531, 576
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/test/test_helpers.ritz` — lines 16, 18, 20, 33, 54
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/test/test_poly1305.ritz` — line 135
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/test/test_tls13_record.ritz` — lines 137, 269

**Example correction:**
```ritz
# Wrong:
if result != 0 && result != 1

# Correct:
if result != 0 and result != 1
```

```ritz
# Wrong:
while j < 64 && (i + j) < pt_len

# Correct:
while j < 64 and (i + j) < pt_len
```

Note: Several uses of `||` within comment lines (describing bit concatenation in cryptographic notation like `aad || ciphertext`) are not code and do not require changes.

### MAJ-2: No `impl` Blocks — All Methods Are Standalone Functions

**Severity:** Major — architectural pattern issue affecting the entire library.

The spec prefers `impl Type` blocks for methods over standalone functions. Cryptosec uses zero `impl` blocks across all 61 files. All struct-associated operations are defined as top-level free functions (e.g., `sha256_init`, `sha256_update`, `sha256_final` rather than methods on `Sha256`). While the deprecated `fn Type.method()` syntax is tolerated, the complete absence of `impl` blocks in an application-level library is non-idiomatic.

**Affected:** All struct types — `Sha256`, `Aes128`, `Aes256`, `ChaCha20`, `Poly1305`, `RsaPublicKey`, `BigInt`, `Transcript`, `ClientHello`, `ServerHello`, etc.

**Example (sha256.ritz):**
```ritz
# Current (non-idiomatic standalone functions):
pub fn sha256_init(ctx: *Sha256)
pub fn sha256_update(ctx: *Sha256, data: *u8, len: u64)
pub fn sha256_final(ctx: *Sha256, out: *u8)

# Preferred (impl block):
impl Sha256
    pub fn init(self:& Sha256)
    pub fn update(self:& Sha256, data: *u8, len: u64)
    pub fn final(self:& Sha256, out: *u8)
```

This is a pervasive architectural concern. Given the scale (25 lib files), a phased migration is recommended.

## Minor Issues

### MIN-1: One Commented-Out `@test` Attribute

**File:** `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/test/test_ed25519.ritz` line 959

```ritz
# @test
```

A single commented-out old-style `@test` attribute. This is benign (it is a comment, not active code) but indicates the file may have been partially migrated. The surrounding active test functions correctly use `[[test]]`. No action required beyond awareness.

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | OK | Raw `*T` pointers used throughout, but this is consistent with a low-level crypto library; `@T` reference types used correctly for in-library address-of operations |
| Reference Types (@) | OK | `@x` syntax used correctly and consistently for address-of throughout all files |
| Attributes ([[...]]) | OK | All 502 test attributes across 30 test files use `[[test]]` correctly; one commented-out `@test` is harmless |
| Logical Operators | ISSUE | `&&` and `||` used throughout 18+ files; must be replaced with `and`/`or` |
| String Types | ISSUE | One `c"..."` literal in `tls13_handshake.ritz:732` with workaround comment; all other string usage is correct |
| Error Handling | OK | Consistent use of integer return codes (appropriate for low-level crypto); no nested match anti-patterns found |
| Naming Conventions | OK | Functions: snake_case; Types: PascalCase; Constants: SCREAMING_SNAKE_CASE; all consistent |
| Code Organization | OK | Files well-organized with clear header comments, constants, structs, and functions; tests are in separate `test/` directory |

## Files Needing Attention

**Priority 1 (Critical):**
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/tls13_handshake.ritz` — `c"..."` literal (line 732)

**Priority 2 (Major — `&&`/`||` replacement):**
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/test/test_cpuid.ritz` (16 occurrences)
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/pem.ritz` (many occurrences)
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/bigint.ritz` (many occurrences)
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/p256.ritz` (many occurrences)
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/x509_verify.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/ca_store.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/base64.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/hkdf.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/tls13_kdf.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/cpuid.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/aes_gcm.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/chacha20.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/chacha20_avx2.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/tls13_handshake.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/test/test_helpers.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/test/test_poly1305.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/test/test_tls13_record.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/cryptosec/lib/rsa.ritz`

**Priority 3 (Major — impl blocks):**
- All lib files defining structs with associated functions (all 25 lib files)

## Recommendations

1. **Immediate (before merge):** Fix the `c"..."` literal in `tls13_handshake.ritz:732`. This is a one-line change and is the only critical issue. Either use `.as_cstr()` or work around the compiler bug differently (e.g., assign to a `*u8` from a byte array).

2. **Short-term (next sprint):** Replace all `&&` with `and` and all `||` with `or` in code paths. This affects ~18 files and ~60+ occurrences. A global find-replace is appropriate here since all occurrences in actual code (not comments) need to be updated. Be careful to distinguish `||` used in cryptographic notation comments (e.g., `# aad || ciphertext`) from actual code operators.

3. **Medium-term:** Begin migrating standalone struct-associated functions to `impl` blocks. Prioritize the most frequently used types (`Sha256`, `Aes128`, `Aes256`, `ChaCha20`) as a proof-of-concept migration, then continue through the rest of the library.

4. **No action needed:** The `@` reference syntax, `[[test]]` attributes, naming conventions, string literal usage, and overall code organization are all in excellent shape. The test coverage is thorough and well-structured.
