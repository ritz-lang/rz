# Cryptosec TODO

A cryptographic & security library for Ritz, targeting TLS 1.3 for the Valet webserver.

## Design Principles

1. **TDD** - Tests written first, in Ritz using `@test` framework
2. **Constant-time** - No branching on secret data (side-channel resistance)
3. **Stack-first** - Minimize heap allocations in hot paths
4. **Generics where appropriate** - Use `<T>` for reusable abstractions
5. **SIMD acceleration** - AVX2/AVX-512 for bulk operations where beneficial

---

## Phase 1: Foundations

### 1.1 Secure Memory Utilities
- [x] `mem_zero(ptr, len)` - Memory zeroing (TODO: volatile semantics)
- [x] `mem_eq(a, b, len)` - Constant-time memory comparison
- [x] `mem_copy(dst, src, len)` - Safe memory copy
- [x] `ct_select_u8`, `ct_select_u64` - Constant-time conditional select
- [x] `ct_is_zero_u64` - Constant-time zero check
- [x] `mem_is_zero(ptr, len)` - Constant-time all-zeros check
- [x] Tests for all memory utilities (20 tests)
- [ ] `SecureBuffer<N>` - Stack buffer that zeros on drop

### 1.2 Fixed-Width Integer Operations
- [x] `u128` emulation via `struct U128 { lo: u64, hi: u64 }`
- [x] `u128_add`, `u128_sub`, `u128_mul`, `u128_shl`, `u128_shr`
- [x] `u128_and`, `u128_or`, `u128_xor`, `u128_eq`, `u128_lt`, `u128_gt`
- [x] Tests with known vectors (27 tests)

### 1.3 Random Number Generation
- [x] `getrandom(buf, len, flags)` - Wrapper for Linux getrandom syscall
- [x] `random_bytes(buf, len)` - Fill buffer with secure random bytes
- [x] `random_u64()`, `random_u32()` - Get random values
- [x] `random_range_u64(max)` - Random in range [0, max)
- [x] Tests (14 tests - functionality + statistical sanity)

---

## Phase 2: Hash Algorithms (SHA-2 Family)

### 2.1 SHA-256
- [x] `Sha256` struct (state + buffer)
- [x] `sha256_init(ctx)` - Initialize state
- [x] `sha256_update(ctx, data, len)` - Process data
- [x] `sha256_final(ctx, out)` - Finalize and output 32-byte hash
- [x] `sha256(data, len, out)` - One-shot convenience function
- [x] SHA-NI accelerated path (runtime detection via CPUID)
- [x] Tests with NIST test vectors (19 tests)

### 2.2 SHA-384 / SHA-512
- [x] `Sha512` struct (64-bit state)
- [x] `sha512_init`, `sha512_update`, `sha512_final`
- [x] `sha384_init` (different IV, truncated output)
- [x] Tests with NIST test vectors (16 tests)

### 2.3 HMAC
- [x] `hmac_sha256(key, key_len, data, data_len, out)` - RFC 2104/4231 compliant
- [x] `hmac_sha384(key, data, out)` - RFC 4231 compliant
- [x] `hmac_sha512(key, data, out)` - RFC 4231 compliant
- [x] Tests with RFC 4231 test vectors (16 tests)

### 2.4 HKDF (Key Derivation)
- [x] `hkdf_extract(salt, salt_len, ikm, ikm_len, prk)` - Extract step
- [x] `hkdf_expand(prk, info, info_len, okm, okm_len)` - Expand step
- [x] `hkdf_sha256(salt, salt_len, ikm, ikm_len, info, info_len, okm, okm_len)` - Combined
- [x] Tests with RFC 5869 test vectors (10 tests)

---

## Phase 3: Symmetric Ciphers

### 3.1 AES Core
- [x] `Aes128` / `Aes256` key schedule structs
- [x] `aes128_init(ctx, key)` - Key expansion
- [x] `aes128_encrypt_block(ctx, in, out)` - Single block encrypt
- [x] `aes128_decrypt_block(ctx, in, out)` - Single block decrypt
- [x] AES-NI accelerated path (runtime detection via CPUID)
- [x] Tests with NIST FIPS 197 test vectors (12 tests)

### 3.2 AES-GCM (AEAD)
- [x] `AesGcm128` / `AesGcm256` structs
- [x] `aes128_gcm_encrypt/decrypt` and `aes256_gcm_encrypt/decrypt`
- [x] GHASH implementation (GF(2^128) multiplication)
- [~] PCLMULQDQ-accelerated GHASH (infrastructure ready, reduction needs work)
- [x] Tests with NIST SP 800-38D test vectors (10 tests)

### 3.3 ChaCha20-Poly1305 (AEAD)
- [x] `ChaCha20` struct (state)
- [x] `chacha20_init(ctx, key, nonce, counter)`
- [x] `chacha20_encrypt(ctx, in, out, len)` - XOR keystream
- [x] `Poly1305` struct (with streaming buffer)
- [x] `poly1305_mac(key, msg, len, tag)`
- [x] `chacha20_poly1305_encrypt(key, nonce, aad, pt, ct, tag)`
- [x] `chacha20_poly1305_decrypt(...)` -> i32
- [x] AVX2 vectorized ChaCha20 quarter-round (lib/chacha20_avx2.ritz - 8 tests)
- [x] Tests with RFC 8439 test vectors (17 tests + 8 AVX2 tests)

---

## Phase 4: Elliptic Curve Cryptography

### 4.1 Field Arithmetic (mod p)
- [x] `Fe25519` - Field element for Curve25519 (5x51-bit limbs)
- [x] `fe_add`, `fe_sub`, `fe_mul`, `fe_sq`, `fe_inv`
- [x] Constant-time field operations
- [x] `FeP256` - Field element for P-256 (4x64-bit limbs)
- [x] P-256 field operations with NIST fast reduction
- [x] Tests with known vectors (25 tests)

### 4.2 X25519 (Key Exchange)
- [x] `x25519(out, scalar, point)` - Scalar multiplication
- [x] `x25519_pubkey(pubkey, privkey)` - Multiply by base point
- [x] `x25519_clamp(scalar)` - Scalar clamping
- [x] Tests with RFC 7748 test vectors (6 tests)

### 4.3 Ed25519 (Signatures) - Complete ✅
- [x] `Ge25519` extended coordinates point (X, Y, Z, T)
- [x] `ge_add`, `ge_double`, `ge_neg`, `ge_copy`, `ge_zero`
- [x] `ge_scalarmult`, `ge_scalarmult_base`
- [x] `ge_tobytes`, `ge_frombytes` (encoding/decoding)
- [x] `ge_basepoint` - Ed25519 base point constants
- [x] `ed25519_keygen(pubkey, privkey, seed)` - Key generation (RFC 8032)
- [x] `fe_sqrt` - Square root mod p using addition chain (p ≡ 5 mod 8)
- [x] `sc_reduce` - Reduce 512-bit scalar mod l (TweetNaCl algorithm)
- [x] `sc_muladd` - Scalar multiply-add mod l
- [x] `ed25519_sign(sig, msg, msg_len, privkey)` - RFC 8032 compliant
- [x] `ed25519_verify(sig, msg, msg_len, pubkey)` -> i32 - RFC 8032 compliant
- [x] Tests with RFC 8032 test vectors (202 tests passing)

### 4.4 P-256 / ECDSA (For TLS 1.3 compatibility) ✅
- [x] `P256Point` struct (Jacobian coordinates)
- [x] Point addition, doubling, negation
- [x] Scalar multiplication (double-and-add)
- [x] On-curve verification
- [x] Tests (36 tests including field and point ops)
- [x] `Scalar256` type for scalars mod n (group order)
- [x] Scalar arithmetic: add, sub, mul, inv (mod n)
- [x] RFC 6979 deterministic k generation using HMAC-DRBG
- [x] `ecdsa_p256_sign` - Deterministic signature (RFC 6979)
- [x] `ecdsa_p256_verify` - Signature verification
- [x] `ecdsa_p256_pubkey_from_privkey` - Key derivation
- [x] Signature serialization (64 bytes: r || s)
- [x] Tests (10 ECDSA tests including sign/verify roundtrip)

---

## Phase 5: TLS 1.3 Protocol

### 5.1 Record Layer ✅
- [x] `tls13_record_encrypt` - AEAD record encryption (AES-128-GCM)
- [x] `tls13_record_decrypt` - AEAD record decryption with tag verification
- [x] `tls13_compute_nonce` - Per-record nonce (IV XOR sequence number)
- [x] `tls13_build_aad` - Additional authenticated data construction
- [x] `tls13_build_inner_plaintext` / `tls13_parse_inner_plaintext`
- [x] `TlsRecordState` struct with sequence number management
- [x] Tests (13 tests)

### 5.2 Key Schedule ✅
- [x] `hkdf_expand_label` - RFC 8446 HKDF-Expand-Label
- [x] `derive_secret` - Derive-Secret with transcript hash
- [x] `tls13_early_secret` - Early secret (no PSK)
- [x] `tls13_handshake_secret` - Handshake secret from shared secret
- [x] `tls13_master_secret` - Master secret derivation
- [x] `tls13_derive_traffic_keys` - Key/IV from traffic secret
- [x] `TLS13KeySchedule` struct with full state management
- [x] RFC 8448 test vectors (15 tests)

### 5.3 Handshake Messages ✅
- [x] `Transcript` struct with SHA-256 hash management
- [x] `ClientHello` struct and serialization (with extensions)
- [x] `ServerHello` struct and parsing
- [x] `EncryptedExtensions` parsing
- [x] `CertificateMessage` parsing (single cert + chain)
- [x] `CertificateVerify` parsing
- [x] `Finished` compute and verify
- [x] Tests with RFC 8446 compliant behavior (21 tests)

### 5.4 X.509 Certificate Parsing and Validation (Issues #3, #5) ✅
- [x] ASN.1 DER parser (lib/asn1.ritz) - 22 tests
- [x] `X509Certificate` struct
- [x] `x509_parse_certificate(der, len, cert)` -> Result
- [x] Certificate chain validation (lib/x509_verify.ritz) - 13 tests
  - [x] `x509_verify_signature` - RSA-SHA256/384/512 signature verification
  - [x] `x509_verify_chain` - Chain building and path validation
  - [x] `x509_verify_chain_at_time` - With validity period checking
  - [x] `x509_verify_hostname` - Hostname verification (exact + wildcard)
  - [x] `x509_verify_server_cert` - One-shot TLS server cert verification
- [x] Root CA store loading (lib/ca_store.ritz) - 14 tests
  - [x] `CaStore` struct with arena-based allocation
  - [x] `ca_store_init`, `ca_store_destroy` - Lifecycle management
  - [x] `ca_store_load_pem_bundle` - Load from PEM bundle data
  - [x] `ca_store_load_pem_file` - Load from PEM file (e.g., ca-certificates.crt)
  - [x] `ca_store_find_by_subject` - Issuer lookup
  - [x] `ca_store_as_array` - Integration with x509_verify_chain

### 5.5 RSA Signature Verification (Issue #5) ✅
- [x] Big integer arithmetic (lib/bigint.ritz) - 25 tests
  - [x] `BigInt` struct (64 limbs of 64 bits = 4096 bits max)
  - [x] `bigint_from_bytes`, `bigint_to_bytes` - Big-endian conversion
  - [x] `bigint_add`, `bigint_sub`, `bigint_mul` - Basic arithmetic
  - [x] `bigint_mod_fast` - Modular reduction
  - [x] `bigint_mod_exp` - Square-and-multiply modular exponentiation
- [x] RSA public key parsing (lib/rsa.ritz)
  - [x] `RsaPublicKey` struct (modulus + exponent)
  - [x] `rsa_parse_public_key` - Parse from DER (SubjectPublicKeyInfo or raw)
- [x] PKCS#1 v1.5 signature verification
  - [x] `rsa_verify_pkcs1_sha256` - RSA-SHA256 verification
  - [x] `rsa_verify_pkcs1_sha384` - RSA-SHA384 verification
  - [x] `rsa_verify_pkcs1_sha512` - RSA-SHA512 verification
  - [x] DigestInfo prefix construction for SHA-256/384/512
- [x] Tests (11 tests including key parsing, modexp, and invalid signature handling)

### 5.6 TLS Connection State Machine ✅
- [x] `TlsConfig` struct (cipher suites, hostname, verify settings)
- [x] `TlsClient` struct (8-state handshake flow)
- [x] `tls_client_init(client, config)` - Initialize from config
- [x] `tls_client_start(client, out, out_cap)` - Generate ClientHello
- [x] `tls_client_process(client, data, len, out, out_cap, out_len)` - State machine
- [x] `tls_client_write(client, data, len, out, out_cap)` - Encrypt app data
- [x] `tls_client_read(client, data, len, out, out_cap)` - Decrypt app data
- [x] `tls_client_close(client, out, out_cap)` - Send close_notify
- [x] Non-blocking API for io_uring integration
- [x] Tests (12 tests)

---

## SIMD Considerations

| Algorithm | SIMD Opportunity | Instruction Set |
|-----------|------------------|-----------------|
| SHA-256 | SHA-NI (Intel) | SHA extensions |
| AES | AES-NI | AESNI + PCLMULQDQ |
| ChaCha20 | 4-way parallel | AVX2 |
| Poly1305 | Vectorized multiply | AVX2 |
| X25519 | Field multiply | AVX2/AVX-512 |

Runtime detection via CPUID (lib/cpuid.ritz):
- [x] `cpu_has_sha_ni()` -> i32 - SHA extensions
- [x] `cpu_has_aes_ni()` -> i32 - AES-NI
- [x] `cpu_has_avx()` -> i32 - AVX
- [x] `cpu_has_avx2()` -> i32 - AVX2
- [x] `cpu_has_avx512()` -> i32 - AVX-512F
- [x] `cpu_has_pclmulqdq()` -> i32 - PCLMULQDQ (for GHASH)
- [x] `CpuFeatures` struct for bulk detection
- [x] __cpuid builtin added to Ritz compiler
- [x] Tests (12 tests)

---

## Project Structure

```
cryptosec/
├── src/
│   └── main.ritz           # Example/demo entry point
├── lib/
│   ├── mem.ritz            # Secure memory utilities
│   ├── u128.ritz           # 128-bit integer emulation
│   ├── random.ritz         # CSPRNG
│   ├── sha256.ritz         # SHA-256
│   ├── sha512.ritz         # SHA-384/512
│   ├── hmac.ritz           # HMAC
│   ├── hkdf.ritz           # HKDF
│   ├── aes.ritz            # AES block cipher
│   ├── gcm.ritz            # AES-GCM AEAD
│   ├── chacha20.ritz       # ChaCha20 stream cipher
│   ├── poly1305.ritz       # Poly1305 MAC
│   ├── chacha20poly1305.ritz # Combined AEAD
│   ├── fe25519.ritz        # Curve25519 field arithmetic
│   ├── x25519.ritz         # X25519 key exchange
│   ├── ed25519.ritz        # Ed25519 signatures
│   ├── cpuid.ritz          # CPU feature detection
│   └── tls/
│       ├── record.ritz     # TLS record layer
│       ├── handshake.ritz  # Handshake messages
│       ├── keyschedule.ritz # Key derivation
│       └── client.ritz     # TLS client
├── test/
│   ├── test_mem.ritz
│   ├── test_sha256.ritz
│   ├── test_aes.ritz
│   ├── test_gcm.ritz
│   ├── test_chacha20poly1305.ritz
│   ├── test_x25519.ritz
│   ├── test_ed25519.ritz
│   ├── test_bigint.ritz
│   ├── test_rsa.ritz
│   ├── test_tls13_kdf.ritz
│   └── test_tls13_record.ritz
├── fixtures/
│   └── test_vectors/       # NIST, RFC test vectors
├── build.sh
├── TODO.md
├── DONE.md
└── README.md
```

---

## Current Phase: 5 - TLS 1.3 Protocol ✅ COMPLETE

**All TLS 1.3 components implemented!**
- TLS 1.3 record encryption/decryption (AES-128-GCM) ✅
- TLS 1.3 key schedule (RFC 8446 Section 7.1) ✅
- RSA signature verification (PKCS#1 v1.5) ✅
- Big integer arithmetic for RSA modular exponentiation ✅
- RSA-SHA256/384/512 signature verification ✅
- X.509 certificate chain validation ✅
- Hostname verification with wildcard support ✅
- Handshake message parsing/serialization ✅
- Full TLS client state machine ✅
- ECDSA P-256 sign/verify (RFC 6979) ✅
- Root CA store loading from PEM bundles ✅
- 486 tests total (483 passing, 3 pre-existing compiler struct array comparison bugs)

**Ready for Valet integration!**
