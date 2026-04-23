# Cryptosec Code Review — February 2026

**Scope:** 29 library files, 13,601 lines in `projects/cryptosec/lib/`
**Method:** 4 parallel Sonnet agents reviewing memory safety, code smell, duplicate code, and raw pointer/allocation patterns
**Date:** 2026-02-20
**Branch:** `cryptosec`

---

## Executive Summary

The cryptographic primitives (ChaCha20, Poly1305, X25519, Ed25519, AES, SHA-256/512) are generally solid and correctly implemented. The **TLS 1.3 layer is the danger zone** — it contains remote buffer overflows, missing authentication, and incomplete zeroing of secret material. Code duplication is ~19% (~683 lines), concentrated in SHA/HMAC/AES/RSA families where parameterization would eliminate it cleanly.

### Key Stats

| Metric | Value |
|--------|-------|
| Total library lines | 13,601 |
| Duplicated lines | ~683 (~19%) |
| HIGH severity findings | 10 |
| MEDIUM severity findings | 20 |
| LOW severity findings | 10+ |
| `sys_mmap` calls | 2 (both in `ca_store.ritz`) |
| `sys_munmap` calls | 3 (all correctly paired) |
| Functions over 80 lines | 28 |
| If/else chains → lookup tables | 7 |
| Magic numbers | 24 instances |
| Dead code blocks | 7 |

---

## CRITICAL / HIGH — Fix Before Any Use

### H-1: Remote stack buffer overflow in `tls13_record_decrypt`

**File:** `tls13_record.ritz:148, 168, 172`
**Severity:** HIGH — Remote exploitable

`inner[1024]` receives decrypted TLS records up to 16,400 bytes. `ciphertext_len` comes directly from the wire record header and is bounded only by the TLS record size limit of 16,400 bytes. `aes128_gcm_decrypt` writes `inner_len` bytes into `inner`, which is only 1,024 bytes. Any TLS record larger than ~1,040 bytes will overflow this stack buffer.

**Fix:** Change to `var inner: [16400]u8` or add `if inner_len > 1024 { return -1 }` before the decrypt call.

---

### H-2: Server authentication completely bypassed

**File:** `tls13_handshake.ritz:754-756`, `tls13_client.ritz:493`
**Severity:** HIGH — Full MITM

`certificate_verify_verify` always returns 0 (success) without performing any cryptographic verification:

```ritz
if cv.algorithm == SIG_RSA_PKCS1_SHA256
    var hash: [32]u8
    sha256(@content[0], pos as i64, @hash[0])
    # TODO: Call RSA verification
    # For now, return success placeholder
    return 0
```

The TLS 1.3 client accepts any server certificate and any CertificateVerify message. A man-in-the-middle can present any key and will be accepted.

**Fix:** Complete `certificate_verify_verify` to call `rsa_verify_pkcs1_sha256` (and SHA-384/SHA-512 variants). The RSA verification infrastructure already exists in `rsa.ritz`. Until implemented, change to `return -1` (fail-closed).

---

### H-3: Second buffer overflow in TLS client decrypt

**File:** `tls13_client.ritz:400, 404`
**Severity:** HIGH — Remote exploitable

`plaintext[4096]` is too small for TLS records (max 16,384 bytes). This compounds H-1.

**Fix:** Change to `var plaintext: [16400]u8` and pass `16400` as `out_cap`.

---

### H-4: Undersized `mem_zero` leaves traffic keys in memory

**File:** `tls13_kdf.ritz:221`
**Severity:** HIGH — Secret key material exposure

`mem_zero(ks as *u8, 296)` does not zero the full `TLS13KeySchedule` struct. The struct contains 9 x 32-byte secrets + 2 x 32-byte keys + 2 x 12-byte IVs + 4-byte state = ~380 bytes. The `client_write_key`, `server_write_key`, and IVs are NOT being zeroed.

**Fix:** Compute and use the actual struct size. All hardcoded "approximate sizeof" values must be verified:

| File | Line | Hardcoded Size | Struct | Risk |
|------|------|---------------|--------|------|
| `x509.ritz` | 604 | `1200` | `X509Certificate` | Under-zeroing if struct grows |
| `tls13_client.ritz` | 164 | `8192` | `TlsClient` | Struct is likely 10-16 KB |
| `tls13_kdf.ritz` | 221 | `296` | `TLS13KeySchedule` | **Too small by ~84 bytes** |
| `tls13_client.ritz` | 91 | `280` | `TlsConfig` | Unverified |
| `tls13_client.ritz` | 195 | `296` | `TLS13KeySchedule` | Same as above |
| `tls13_client.ritz` | 481 | `600` | `X509PublicKey` | Unverified |
| `tls13_record.ritz` | 207 | `120` | `TlsRecordState` | Safe by accident (actual ~108) |
| `tls13_handshake.ritz` | 117 | `112` | `Sha256` | Correct but fragile |

---

### H-5: SHA-256 round constants as 64-branch if/else chain

**File:** `sha256.ritz:94-223`
**Severity:** HIGH — Code smell (130 wasted lines)

`get_k(i: i32) -> u32` is a 64-branch if/else chain for the SHA-256 round constants. This is the worst instance of "if/else instead of lookup table" in the codebase.

**Fix:** Replace with `const SHA256_K: [64]u32 = [0x428a2f98, 0x71374491, ...]` and index with `SHA256_K[i]`. Eliminates ~130 lines.

---

### H-6: SHA-512 round constants as 80-branch if/else chain

**File:** `sha512.ritz:121-282`
**Severity:** HIGH — Code smell (162 wasted lines)

Same as H-5 but for SHA-512 with 80 branches.

**Fix:** Replace with `const SHA512_K: [80]u64 = [...]`. Eliminates ~162 lines.

---

### H-7: `u128_mul` silently produces wrong results

**File:** `u128.ritz:109-120`
**Severity:** HIGH — Correctness bug

`u128_mul` contains a comment "might overflow, but that's ok" at line 109 for `mid = p01 + p10`. The subsequent hi computation silently ignores the carry from this overflow, producing wrong results when `p01 + p10 > 2^64`.

**Fix:** Use `u128_mul_u64` (defined at line 125) which correctly handles the mid-carry. Either delegate `u128_mul` to use `u128_mul_u64` for partial products, or add the carry handling.

---

### H-8: Dead code in `fep256_inv` — 40 lines of discarded computation

**File:** `p256.ritz:914-961`
**Severity:** HIGH — Dead code

`fep256_inv` computes ~40 lines of squarings and multiplications, then at line 961 calls `fep256_pow_p_minus_2(c, a)` discarding all prior work.

**Fix:** Remove the dead code and keep only the `fep256_pow_p_minus_2` call.

---

### H-9: Dead code — 242-line SHA-NI function never called

**File:** `sha256.ritz:450-695`
**Severity:** HIGH — Dead code / maintenance burden

`sha256_transform_ni` is a 242-line hand-unrolled SHA-NI intrinsic function that is never called — the dispatch at lines 553-555 never invokes it.

**Fix:** Either enable the SHA-NI path or remove the dead function.

---

### H-10: `ed25519_verify` missing scalar range check

**File:** `ed25519.ritz:720`
**Severity:** HIGH — RFC compliance

`ed25519_verify` does not validate that the signature scalar `s` is in the valid range `[0, l)`. Per RFC 8032 Section 5.1.7, this check is required. The TODO comment acknowledges this.

**Fix:** Add the scalar range check before performing the verification computation.

---

## MEDIUM Severity

### M-1: `mem_zero` lacks volatile semantics

**File:** `mem.ritz:21-27`

An optimising compiler may eliminate stores to memory that are not subsequently read. `mem_zero` is the sole mechanism for clearing sensitive material across ~40 call sites in the library.

**Fix:** Implement using inline assembly barrier or volatile semantics. Until available, use a function-pointer indirection through a volatile global to prevent elision.

---

### M-2: `tls_client_free` incomplete — session keys not zeroed

**File:** `tls13_client.ritz:192-196`

Not zeroed: `recv_buf[4096]`, `send_buf[4096]`, transcript hash, `server_certs`, `server_pubkey`, and the `read_state`/`write_state` `TlsRecordState` structs which store the live session keys and IVs.

**Fix:** Zero all sensitive fields, especially `read_state`/`write_state` which contain `client_key[32]`, `client_iv[12]`, `server_key[32]`, `server_iv[12]`.

---

### M-3: Dangling pointer risk in parsed certificate structs

**File:** `x509.ritz:223, 630`, `tls13_handshake.ritz:612`

`cert.tbs_data` and `name.der_data` are raw pointers into the input DER buffer. `CertificateMessage.cert_data[10]*u8` stores raw pointers into a transient `plaintext: [4096]u8` stack buffer.

**Fix:** Document lifetime requirements. Consider copying TBS data into the struct or using byte offsets instead of absolute pointers.

---

### M-4: `hkdf_expand` buffer overflow with large `info_len`

**File:** `hkdf.ritz:68-69`

`input[256]` overflows when `info_len >= 223`. No bounds check on this public function.

**Fix:** Add `if info_len > 223 { return }` at the top of `hkdf_expand`.

---

### M-5: `hkdf_expand_label` buffer could overflow

**File:** `tls13_kdf.ritz:79`

`hkdf_label[256]` comment acknowledges 520-byte theoretical max. Unbounded `label_len`/`context_len` parameters can overflow.

**Fix:** Either validate `label_len + context_len <= 247` at entry or increase buffer to `[520]u8`.

---

### M-6: Poly1305 one-time key not zeroed after use

**File:** `chacha20_poly1305.ritz:45, 91`

`poly_key[64]` is derived from the main AEAD key and left on the stack after both encrypt and decrypt return.

**Fix:** Add `mem_zero(@poly_key[0], 64)` before each `return`.

---

### M-7: Silent return of 0 on CSPRNG failure

**File:** `random.ritz:60-62, 82-83`

`random_u64()` returns 0 on `getrandom` failure. Callers cannot detect CSPRNG failure. If `random_u64` fails repeatedly during key generation, the private scalar would be all-zeros.

**Fix:** Loop on `EINTR`, abort on all other errors.

---

### M-8: RSA PKCS#1 v1.5 verification not constant-time

**File:** `rsa.ritz:271-283`

Both comparison loops use early-exit branching, leaking hash byte position via timing.

**Fix:** Replace with accumulator-based constant-time comparison.

---

### M-9: `x509_verify_hostname` ignores SubjectAltName

**File:** `x509_verify.ritz:280-286`

Only checks Common Name. RFC 6125/9525 requires SAN checking. All modern CA-issued certs carry SANs and may have empty CN.

**Fix:** Parse SAN extension (OID 2.5.29.17) and iterate over `dNSName` entries.

---

### M-10: P-256 scalar multiplication not constant-time

**File:** `p256.ritz:1290-1311`

`p256_scalar_mult` uses conditional add only when a bit is set. For `ecdsa_p256_sign` this leaks the ephemeral private key `k` via timing.

**Fix:** Implement constant-time double-and-add using conditional swaps.

---

### M-11: `random_range_u64` has modulo bias

**File:** `random.ritz:85-99`

Documented but unfixed. Unacceptable for a cryptographic library.

**Fix:** Use rejection sampling.

---

### M-12: `ed25519_verify` return convention inverted

**File:** `ed25519.ritz:755`

Returns 0 on success and -1 on failure, while every other verify function returns 1 on success and 0 on failure.

**Fix:** Change to `return mem_eq(@check_bytes[0], sig, 32)`.

---

### M-13: Intermediate scalars not zeroed in ECDSA sign

**File:** `p256.ritz:1591-1595`

`z`, `rd`, `z_rd` are intermediate values (including `r * privkey`) not zeroed before return.

**Fix:** Add `scalar256_zero(@z)`, `scalar256_zero(@rd)`, `scalar256_zero(@z_rd)`.

---

### M-14: RFC 6979 `rfc6979_generate_k` doesn't zero sensitive locals

**File:** `p256.ritz:1423-1515`

`key[32]` (HMAC key derived from private key), `v[32]`, `x_bytes[32]` (private key copy), and `msg1[97]` not zeroed.

**Fix:** Add `mem_zero` calls before each `return`.

---

### M-15: `x25519_scalarmult` scalar copy not zeroed

**File:** `x25519.ritz:585-589`

`k[32]` is a clamped copy of the private scalar, not zeroed before return.

**Fix:** Add `mem_zero(@k[0], 32)`.

---

### M-16: SHA-256/512 context not zeroed after finalization

**File:** `sha256.ritz`, `sha512.ritz`

Internal hash state (`ctx.state[8]`, `ctx.block[64]`) not zeroed after `sha256_final`/`sha512_final`. Any sensitive data fed into the hash remains on the stack.

**Fix:** Add `mem_zero(ctx as *u8, sizeof)` at end of final functions.

---

### M-17: HMAC inner/outer SHA contexts not zeroed

**File:** `hmac.ritz`

`inner_ctx` and `outer_ctx` contain intermediate hash state computed over HMAC key material, not zeroed.

**Fix:** Add `mem_zero` for both contexts before return in each HMAC variant.

---

### M-18: `bigint_mod` uses O(k) repeated subtraction

**File:** `bigint.ritz:374-378`

Algorithmically unacceptable for large RSA-sized bigints (2048+ bits). Critical performance bottleneck.

**Fix:** Replace with Barrett reduction or multi-precision division.

---

### M-19: CPUID global cache not thread-safe

**File:** `cpuid.ritz:1-191`

Eight mutable global variables cache CPU feature detection results with no atomic initialization.

**Fix:** Document thread-safety assumption or use atomic initialization.

---

### M-20: `transcript_init_for_suite` SHA-384 branch is dead code

**File:** `tls13_handshake.ritz:94-104`

Both branches of the if/else execute identical code (SHA-256 init). SHA-384 is not actually supported.

**Fix:** Implement SHA-384 branch or document that only SHA-256 suites are supported.

---

## LOW Severity

| # | Finding | File |
|---|---------|------|
| L-1 | Arena partial-allocation waste on cert parse failure | `ca_store.ritz:138-156` |
| L-2 | `ca_store_load_pem_file` passes `size=0` to `sys_mmap` for empty files | `ca_store.ritz:237` |
| L-3 | BigInt intermediates not zeroed in `bigint_mod_exp` | `bigint.ritz` |
| L-4 | ECDSA/Ed25519 X.509 verification returns 0 (fail-safe but undocumented) | `x509_verify.ritz:42-46` |
| L-5 | `GRND_NONBLOCK`/`GRND_RANDOM` constants defined but unused | `random.ritz:25-26` |
| L-6 | `fe_reduce` in x25519 uses non-constant-time nested branches | `x25519.ritz:248-253` |
| L-7 | `cpu_has_avx512` doesn't check AVX2 prerequisite | `cpuid.ritz:165` |
| L-8 | `pem_parse_certificate` only checks first 2 bytes ("CE") of type label | `pem.ritz:292-307` |
| L-9 | Various naming issues (`sha512_new` suggests ready-to-use but isn't) | `sha512.ritz` |
| L-10 | `x25519_pubkey` unnecessary zeroing loop for basepoint | `x25519.ritz:689-697` |

---

## Duplicate Code — ~683 Lines (~19%)

### Top 5 Consolidation Opportunities

#### 1. SHA-512 / SHA-384 Unification (~125 lines)

**Files:** `sha512.ritz`

`Sha384` struct is identical to `Sha512`. `sha384_update` is a near-exact copy of `sha512_update`. `sha384_final` is a copy of `sha512_final` truncated to 48 bytes. `sha384_new` is identical to `sha512_new`.

**Fix:** Remove `Sha384` as separate struct. Use `Sha512` as underlying context for both. Implement `sha384_final` as `sha512_final_n(ctx, out, 48)`.

---

#### 2. AES Block Cipher Round Body Extraction (~144 lines)

**Files:** `aes.ritz`, `aes_gcm.ritz`

`aes128_encrypt_block` and `aes256_encrypt_block` contain identical 44-line SubBytes+ShiftRows+MixColumns+AddRoundKey round bodies. Same for decrypt (~50 lines). AES-GCM 128/256 encrypt/decrypt loops are near-identical (~50 lines).

**Fix:** Extract `aes_encrypt_round(state, rk)` and `aes_decrypt_round(state, rk)` helpers. Both key sizes call the same helper parameterized by round count.

---

#### 3. HMAC Generic Implementation (~60 lines)

**Files:** `hmac.ritz`

`hmac_sha256`, `hmac_sha512`, `hmac_sha384` are structurally identical. Same HMAC algorithm with different hash functions/sizes. The ipad/opad XOR loop appears 6 times.

**Fix:** Extract parameterized `hmac_generic` inner function. Three public functions become thin wrappers.

---

#### 4. `aes_gcm.ritz` Local `mem_*` Copies (~20 lines, security risk)

**Files:** `aes_gcm.ritz`, `mem.ritz`

`gcm_mem_zero`, `gcm_mem_copy`, `gcm_mem_eq` are local copies with comment: "inlined to work around module resolution issue." If `mem.ritz`'s constant-time `mem_eq` is hardened, `gcm_mem_eq` will silently remain stale.

**Fix:** Fix module resolution issue, remove local copies.

---

#### 5. RSA / X509 Verification Chain (~159 lines)

**Files:** `rsa.ritz`, `x509_verify.ritz`

Three DigestInfo prefix builders (60 lines), three `rsa_verify_pkcs1_*` wrappers, and three `x509_verify_rsa_*` functions can all be unified into a single `hash_alg` dispatch.

**Fix:** Single `rsa_verify_pkcs1_hash(key, hash_alg, data, sig)` with dispatch. Adding SHA-3 support currently requires 9 new functions; after refactor, only 1 case.

---

### Other Duplication

| Pattern | Files | Lines |
|---------|-------|-------|
| `load32_le`/`store32_le` triplicated | `chacha20.ritz`, `chacha20_avx2.ritz`, `poly1305.ritz` | ~24 |
| ChaCha20 struct/init/encrypt identical in AVX2 | `chacha20.ritz`, `chacha20_avx2.ritz` | ~80 |
| TLS record header written 4 times | `tls13_client.ritz` | ~20 |
| ChaCha20-Poly1305 MAC construction duplicated | `chacha20_poly1305.ritz` | ~30 |
| `fe_carry_propagate` pattern repeated 7 times | `x25519.ritz` | ~35 |
| `sc_reduce`/`sc_muladd` reduction loop duplicated | `ed25519.ritz` | ~30 |
| SHA-256/512 init buffer zeroing (manual loop vs mem_zero) | `sha256.ritz`, `sha512.ritz` | ~12 |
| SHA-256/512 final big-endian output unrolled | `sha256.ritz`, `sha512.ritz` | ~96 |
| RSA modulus leading-zero stripping duplicated | `rsa.ritz` | ~10 |
| "CERTIFICATE" string comparison duplicated | `pem.ritz`, `ca_store.ritz` | ~14 |
| `pem.ritz` local `mem_cmp` separate from `mem.ritz` | `pem.ritz` | ~6 |
| `shift_recv_buf` manual memmove | `tls13_client.ritz` | ~8 |
| SIGMA constants duplicated with renaming | `chacha20.ritz`, `chacha20_avx2.ritz` | ~4 |
| `bigint_to_bytes` / `bigint_to_bytes_fixed` share logic | `bigint.ritz` | ~15 |

---

## Raw Pointer & Allocation Summary

### Heap Allocations (sys_mmap)

Only `ca_store.ritz` performs heap allocations:

| Line | Call | Size | Purpose | Paired munmap? |
|------|------|------|---------|----------------|
| 104 | `sys_mmap(...)` | 4 MB | Arena for CA certificate storage | Yes (`ca_store_destroy:115`) |
| 237 | `sys_mmap(...)` | up to 10 MB | Temporary PEM file read buffer | Yes (lines 254, 261) |

**Recommendation:** The file-read mmap (line 237) can be replaced with a streaming reader using a `[8192]u8` stack buffer, eliminating the heap allocation entirely. The arena (line 104) is harder to avoid but could shrink dramatically if DER data is referenced by offset rather than copied.

### Raw Pointer Stats

| Category | Count | Files |
|----------|-------|-------|
| `*u8` struct fields (dangling risk) | 4 | `asn1.ritz`, `x509.ritz`, `tls13_handshake.ritz`, `pem.ritz` |
| `as *u8` type-punning casts | 10+ | TLS layer files, `x509.ritz` |
| Integer-cast pointer arithmetic | 5 | `random.ritz`, `sha256.ritz`, `sha512.ritz`, `ca_store.ritz` |
| Byte-offset pointer arithmetic | 30+ | `aes.ritz`, TLS layer files |
| Backward pointer arithmetic | 2 | `x509.ritz:223,630` |
| Double pointers `**T` | 4 | `x509_verify.ritz`, `asn1.ritz`, `ca_store.ritz` |
| `*i64` type-punning for SIMD | 8 | `aes.ritz` NI functions |

---

## Code Smell Summary

| Category | Count | Worst Offenders |
|----------|-------|-----------------|
| Functions over 80 lines | 28 | `p256.ritz`, `x509.ritz`, `sha256.ritz`, `tls13_handshake.ritz` |
| If/else chains that should be tables | 7 | `sha256.ritz` (64 branches), `sha512.ritz` (80 branches), `base64.ritz` |
| Magic numbers | 24 | `p256.ritz`, `tls13_kdf.ritz`, `tls13_record.ritz`, `ca_store.ritz` |
| Dead code | 7 | `p256.ritz` (fep256_inv), `sha256.ritz` (transform_ni), `tls13_handshake.ritz` (SHA-384 branch) |
| Deep nesting (>3 levels) | 8 | `x509.ritz` (8 levels), `ed25519.ritz` (5 levels) |
| God functions / massive duplication | 12 | `hmac.ritz`, `sha512.ritz`, `aes.ritz`, `tls13_client.ritz` |

---

## Recommended Fix Order

### Tier 1 — Security critical (do immediately)

1. `tls13_record.ritz:168` — Enlarge `inner[1024]` to `[16400]`
2. `tls13_client.ritz:400` — Enlarge `plaintext[4096]` to `[16400]`
3. `tls13_handshake.ritz:754` — Change `certificate_verify_verify` to return `-1` until implemented
4. `tls13_kdf.ritz:221` — Fix undersized `mem_zero` for `TLS13KeySchedule`
5. `u128.ritz:109` — Fix `u128_mul` overflow

### Tier 2 — High-value cleanup (big line savings, low risk)

6. `sha256.ritz` — Replace 64-branch `get_k()` with `const` array (~130 lines)
7. `sha512.ritz` — Replace 80-branch `get_k512()` with `const` array (~162 lines)
8. `sha512.ritz` — Unify SHA-384/SHA-512 struct + update + final (~125 lines)
9. `aes.ritz` — Extract round body helpers (~94 lines)
10. `aes_gcm.ritz` — Remove local `mem_*` copies, fix module import

### Tier 3 — Important but larger scope

11. Implement `certificate_verify_verify` properly (RSA + ECDSA)
12. Implement SAN hostname verification
13. Add volatile semantics to `mem_zero`
14. Fix all hardcoded `sizeof` approximations
15. Add bounds check to `hkdf_expand`
16. Make P-256 scalar mult constant-time
17. Fix `ed25519_verify` return convention and add `s < l` check
18. Zero all sensitive intermediates (poly_key, HMAC contexts, SHA contexts, ECDSA scalars)
19. Consolidate HMAC into generic parameterized implementation
20. Consolidate RSA/X509 verify chain (9 functions → 3)

---

*Review conducted by 4 parallel Claude Sonnet 4.6 agents, consolidated by Claude Opus 4.6.*
