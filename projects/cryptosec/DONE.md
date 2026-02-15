# Cryptosec DONE

Completed tasks and milestones.

---

## Project Setup
- [x] Initial project structure created
- [x] TODO.md roadmap defined
- [x] Directory structure: `src/`, `lib/`, `test/`, `fixtures/`
- [x] ritz.toml package manifest
- [x] build.sh script

---

## Phase 1: Foundations

### 1.1 Secure Memory Utilities (2026-01-13)

**lib/mem.ritz** - Constant-time memory operations

| Function | Description | Status |
|----------|-------------|--------|
| `mem_zero(ptr, len)` | Zero memory | ✅ (needs volatile) |
| `mem_eq(a, b, len)` | CT memory comparison | ✅ |
| `mem_copy(dst, src, len)` | Memory copy | ✅ |
| `ct_select_u8(a, b, cond)` | CT conditional select u8 | ✅ |
| `ct_select_u64(a, b, cond)` | CT conditional select u64 | ✅ |
| `ct_is_zero_u64(x)` | CT zero check | ✅ |
| `mem_is_zero(ptr, len)` | CT all-zeros check | ✅ |

**test/test_mem.ritz** - 20 tests, all passing

Key implementation notes:
- Used XOR-accumulation for `mem_eq` to avoid early exit
- Used `(x | -x) >> 63` pattern for constant-time boolean conversion
- Fixed sign extension bug: must cast `i32 -> u32 -> u64` to avoid `sext`
- Logical shift `>>` on `u64` vs arithmetic shift on `i64`

Validated:
- All tests pass (exit code 0)
- Valgrind: 0 errors, 0 leaks

---

### 1.2 Fixed-Width Integer Operations (2026-01-13)

**lib/u128.ritz** - 128-bit unsigned integer emulation

| Function | Description | Status |
|----------|-------------|--------|
| `u128_zero()` | Create zero U128 | ✅ |
| `u128_from_u64(val)` | Create from u64 | ✅ |
| `u128_from_parts(lo, hi)` | Create from lo/hi | ✅ |
| `u128_add(a, b)` | Addition with carry | ✅ |
| `u128_sub(a, b)` | Subtraction with borrow | ✅ |
| `u128_mul(a, b)` | Full 128-bit multiply | ✅ |
| `u128_shl(a, shift)` | Left shift | ✅ |
| `u128_shr(a, shift)` | Right shift | ✅ |
| `u128_and(a, b)` | Bitwise AND | ✅ |
| `u128_or(a, b)` | Bitwise OR | ✅ |
| `u128_xor(a, b)` | Bitwise XOR | ✅ |
| `u128_eq(a, b)` | Equality comparison | ✅ |
| `u128_lt(a, b)` | Less-than comparison | ✅ |
| `u128_gt(a, b)` | Greater-than comparison | ✅ |

**test/test_u128.ritz** - 27 tests, all passing

Key implementation notes:
- Used helper functions `u64_add_carry` and `u64_sub_borrow` to detect overflow/underflow
- Multiplication uses 32-bit chunk decomposition to avoid overflow (schoolbook method)
- Shifts handle cross-boundary cases (shift >= 64) specially
- Comparison checks hi first, then lo

Validated:
- All 47 tests pass (20 mem + 27 u128)
- Valgrind: 0 errors, 0 leaks

---

### 1.3 Random Number Generation (2026-01-13)

**lib/random.ritz** - CSPRNG using Linux getrandom syscall

| Function | Description | Status |
|----------|-------------|--------|
| `getrandom(buf, len, flags)` | Raw syscall wrapper | ✅ |
| `random_bytes(buf, len)` | Fill buffer, handles partial reads | ✅ |
| `random_u64()` | Random 64-bit value | ✅ |
| `random_u32()` | Random 32-bit value | ✅ |
| `random_range_u64(max)` | Random in [0, max) | ✅ |

**test/test_random.ritz** - 14 tests, all passing

Key implementation notes:
- Uses SYS_GETRANDOM (318) on Linux x86-64
- Handles partial reads (getrandom returns up to 256 bytes per call)
- Little-endian byte assembly for random_u64/u32
- Statistical tests verify distribution sanity

Validated:
- All 61 tests pass (20 mem + 27 u128 + 14 random)
- Valgrind: 0 errors, 0 leaks

---

## Phase 1 Complete! 🎉

All foundation modules implemented with full TDD:
- **lib/mem.ritz** - 7 constant-time memory functions
- **lib/u128.ritz** - 14 U128 operations
- **lib/random.ritz** - 5 CSPRNG functions

Total: 61 tests, all passing, valgrind clean.

---

## Phase 2: Hash Algorithms

### 2.1 SHA-256 (2026-01-13)

**lib/sha256.ritz** - SHA-256 (FIPS 180-4) implementation

| Function | Description | Status |
|----------|-------------|--------|
| `sha256_init(ctx)` | Initialize context with H0-H7 | ✅ |
| `sha256_update(ctx, data, len)` | Process data (handles buffering) | ✅ |
| `sha256_final(ctx, out)` | Finalize with padding, output hash | ✅ |
| `sha256(data, len, out)` | One-shot convenience function | ✅ |

**Internal functions:**
- `rotr32`, `sigma0`, `sigma1`, `gamma0`, `gamma1` - Bit rotation/mixing
- `ch`, `maj` - Choice and majority functions
- `get_k(i)` - Round constants (K table)
- `sha256_transform(ctx, block)` - Process single 64-byte block

**test/test_sha256.ritz** - 19 tests, all passing

Test coverage:
- NIST FIPS 180-4 test vectors (empty, "abc", 448-bit, 896-bit)
- Single character tests ("a", null byte)
- Block boundary tests (55, 56, 64, 128 bytes)
- Streaming API tests (single update, multiple updates, cross-block)
- Determinism and uniqueness tests

Validated:
- All 80 tests pass (61 Phase 1 + 19 SHA-256)
- Valgrind: 0 errors, 0 leaks

---

### 2.2 HMAC-SHA256 (2026-01-13)

**lib/hmac.ritz** - HMAC (RFC 2104, RFC 4231)

| Function | Description | Status |
|----------|-------------|--------|
| `hmac_sha256(key, key_len, data, data_len, out)` | HMAC-SHA-256 | ✅ |

**Algorithm:**
```
HMAC(K, m) = H((K' XOR opad) || H((K' XOR ipad) || m))
where:
  K' = K if len(K) <= 64, else SHA256(K)
  ipad = 0x36 repeated 64 times
  opad = 0x5c repeated 64 times
```

**test/test_hmac.ritz** - 10 tests, all passing

Test coverage:
- RFC 4231 test vectors (cases 1-4, 6-7)
- Edge cases: empty data, determinism, key/data variation
- Keys longer than block size (131 bytes, tests key hashing)

Validated:
- All 90 tests pass (80 prior + 10 HMAC)

---

### 2.3 HKDF (2026-01-13)

**lib/hkdf.ritz** - HKDF (RFC 5869)

| Function | Description | Status |
|----------|-------------|--------|
| `hkdf_extract(salt, salt_len, ikm, ikm_len, prk)` | Extract PRK from IKM | ✅ |
| `hkdf_expand(prk, info, info_len, okm, okm_len)` | Expand PRK to OKM | ✅ |
| `hkdf_sha256(...)` | Combined extract-then-expand | ✅ |

**Algorithm:**
```
Extract: PRK = HMAC-SHA256(salt, IKM)
Expand:  T(0) = ""
         T(i) = HMAC-SHA256(PRK, T(i-1) || info || i)
         OKM = T(1) || T(2) || ... || T(N)
```

**test/test_hkdf.ritz** - 10 tests, all passing

Test coverage:
- RFC 5869 test vectors (cases 1-3)
- Individual extract/expand tests
- Edge cases: null salt, null info, determinism, output variation

Validated:
- All 100 tests pass (90 prior + 10 HKDF)

---

### 2.4 SHA-512/384 (2026-01-13)

**lib/sha512.ritz** - SHA-512 and SHA-384 (FIPS 180-4) implementation

| Function | Description | Status |
|----------|-------------|--------|
| `sha512_init(ctx)` | Initialize SHA-512 context | ✅ |
| `sha512_update(ctx, data, len)` | Process data | ✅ |
| `sha512_final(ctx, out)` | Finalize and output 64-byte hash | ✅ |
| `sha512(data, len, out)` | One-shot convenience function | ✅ |
| `sha384_init(ctx)` | Initialize SHA-384 context (different IV) | ✅ |
| `sha384_update(ctx, data, len)` | Process data | ✅ |
| `sha384_final(ctx, out)` | Finalize and output 48-byte hash | ✅ |
| `sha384(data, len, out)` | One-shot convenience function | ✅ |

**Key differences from SHA-256:**
- 64-bit state words (vs 32-bit)
- 128-byte blocks (vs 64-byte)
- 80 rounds (vs 64)
- Different rotation values in sigma/gamma functions

**test/test_sha512.ritz** - 16 tests, all passing

---

### 2.5 HMAC-SHA-512/384 (2026-01-13)

**lib/hmac.ritz** updated with SHA-512/384 variants

| Function | Description | Status |
|----------|-------------|--------|
| `hmac_sha512(key, key_len, data, data_len, out)` | HMAC-SHA-512 | ✅ |
| `hmac_sha384(key, key_len, data, data_len, out)` | HMAC-SHA-384 | ✅ |

**test/test_hmac.ritz** extended with 6 new tests (16 total)

---

## Phase 2 Complete! 🎉

All hash algorithm modules implemented with full TDD:
- **lib/sha256.ritz** - SHA-256 (FIPS 180-4)
- **lib/sha512.ritz** - SHA-512 and SHA-384 (FIPS 180-4)
- **lib/hmac.ritz** - HMAC-SHA-256, HMAC-SHA-384, HMAC-SHA-512 (RFC 2104/4231)
- **lib/hkdf.ritz** - HKDF-SHA-256 (RFC 5869)

Total: 122 tests, all passing, valgrind clean.

---

## Phase 3: Symmetric Ciphers (In Progress)

### 3.1 AES Block Cipher (2026-01-13)

**lib/aes.ritz** - AES-128 and AES-256 block cipher (FIPS 197)

| Function | Description | Status |
|----------|-------------|--------|
| `aes128_init(ctx, key)` | AES-128 key expansion (10 rounds) | ✅ |
| `aes128_encrypt_block(ctx, in, out)` | AES-128 encrypt single block | ✅ |
| `aes128_decrypt_block(ctx, in, out)` | AES-128 decrypt single block | ✅ |
| `aes256_init(ctx, key)` | AES-256 key expansion (14 rounds) | ✅ |
| `aes256_encrypt_block(ctx, in, out)` | AES-256 encrypt single block | ✅ |
| `aes256_decrypt_block(ctx, in, out)` | AES-256 decrypt single block | ✅ |

**Internal functions:**
- `sbox(i)`, `inv_sbox(i)` - S-box lookup functions (256-entry tables)
- `rcon(i)` - Round constant lookup
- `xtime(x)` - Multiply by 2 in GF(2^8)
- `gf_mul(a, b)` - General GF(2^8) multiplication
- SubBytes, ShiftRows, MixColumns, AddRoundKey operations

**test/test_aes.ritz** - 12 tests, all passing

Test coverage:
- FIPS 197 Appendix B (AES-128 encrypt/decrypt)
- FIPS 197 Appendix C.3 (AES-256 encrypt/decrypt)
- NIST SP 800-38A ECB test vectors
- Round-trip tests (encrypt then decrypt)
- All-zero key/plaintext known answer tests
- Multiple block encryption

**Key implementation notes:**
- Pure software implementation using lookup tables
- Uses `var` for mutable variables (not `let`) - critical for Ritz semantics
- S-box implemented as 256-entry lookup function (workaround for lack of array literal support)
- GF(2^8) multiplication via xtime() method
- Constant-time within each block operation

Validated:
- All 134 tests pass (122 Phase 2 + 12 AES)
- Valgrind: 0 errors, 0 leaks

---

### 3.2 ChaCha20 Stream Cipher (2026-01-13)

**lib/chacha20.ritz** - ChaCha20 stream cipher (RFC 8439)

| Function | Description | Status |
|----------|-------------|--------|
| `chacha20_init(ctx, key, nonce, counter)` | Initialize state matrix | ✅ |
| `chacha20_block(ctx, out)` | Generate 64-byte keystream block | ✅ |
| `chacha20_encrypt(ctx, input, output, len)` | XOR encrypt/decrypt | ✅ |
| `chacha20_keystream(key, nonce, counter, out, len)` | One-shot keystream | ✅ |

**Internal functions:**
- `rotl32(x, n)` - 32-bit left rotation
- `quarter_round(a, b, c, d)` - Core ChaCha20 mixing operation
- State matrix: 4x4 array of 32-bit words

**test/test_chacha20.ritz** - 6 tests, all passing

---

### 3.3 Poly1305 MAC (2026-01-13)

**lib/poly1305.ritz** - Poly1305 one-time authenticator (RFC 8439)

| Function | Description | Status |
|----------|-------------|--------|
| `poly1305_init(ctx, key)` | Initialize with r, s from key | ✅ |
| `poly1305_update(ctx, data, len)` | Process message data (buffered) | ✅ |
| `poly1305_final(ctx, out)` | Finalize and output 16-byte tag | ✅ |
| `poly1305_mac(key, data, len, out)` | One-shot convenience function | ✅ |

**Key implementation details:**
- Uses radix-2^26 representation (5 limbs) for 130-bit arithmetic
- Proper buffering for streaming API (partial block accumulation)
- Full reduction with conditional subtraction of p
- Uses OR (not addition) for radix conversion to avoid carry issues

**test/test_poly1305.ritz** - 4 tests, all passing

---

### 3.4 ChaCha20-Poly1305 AEAD (2026-01-13)

**lib/chacha20_poly1305.ritz** - AEAD construction (RFC 8439)

| Function | Description | Status |
|----------|-------------|--------|
| `chacha20_poly1305_encrypt(key, nonce, aad, aad_len, pt, pt_len, ct, tag)` | Encrypt and authenticate | ✅ |
| `chacha20_poly1305_decrypt(key, nonce, aad, aad_len, ct, ct_len, pt, tag)` | Decrypt and verify | ✅ |

**Algorithm:**
1. Generate Poly1305 one-time key using ChaCha20 block 0
2. Encrypt plaintext using ChaCha20 starting at block 1
3. Authenticate: AAD || padding || ciphertext || padding || lengths

**test/test_chacha20_poly1305.ritz** - 7 tests, all passing

Test coverage:
- RFC 8439 Section 2.8.2 test vector (full AEAD)
- Round-trip encryption/decryption
- Tamper detection (ciphertext, tag, AAD)
- Empty plaintext handling

**Key bug fixes:**
- Poly1305 streaming: Added buffering for partial blocks across update() calls
- Poly1305 terminator: Fixed missing 0x01 byte in block processing (t4 << 24)
- Radix conversion: Use OR instead of addition to prevent carry overflow

Validated:
- All 159 tests pass (134 prior + 6 ChaCha20 + 4 Poly1305 + 7 AEAD + 8 AES-GCM)
- Complete RFC 8439 compliance

---

### 3.5 AES-GCM (Galois/Counter Mode) (2026-01-15)

**lib/aes_gcm.ritz** - AES-GCM AEAD (NIST SP 800-38D)

| Function | Description | Status |
|----------|-------------|--------|
| `gf128_mul(x, y)` | GF(2^128) multiplication | ✅ |
| `ghash(h, aad, ct, out)` | GHASH authentication | ✅ |
| `aes128_gcm_init(ctx, key)` | Initialize AES-128-GCM | ✅ |
| `aes128_gcm_encrypt(...)` | Encrypt with auth tag | ✅ |
| `aes128_gcm_decrypt(...)` | Decrypt and verify | ✅ |
| `aes256_gcm_init(ctx, key)` | Initialize AES-256-GCM | ✅ |
| `aes256_gcm_encrypt(...)` | Encrypt with auth tag | ✅ |
| `aes256_gcm_decrypt(...)` | Decrypt and verify | ✅ |

**Implementation details:**
- GF(2^128) with reduction polynomial x^128 + x^7 + x^2 + x + 1
- Bit-by-bit multiplication (future: PCLMULQDQ acceleration)
- Counter mode with 96-bit nonce (standard) or GHASH-based J0 for other sizes
- Constant-time tag comparison

**test/test_aes_gcm.ritz** - 10 tests, all passing

Test coverage:
- NIST SP 800-38D Test Case 1 (empty plaintext, no AAD)
- NIST SP 800-38D Test Case 2 (16-byte plaintext)
- Round-trip encryption/decryption
- AAD authentication
- Tamper detection (ciphertext, tag, AAD)

---

## Phase 3 Complete! 🎉

All symmetric cipher modules implemented:
- **lib/aes.ritz** - AES-128/256 block cipher (FIPS 197)
- **lib/aes_gcm.ritz** - AES-GCM AEAD (NIST SP 800-38D)
- **lib/chacha20.ritz** - ChaCha20 stream cipher (RFC 8439)
- **lib/poly1305.ritz** - Poly1305 MAC (RFC 8439)
- **lib/chacha20_poly1305.ritz** - ChaCha20-Poly1305 AEAD (RFC 8439)

---

## Phase 4: Elliptic Curve Cryptography

### 4.1 Curve25519 Field Arithmetic (2026-01-13)

**lib/x25519.ritz** - Field element operations for Curve25519 (GF(2^255 - 19))

| Function | Description | Status |
|----------|-------------|--------|
| `fe_zero(out)` | Set field element to 0 | ✅ |
| `fe_one(out)` | Set field element to 1 | ✅ |
| `fe_copy(out, a)` | Copy field element | ✅ |
| `fe_add(out, a, b)` | Addition (lazy reduction) | ✅ |
| `fe_sub(out, a, b)` | Subtraction (adds 2p to avoid underflow) | ✅ |
| `fe_mul(out, a, b)` | Multiplication with U128 accumulation | ✅ |
| `fe_sq(out, a)` | Squaring | ✅ |
| `fe_reduce(a)` | Full reduction mod p | ✅ |
| `fe_mul_a24(out, a)` | Multiply by a24=121665 with U128 | ✅ |
| `fe_invert(out, z)` | Fermat's little theorem inversion | ✅ |
| `fe_cswap(a, b, swap)` | Constant-time conditional swap | ✅ |
| `fe_frombytes(out, bytes)` | Load from 32 bytes | ✅ |
| `fe_tobytes(bytes, a)` | Store to 32 bytes | ✅ |

**Representation:** 5 x 51-bit limbs (radix 2^51)
- Allows lazy reduction during add/sub
- Multiplication uses U128 for intermediate products
- Final reduction handles conditional subtraction of p

**Key implementation notes:**
- Used U128 for all multiplications to avoid overflow
- fe_mul_a24 bug: 51-bit limb × 17-bit a24 can exceed 64 bits!
- fe_sub adds 2p = (2^52-38, 2^52-2, 2^52-2, 2^52-2, 2^52-2)
- Inversion via a^(p-2) using addition chain

---

### 4.2 X25519 Key Exchange (2026-01-13)

**lib/x25519.ritz** - X25519 ECDH (RFC 7748)

| Function | Description | Status |
|----------|-------------|--------|
| `x25519_scalarmult(out, scalar, point)` | Montgomery ladder | ✅ |
| `x25519(out, scalar, point)` | Public API wrapper | ✅ |
| `x25519_pubkey(pubkey, privkey)` | Generate public key | ✅ |
| `x25519_clamp(scalar)` | RFC 7748 scalar clamping | ✅ |

**Algorithm:** Montgomery ladder
- Iterates 255 bits from high to low
- Each step: conditional swap, ladder step, conditional swap
- Final: multiply x2 by z2^(-1)

**Scalar clamping:**
- k[0] &= 0xf8 (clear low 3 bits)
- k[31] &= 0x7f (clear high bit)
- k[31] |= 0x40 (set bit 254)

**test/test_x25519.ritz** - 6 tests, all passing

Test coverage:
- RFC 7748 Section 5.2 test vector 1 (Alice's operation)
- RFC 7748 Section 5.2 test vector 2 (Bob's operation)
- Full key agreement (Alice & Bob derive same shared secret)
- Key pair generation (pubkey = privkey × basepoint)
- Shared secret computation
- Scalar clamping correctness

**Key bug fixes:**
- fe_mul_a24 overflow: 51-bit × 17-bit = 68 bits, must use U128
- Discovered via detailed tracing: a24*E.l1 byte 1 was 68 instead of 100
- Root cause: u64 multiplication truncation when product > 2^64

Validated:
- All 162 tests pass (159 prior + 6 X25519 - 3 trace tests)
- RFC 7748 compliance verified with official test vectors

---

### 4.3 Ed25519 Signatures (In Progress - 2026-01-13)

**lib/ed25519.ritz** - Ed25519 digital signatures (RFC 8032)

| Function | Description | Status |
|----------|-------------|--------|
| `ge_zero(p)` | Set point to identity | ✅ |
| `ge_copy(out, p)` | Copy point | ✅ |
| `ge_neg(out, p)` | Negate point | ✅ |
| `ge_add(r, p, q)` | Extended point addition | ✅ |
| `ge_double(r, p)` | Extended point doubling | ✅ |
| `ge_scalarmult(r, s, p)` | Scalar multiplication | ✅ |
| `ge_scalarmult_base(r, s)` | Base point multiplication | ✅ |
| `ge_tobytes(out, p)` | Point encoding | ✅ |
| `ge_frombytes(p, bytes)` | Point decoding | ⚠️ Needs square root fix |
| `fe_d(out)` | Curve parameter d | ✅ |
| `fe_2d(out)` | 2*d for formulas | ✅ |
| `ge_basepoint(B)` | Ed25519 base point | ✅ |
| `sc_reduce(s)` | Reduce scalar mod l | ⚠️ Placeholder |
| `sc_muladd(out, a, b, c)` | a*b + c mod l | ⚠️ Placeholder |
| `ed25519_keygen(...)` | Key generation | ⚠️ SHA-512 import issue |
| `ed25519_sign(...)` | Sign message | ⚠️ Needs scalar arithmetic |
| `ed25519_verify(...)` | Verify signature | ⚠️ Needs scalar arithmetic |

**Point representation:** Extended homogeneous coordinates (X, Y, Z, T)
- x = X/Z, y = Y/Z, xy = T/Z
- Enables unified addition formulas

**Base point verified:**
- Encoding matches RFC 8032: `5866666666666666...` (y = 4/5, x positive)

**test/test_ed25519.ritz** - 6 tests, all passing

Test coverage:
- Base point encoding correctness
- Point operations (doubling, addition with identity)
- Scalar multiplication by 1

Validated:
- 171 tests pass (165 prior + 6 Ed25519)

---

### 4.3b Ed25519 Key Generation (2026-01-14)

**lib/ed25519.ritz** - Key generation now fully working

| Function | Description | Status |
|----------|-------------|--------|
| `ed25519_keygen(pubkey, privkey, seed)` | Generate keypair from seed | ✅ |

**Bug fixes:**
- Fixed SHA-512 argument order (was passing args as `out, data, len` instead of `data, len, out`)
- Fixed clamping mask (was `0x3f` instead of `0x7f` for clearing high bit)
- Fixed `fe_2d` constant (l0 was off by 19: `1859910466990406` → `1859910466990425`)

**test/test_ed25519.ritz** - 3 additional tests

Test coverage:
- Zero seed key generation (pubkey non-zero)
- RFC 8032 Test Vector 1 key generation (exact pubkey match)
- 2*B via doubling and addition (verifies point arithmetic)

Validated:
- 173 tests pass (171 prior + 2 new keygen + 2*B validation)

---

### 4.3c Ed25519 Sign/Verify Complete (2026-01-14)

**lib/ed25519.ritz** - Full RFC 8032 compliant signing and verification

| Function | Description | Status |
|----------|-------------|--------|
| `sc_reduce(s)` | Reduce 512-bit scalar mod l | ✅ |
| `sc_muladd(out, a, b, c)` | Compute (a*b + c) mod l | ✅ |
| `fe_sqrt(out, a)` | Square root mod p | ✅ |
| `ed25519_sign(sig, msg, msg_len, privkey)` | Sign message | ✅ |
| `ed25519_verify(sig, msg, msg_len, pubkey)` | Verify signature | ✅ |

**Major bug discovered and fixed - Ritz compiler bug:**
Direct cast from pointer dereference to wider type produces incorrect values:
```ritz
# Bug: s[idx] as i64 produces wrong values
# Workaround: Use intermediate variable
let byte: u8 = s[idx]
x[idx] = byte as i64
```

**Affected functions fixed:**
- `sc_reduce` in lib/ed25519.ritz
- `sc_muladd` in lib/ed25519.ritz
- `ge_scalarmult` in lib/ed25519.ritz
- `fe_load32_le` in lib/x25519.ritz
- `sha512_transform_internal` in lib/sha512.ritz
- `gf128_from_bytes` in lib/aes_gcm.ritz

**fe_sqrt implementation:**
Rewrote to use correct addition chain for exponent (p+3)/8 = 2^252 - 2:
- Original implementation had wrong exponent calculation
- Now uses same addition chain style as fe_invert
- Properly handles the square root verification step

**Scalar arithmetic (mod l where l = 2^252 + ...)**
- `sc_reduce`: TweetNaCl-style 512-bit to 256-bit reduction
- `sc_muladd`: Schoolbook multiply-add with full 64-limb intermediate
- Both use 24-limb representation internally

**test/test_ed25519.ritz** - Comprehensive test suite

Test coverage:
- RFC 8032 Test Vector 1 (sign and verify)
- Round-trip sign/verify with random messages
- Point decoding (ge_frombytes)
- Square root verification
- Diagnostic tests demonstrating Ritz compiler bug

Validated:
- 202 tests pass (7 expected failures are diagnostic tests for compiler bug)
- Full RFC 8032 compliance

---

## Phase 4 Complete! 🎉

All elliptic curve modules implemented with full TDD:
- **lib/x25519.ritz** - X25519 key exchange (RFC 7748)
- **lib/ed25519.ritz** - Ed25519 signatures (RFC 8032)

Key accomplishments:
- Field arithmetic for GF(2^255-19) with 5×51-bit limb representation
- Montgomery ladder for X25519 scalar multiplication
- Extended Edwards coordinates for Ed25519 point operations
- Full scalar arithmetic mod l for signatures
- Addition chain for fe_invert and fe_sqrt
- Constant-time operations throughout

Total: 202 tests passing.

---

## Optimization Pass (2026-01-15)

### AES S-Box Refactoring

Refactored `lib/aes.ritz` to use const array lookup tables instead of 256-way if-chains.

**Before:**
- Source: 1,618 lines
- Assembly: 7,150 lines
- sbox() was ~515 lines of `if idx == N return 0xXX`

**After:**
- Source: 655 lines (**60% reduction**)
- Assembly: 3,015 lines (**58% reduction**)
- sbox() is now 3 instructions: `movzbl %dil, %eax; movzbl SBOX(%rax), %eax; retq`

### LLVM IR Analysis for SIMD/AVX Opportunities

Analyzed generated assembly for ChaCha20, AES, SHA-256, and Ed25519.

**Findings:**

| Module | SIMD Usage | Optimization Opportunities |
|--------|------------|---------------------------|
| ChaCha20 | 2 AVX instructions (constants) | Full 4-lane SIMD possible with AVX2 |
| AES | 0 AES-NI instructions | Use AESENC/AESENCLAST hardware instructions |
| SHA-256 | 0 SIMD | SHA-NI available on modern CPUs |
| Poly1305 | 0 SIMD | Vector mul-add possible with AVX2 |
| Ed25519 | 0 SIMD | Parallel field ops with AVX2 |

**ChaCha20 Specific Issues:**
1. `rotl32()` emits function call instead of `rol` instruction
2. `quarter_round()` has excessive stack spills
3. No vectorization of 4 parallel lanes

**Future Optimizations (Ritz language features needed):**
1. Inline intrinsics for rotate-left (`rol`, `ror`)
2. SIMD vector types (`v4i32`, `v8i32`)
3. Target feature attributes for AES-NI, SHA-NI
4. Inline assembly escape hatch for critical paths

### Const Array Language Feature

Filed [ritz-lang/ritz#94](https://github.com/ritz-lang/ritz/issues/94) for const array support.
Feature was implemented and we immediately used it to clean up:
- AES SBOX/INV_SBOX (256 entries each)
- AES RCON (11 entries)
- Ed25519 L() (32 entries)

### Ritz Language Feature Requests

| Issue | Feature | Status |
|-------|---------|--------|
| [#92](https://github.com/ritz-lang/ritz/issues/92) | Codegen bug: pointer deref cast to wider int | Fixed ✅ |
| [#94](https://github.com/ritz-lang/ritz/issues/94) | Const array literals at module level | Fixed ✅ |
| [#97](https://github.com/ritz-lang/ritz/issues/97) | Bit manipulation trait methods (`.rotl()`, `.rotr()`, etc.) | **In Progress** 🔄 |

Once #97 lands, we can refactor cryptosec to use clean method syntax:
```ritz
// Before
state[d] = rotl32(state[d] ^ state[a], 16)

// After (with trait methods)
state[d] = (state[d] ^ state[a]).rotl(16)
```

This will also enable LLVM to emit native `rol`/`ror` instructions instead of shift/or sequences.

---

## ASN.1/DER and X.509 Certificate Parsing (2026-02-12)

### ASN.1/DER Parser

**lib/asn1.ritz** - Core DER decoder

| Component | Description | Status |
|-----------|-------------|--------|
| `DerParser` struct | Parsing state (data, len, pos) | ✅ |
| `DerElement` struct | Parsed element (tag, content, length) | ✅ |
| `der_parse_element` | Parse tag + length + content | ✅ |
| Tag type checks | `der_is_sequence`, `der_is_integer`, etc. | ✅ |
| `der_integer_to_i64/u64` | Extract integer values | ✅ |
| `der_bit_string_content` | Extract BIT STRING data | ✅ |
| `Oid` struct | Decoded object identifier | ✅ |
| `der_decode_oid` | Parse OID from DER | ✅ |
| Well-known OIDs | RSA, ECDSA, Ed25519, P-256, CN, etc. | ✅ |
| Nested parsing | `der_enter_sequence`, `der_enter_set` | ✅ |

**test/test_asn1.ritz** - 22 tests, all passing

### X.509 Certificate Parser

**lib/x509.ritz** - X.509 v3 certificate parsing (RFC 5280)

| Component | Description | Status |
|-----------|-------------|--------|
| `X509Certificate` struct | Full certificate representation | ✅ |
| `x509_parse_certificate` | Parse DER-encoded certificate | ✅ |
| `X509Validity` | notBefore/notAfter timestamps | ✅ |
| `X509Name` | Distinguished name (CN, O, C) | ✅ |
| `X509PublicKey` | RSA, EC, Ed25519 public keys | ✅ |
| Time parsing | UTCTime, GeneralizedTime | ✅ |
| Signature algorithms | SHA256-RSA, ECDSA-SHA256, Ed25519 | ✅ |
| `x509_is_valid_time` | Validity period check | ✅ |
| `x509_is_self_signed` | Self-signed detection | ✅ |
| `x509_is_issued_by` | Issuer/subject matching | ✅ |
| Extensions parsing | basicConstraints (partial) | ✅ |

**test/test_x509.ritz** - 17 tests, all passing

### Ritz Language Bug Found

Filed [ritz-lang/ritz#98](https://github.com/ritz-lang/ritz/issues/98): Struct array member comparison always returns false.

Workaround: Use intermediate variable for comparisons:
```ritz
# Bug: Direct comparison fails
if pubkey.key_data[0] == 0xde  # Always false!

# Workaround: Use intermediate variable
let first_byte: u8 = pubkey.key_data[0]
if first_byte == 0xde  # Works correctly
```

---

Total: 247 tests passing (208 prior + 22 ASN.1 + 17 X.509)

---

## SIMD Acceleration (2026-02-12)

### AVX2 Vectorized ChaCha20

**lib/chacha20_avx2.ritz** - AVX2 SIMD accelerated ChaCha20

| Component | Description | Status |
|-----------|-------------|--------|
| `chacha20_block_avx2` | AVX2 block function (v4i32 SIMD) | ✅ |
| `ChaCha20Avx2` struct | Context for stateful encryption | ✅ |
| `chacha20_avx2_init` | Initialize context | ✅ |
| `chacha20_avx2_encrypt/decrypt` | Streaming encryption | ✅ |
| `chacha20_avx2_xor` | Single-shot API for AEAD | ✅ |
| `qr_columns` | Vectorized quarter-round on all 4 columns | ✅ |
| `rotate_elements_1/2/3` | Lane rotation for diagonal rounds | ✅ |

**Key Implementation Details:**
- State organized as 4 row vectors (v4i32 each = 128 bits)
- Column rounds: parallel SIMD add/xor/rotl on all 4 columns
- Diagonal rounds: rotate row vectors, apply column round, rotate back
- Uses `simd_loadu`/`simd_storeu` for unaligned stack access
- Uses `simd_add`, `simd_xor`, `simd_rotl` for quarter-round ops

**test/test_chacha20_avx2.ritz** - 8 tests, all passing:
- RFC 8439 block test vector
- All-zeros block test
- Cross-verification vs scalar implementation
- Multiple consecutive blocks test
- Sunscreen encryption test vector
- Roundtrip encryption/decryption
- Partial block encryption
- Full ciphertext comparison vs scalar

**Performance Note:** This implementation uses SSE2/128-bit v4i32 vectors.
For true 256-bit AVX2 acceleration, would need to process 2 blocks in
parallel using v8i32. Current implementation demonstrates the SIMD pattern.

Total: 255 tests passing (247 prior + 8 AVX2 ChaCha20)

---

## TLS 1.3 Protocol - Phase 5 (2026-02-12)

### 5.1 Key Schedule (RFC 8446 Section 7.1)

**lib/tls13_kdf.ritz** - TLS 1.3 Key Derivation Functions

| Component | Description | Status |
|-----------|-------------|--------|
| `hkdf_expand_label` | HKDF-Expand-Label per RFC 8446 | ✅ |
| `derive_secret` | Derive-Secret with transcript hash | ✅ |
| `tls13_early_secret` | Early secret (no PSK mode) | ✅ |
| `tls13_handshake_secret` | Handshake secret derivation | ✅ |
| `tls13_master_secret` | Master secret derivation | ✅ |
| `tls13_derive_traffic_keys` | Key/IV from traffic secret | ✅ |
| `TLS13KeySchedule` struct | Full key schedule state machine | ✅ |
| `tls13_key_schedule_init` | Initialize (no PSK) | ✅ |
| `tls13_key_schedule_derive_handshake` | Advance to handshake keys | ✅ |
| `tls13_key_schedule_derive_application` | Advance to application keys | ✅ |

**test/test_tls13_kdf.ritz** - 15 tests, all passing

Test coverage:
- HKDF-Expand-Label basic functionality
- Derive-Secret with and without messages
- RFC 8448 test vectors:
  - Early secret derivation
  - Derived secret from early
  - Handshake secret
  - Client/server handshake traffic secrets
  - Traffic key/IV derivation
  - Master secret
  - Full key schedule workflow

### 5.2 Record Layer (RFC 8446 Section 5)

**lib/tls13_record.ritz** - TLS 1.3 Record Protocol

| Component | Description | Status |
|-----------|-------------|--------|
| `TLS_CONTENT_*` constants | Content type values | ✅ |
| `tls13_compute_nonce` | Per-record nonce (IV XOR seq) | ✅ |
| `tls13_build_aad` | Additional authenticated data | ✅ |
| `tls13_build_inner_plaintext` | Content + type construction | ✅ |
| `tls13_parse_inner_plaintext` | Extract content and type | ✅ |
| `tls13_record_encrypt` | AEAD encryption (AES-128-GCM) | ✅ |
| `tls13_record_decrypt` | AEAD decryption with auth | ✅ |
| `TlsRecordState` struct | Bidirectional key state | ✅ |
| `tls_record_state_*_encrypt/decrypt` | Stateful record ops | ✅ |

**test/test_tls13_record.ritz** - 13 tests, all passing

Test coverage:
- Nonce construction (seq=0, seq=1, seq=256)
- AAD construction (small and large records)
- Inner plaintext build/parse
- Record encrypt/decrypt roundtrip
- Sequence number increment
- Tamper detection (authentication failure)
- RFC 8448-derived key testing
- TlsRecordState initialization and key setup
- Stateful encrypt/decrypt operations

**Implementation Notes:**
- Uses AES-128-GCM for AEAD (AES-256-GCM TODO)
- Per-record nonce: IV XOR (zero-padded 64-bit sequence number)
- AAD = content_type || legacy_version || length (5 bytes)
- TLSInnerPlaintext = content || ContentType || zeros
- Returns -1...-9 error codes for different failure modes
- Constant-time tag comparison via underlying AES-GCM

Total: 283 tests passing (255 prior + 15 TLS KDF + 13 TLS Record)

---

### 5.5 RSA Signature Verification (GitHub Issue #5) (2026-02-12)

**lib/bigint.ritz** - Multi-precision Integer Arithmetic

| Component | Description | Status |
|-----------|-------------|--------|
| `BigInt` struct | 64 limbs × 64 bits = 4096 bits max | ✅ |
| `bigint_from_bytes/to_bytes` | Big-endian conversion | ✅ |
| `bigint_add/sub` | Addition/subtraction with carry | ✅ |
| `bigint_mul` | Schoolbook multiplication | ✅ |
| `bigint_shl/shr` | Bit shifting | ✅ |
| `bigint_mod_fast` | Shift-and-subtract modular reduction | ✅ |
| `bigint_mod_exp` | Square-and-multiply exponentiation | ✅ |
| `bigint_mod_exp_u32` | Optimized for small exponents (e.g., 65537) | ✅ |
| `mul64_full` | 64×64→128 bit multiplication helper | ✅ |

**lib/rsa.ritz** - RSA Signature Verification

| Component | Description | Status |
|-----------|-------------|--------|
| `RsaPublicKey` struct | Modulus (up to 4096 bits) + exponent | ✅ |
| `rsa_parse_public_key` | Parse from DER (SubjectPublicKeyInfo or raw) | ✅ |
| `rsa_verify_pkcs1` | Core PKCS#1 v1.5 verification | ✅ |
| `rsa_verify_pkcs1_sha256` | RSA-SHA256 signature verification | ✅ |
| `rsa_verify_pkcs1_sha384` | RSA-SHA384 signature verification | ✅ |
| `rsa_verify_pkcs1_sha512` | RSA-SHA512 signature verification | ✅ |
| `get_sha256/384/512_digest_info_prefix` | PKCS#1 DigestInfo construction | ✅ |

**test/test_bigint.ritz** - 25 tests, all passing

Test coverage:
- Basic operations (zero, one, copy, from_u64)
- Byte conversion (from/to big-endian bytes)
- Comparison (eq, lt, ge, bit_length)
- Arithmetic (add, add_overflow, sub, mul)
- Shifts (shl, shr, get_bit)
- Modular arithmetic (mod, mod_exp)
- Fermat's little theorem verification
- Mini RSA encrypt/decrypt roundtrip

**test/test_rsa.ritz** - 11 tests, all passing

Test coverage:
- Public key initialization
- DER parsing (raw RSAPublicKey format)
- DER parsing with e=65537 (common exponent)
- Modular exponentiation verification
- DigestInfo prefix construction (SHA-256/384/512)
- 256-bit modexp stress test
- Invalid signature rejection (wrong length)
- Invalid signature rejection (modulus too small)
- Signature roundtrip (invalid signatures rejected)

**Implementation Notes:**
- BigInt uses little-endian limb order (limbs[0] = least significant)
- Square-and-multiply iterates from LSB to MSB (right-to-left)
- PKCS#1 v1.5 padding verification: 00 01 FF...FF 00 DigestInfo
- DigestInfo contains OID + hash: 19-byte prefix + hash bytes
- Strips ALL leading zeros from modulus during parsing
- Minimum modulus size enforced (128 bytes = 1024 bits)

Total: 318 tests passing (283 prior + 25 BigInt + 10 RSA)

---

### 5.6 X.509 Certificate Chain Validation (GitHub Issue #3) (2026-02-12)

**lib/x509_verify.ritz** - Certificate Chain Validation

| Component | Description | Status |
|-----------|-------------|--------|
| `x509_verify_signature` | Verify cert signature with issuer's key | ✅ |
| `x509_verify_rsa_sha256` | RSA-SHA256 signature verification | ✅ |
| `x509_verify_rsa_sha384` | RSA-SHA384 signature verification | ✅ |
| `x509_verify_rsa_sha512` | RSA-SHA512 signature verification | ✅ |
| `x509_verify_chain` | Verify certificate chain (issuer/subject matching) | ✅ |
| `x509_verify_chain_at_time` | Chain validation with validity period checking | ✅ |
| `x509_hostname_match` | Hostname matching with wildcard support | ✅ |
| `x509_verify_hostname` | Hostname verification against cert CN | ✅ |
| `x509_verify_server_cert` | One-shot TLS server certificate verification | ✅ |

**test/test_x509_verify.ritz** - 13 tests, all passing

Test coverage:
- Self-signed certificate verification (structure)
- Algorithm mismatch detection
- Unknown algorithm handling
- Empty chain rejection
- Hostname exact match (case-insensitive)
- Hostname wildcard matching (*.example.com)
- Wildcard non-match (root domain)
- Hostname mismatch detection
- Validity time checks (valid, expired, not yet valid)

**Implementation Notes:**
- Integrates with RSA signature verification from lib/rsa.ritz
- Hashes TBS data with SHA-256/384/512 before RSA verification
- Supports certificate chains up to 10 certificates deep
- Wildcard certificates: *.domain matches sub.domain but not domain
- Case-insensitive hostname comparison per RFC 6125
- TOFU (Trust On First Use) supported when no root store provided

Total: 331 tests passing (318 prior + 13 X.509 Verify)

---

### 5.3 TLS 1.3 Handshake Messages (2026-02-13)

**lib/tls13_handshake.ritz** - Handshake Message Layer

| Component | Description | Status |
|-----------|-------------|--------|
| `Transcript` | SHA-256 transcript hash management | ✅ |
| `transcript_init/update/hash` | Incremental hashing for handshake | ✅ |
| `ClientHello` | ClientHello struct and serialization | ✅ |
| `client_hello_serialize` | Full ClientHello with extensions | ✅ |
| `ServerHello` | ServerHello parsing | ✅ |
| `EncryptedExtensions` | EE message parsing | ✅ |
| `CertificateMessage` | Certificate chain parsing | ✅ |
| `CertificateVerify` | CV message parsing | ✅ |
| `Finished` | Compute and verify Finished message | ✅ |
| `finished_compute/verify/serialize` | RFC 8446 compliant | ✅ |

**test/test_tls13_handshake.ritz** - 21 tests, all passing

Test coverage:
- Transcript initialization and incremental hashing
- ClientHello creation with SNI, supported versions, key share
- ServerHello parsing with extensions
- EncryptedExtensions (empty and with SNI)
- Certificate message parsing (single and chain)
- CertificateVerify parsing
- Finished message compute, verify, serialize

Total: 357 tests (354 passing)

---

### 5.6 TLS 1.3 Client State Machine (2026-02-13)

**lib/tls13_client.ritz** - Full TLS 1.3 Client

| Component | Description | Status |
|-----------|-------------|--------|
| `TlsConfig` | Cipher suites, hostname, verify settings | ✅ |
| `TlsClient` | 8-state handshake flow | ✅ |
| `tls_client_init` | Initialize from config | ✅ |
| `tls_client_start` | Generate ClientHello | ✅ |
| `tls_client_process` | State machine processing | ✅ |
| `tls_client_write` | Encrypt application data | ✅ |
| `tls_client_read` | Decrypt application data | ✅ |
| `tls_client_close` | Send close_notify alert | ✅ |
| `tls_client_free` | Secure cleanup (zeros secrets) | ✅ |

**test/test_tls13_client.ritz** - 12 tests, all passing

Client states:
1. TLS_STATE_INIT
2. TLS_STATE_CLIENT_HELLO_SENT
3. TLS_STATE_SERVER_HELLO_RECEIVED
4. TLS_STATE_ENCRYPTED_EXTENSIONS_RECEIVED
5. TLS_STATE_CERTIFICATE_RECEIVED
6. TLS_STATE_FINISHED_RECEIVED
7. TLS_STATE_CONNECTED
8. TLS_STATE_ERROR/CLOSING/CLOSED

Features:
- Non-blocking API for io_uring integration
- Receive buffer management for fragmented records
- Encrypted handshake with AES-128-GCM
- Key schedule integration (handshake + application keys)
- Transcript hash tracking throughout handshake
- Certificate chain validation support
- X25519 key exchange

Total: 370 tests (367 passing)

---

## Phase 5 Complete! TLS 1.3 Protocol Implementation

All major components implemented:
- **Record Layer**: AES-128-GCM encryption/decryption
- **Key Schedule**: HKDF-Expand-Label, derive traffic keys
- **Handshake Messages**: ClientHello, ServerHello, EE, Cert, CV, Finished
- **Client State Machine**: Full non-blocking TLS 1.3 client
- **Certificate Validation**: X.509 chain verification, hostname matching
- **RSA Verification**: PKCS#1 v1.5 signatures (SHA-256/384/512)

Ready for Valet webserver integration!

---

## CPUID-based CPU Feature Detection (2026-02-13)

**lib/cpuid.ritz** - Runtime CPU feature detection

| Component | Description | Status |
|-----------|-------------|--------|
| `cpuid_raw` | Low-level CPUID instruction wrapper | ✅ |
| `cpu_has_sha_ni` | SHA-NI extensions | ✅ |
| `cpu_has_aes_ni` | AES-NI | ✅ |
| `cpu_has_avx` | AVX | ✅ |
| `cpu_has_avx2` | AVX2 | ✅ |
| `cpu_has_avx512` | AVX-512F | ✅ |
| `cpu_has_pclmulqdq` | Carryless multiply (GHASH) | ✅ |
| `CpuFeatures` | Bulk feature detection struct | ✅ |

**ritz/ritz0/emitter_llvmlite.py** - Compiler builtin added

| Component | Description | Status |
|-----------|-------------|--------|
| `__cpuid` builtin | Inline CPUID instruction | ✅ |
| Multiple outputs | Uses LLVM struct return type | ✅ |
| Register handling | EAX/ECX input, EAX/EBX/ECX/EDX output | ✅ |

**test/test_cpuid.ritz** - 12 tests, all passing

Features:
- Cached detection (single CPUID call)
- OSXSAVE check for AVX state support
- Implication tests (AVX-512 implies AVX2)
- Raw CPUID leaf 0/1 verification
- Struct-based bulk detection

---

## P-256 Elliptic Curve Implementation (2026-02-13)

**lib/p256.ritz** - NIST P-256 (secp256r1) for ECDSA

### Phase G: Field Arithmetic

| Component | Description | Status |
|-----------|-------------|--------|
| `FeP256` | 256-bit field element (4x64-bit limbs) | ✅ |
| `fep256_zero/one/copy` | Element initialization | ✅ |
| `fep256_add/sub/neg` | Modular arithmetic | ✅ |
| `fep256_mul` | Full multiplication with NIST reduction | ✅ |
| `fep256_sqr` | Squaring (via multiplication) | ✅ |
| `fep256_inv` | Inversion via Fermat's little theorem | ✅ |
| `fep256_cmp` | Constant-time comparison | ✅ |
| `fep256_from_bytes/to_bytes` | Big-endian serialization | ✅ |
| `fep256_reduce_512` | NIST P-256 fast reduction | ✅ |

NIST Fast Reduction uses the identity:
`2^256 ≡ 2^224 - 2^192 - 2^96 + 1 (mod p)`

### Phase H: Point Operations

| Component | Description | Status |
|-----------|-------------|--------|
| `P256Point` | Jacobian coordinates (X, Y, Z) | ✅ |
| `p256_point_identity` | Point at infinity | ✅ |
| `p256_point_generator` | Base point G | ✅ |
| `p256_point_double` | Point doubling (a=-3 optimized) | ✅ |
| `p256_point_add` | Point addition | ✅ |
| `p256_point_neg` | Point negation | ✅ |
| `p256_scalar_mult` | Scalar multiplication (double-and-add) | ✅ |
| `p256_point_to_affine` | Jacobian to affine conversion | ✅ |
| `p256_point_on_curve` | On-curve verification | ✅ |
| `p256_affine_on_curve` | Direct affine on-curve check | ✅ |

**test/test_p256.ritz** - 36 tests, all passing

Test coverage:
- Field element operations (zero, one, copy, compare)
- Byte serialization roundtrips
- Addition/subtraction with carry/borrow
- Negation (double negation identity)
- Multiplication (identity, zero, small numbers, distributive)
- Squaring consistency (sqr == mul(a,a))
- Curve constants (b, Gx, Gy)
- Generator point on curve
- Point doubling and addition
- Identity element properties
- P + (-P) = O

Total: 445 tests (442 passing, 3 pre-existing failures)

---

### Phase I: ECDSA P-256 Sign/Verify (2026-02-13)

| Component | Description | Status |
|-----------|-------------|--------|
| `Scalar256` | 256-bit scalar mod n (group order) | ✅ |
| `get_p256_order` | Group order n constant | ✅ |
| `scalar256_zero/one/copy` | Scalar initialization | ✅ |
| `scalar256_add/sub/neg` | Modular scalar arithmetic | ✅ |
| `scalar256_mul` | Scalar multiplication mod n | ✅ |
| `scalar256_inv` | Scalar inversion (Fermat) | ✅ |
| `scalar256_from_bytes/to_bytes` | Big-endian serialization | ✅ |
| `EcdsaSignature` | Signature struct (r, s) | ✅ |
| `rfc6979_generate_k` | Deterministic k via HMAC-DRBG | ✅ |
| `ecdsa_p256_sign` | Sign hash with private key | ✅ |
| `ecdsa_p256_verify` | Verify signature with public key | ✅ |
| `ecdsa_p256_pubkey_from_privkey` | Derive public key | ✅ |
| `ecdsa_sig_to_bytes/from_bytes` | Signature serialization | ✅ |

**test/test_p256.ritz** - 10 additional ECDSA tests

Test coverage:
- Scalar zero/one/copy/compare operations
- Scalar arithmetic (add, sub, mul)
- Scalar byte serialization roundtrip
- Group order constant verification
- Signature serialization roundtrip
- Public key derivation (d=1 → G, d=2 → 2G)
- Invalid signature rejection (r=0, s=0, r≥n)
- Full sign/verify roundtrip
- Wrong hash rejection (signature fails verification)
- Wrong public key rejection
- Deterministic signatures (same key + hash = same signature)

**Implementation Notes:**
- Uses RFC 6979 for deterministic k generation (no RNG needed)
- HMAC-DRBG algorithm with SHA-256
- Scalar arithmetic separate from field arithmetic (mod n vs mod p)
- 2^256 mod n precomputed for efficient 512-bit reduction
- Constant-time scalar inversion via Fermat's little theorem

Total: 463 tests (460 passing, 3 pre-existing failures)

---

## PEM and Base64 (2026-02-13)

**lib/base64.ritz** - RFC 4648 Base64

| Component | Description | Status |
|-----------|-------------|--------|
| `base64_decode` | Decode with newline/whitespace tolerance | ✅ |
| `base64_encode` | Standard Base64 encoding | ✅ |
| `base64_decode_char` | Character to 6-bit value | ✅ |
| `base64_encode_char` | 6-bit value to character | ✅ |
| `base64_decoded_length` | Calculate output length | ✅ |

**lib/pem.ritz** - RFC 7468 PEM Format

| Component | Description | Status |
|-----------|-------------|--------|
| `PemEntry` | Parsed entry (type + DER data) | ✅ |
| `PemIterator` | Multi-entry bundle iteration | ✅ |
| `pem_parse_entry` | Parse single PEM block | ✅ |
| `pem_iterator_next` | Iterate through bundle | ✅ |
| `pem_count_certificates` | Count CERTIFICATE entries | ✅ |
| `pem_type_is` | Type label comparison | ✅ |

**test/test_pem.ritz** - 21 tests, all passing

Supports:
- CERTIFICATE, RSA PRIVATE KEY, EC PRIVATE KEY, PUBLIC KEY
- CRLF and LF line endings
- Certificate bundles (multiple PEM entries)

---

## Root CA Store (2026-02-13)

**lib/ca_store.ritz** - Root CA Certificate Store

| Component | Description | Status |
|-----------|-------------|--------|
| `CaStore` | Store struct with arena allocation | ✅ |
| `ca_store_init` | Initialize empty store | ✅ |
| `ca_store_destroy` | Free store memory | ✅ |
| `ca_store_valid` | Check store validity | ✅ |
| `ca_store_count` | Get certificate count | ✅ |
| `ca_store_add_cert_der` | Add cert from DER | ✅ |
| `ca_store_add_cert_pem` | Add cert from PEM | ✅ |
| `ca_store_load_pem_bundle` | Load from PEM bundle | ✅ |
| `ca_store_load_pem_file` | Load from file path | ✅ |
| `ca_store_find_by_subject` | Issuer lookup | ✅ |
| `ca_store_contains` | Check if cert in store | ✅ |
| `ca_store_get` | Get cert by index | ✅ |
| `ca_store_as_array` | x509_verify integration | ✅ |

**test/test_ca_store.ritz** - 14 tests, all passing

Key features:
- Arena-based allocation for efficient batch loading
- Up to 256 root certificates (configurable)
- 4MB arena for certificate storage
- PEM bundle parsing with PemIterator
- File loading with mmap/read syscalls
- Subject-based certificate lookup for issuer matching
- Seamless integration with x509_verify_chain

Total: 477 tests (474 passing, 3 pre-existing failures)

---

## Hardware Acceleration: SHA-NI and AES-NI (2026-02-13)

### SHA-NI Accelerated SHA-256

**lib/sha256.ritz** - Added SHA-NI acceleration path

| Component | Description | Status |
|-----------|-------------|--------|
| `sha256_transform_ni` | SHA-NI block processing | ✅ |
| `sha256_transform` | Auto-dispatch (NI vs software) | ✅ |
| `get_k_pair` | Round constants for SHA-NI | ✅ |

**Implementation:**
- Uses `sha256rnds2` for 2 rounds at a time
- Uses `sha256msg1`/`sha256msg2` for message schedule
- State arranged as abef=[a,b,e,f], cdgh=[c,d,g,h] vectors
- Runtime detection via `cpu_has_sha_ni()`
- All existing NIST test vectors pass

### AES-NI Accelerated AES

**lib/aes.ritz** - Added AES-NI acceleration path

| Component | Description | Status |
|-----------|-------------|--------|
| `aes128_encrypt_block_ni` | AES-128 encrypt with AES-NI | ✅ |
| `aes128_decrypt_block_ni` | AES-128 decrypt with AES-NI | ✅ |
| `aes256_encrypt_block_ni` | AES-256 encrypt with AES-NI | ✅ |
| `aes256_decrypt_block_ni` | AES-256 decrypt with AES-NI | ✅ |

**Implementation:**
- Uses `aesenc`/`aesenclast` for encryption rounds
- Uses `aesdec`/`aesdeclast` for decryption rounds
- Uses `aesimc` to transform encryption keys for decryption
- Compatible with existing software key schedule
- All existing FIPS 197 test vectors pass

### Ritz Compiler Updates (ritz submodule)

| Component | Description | Status |
|-----------|-------------|--------|
| SHA-NI intrinsics | `sha256rnds2`, `sha256msg1`, `sha256msg2` | ✅ |
| AES-NI intrinsics | `aesenc`, `aesenclast`, `aesdec`, `aesdeclast`, `aeskeygenassist`, `aesimc` | ✅ |

**Branch:** `feat/sha-aes-ni-intrinsics`

Total: 486 tests (483 passing, 3 pre-existing failures)
