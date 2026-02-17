# Cryptosec

Cryptographic primitives and TLS 1.3 for the Ritz ecosystem. 331 tests passing.

---

## Overview

Cryptosec is a pure-Ritz cryptography library implementing the full set of algorithms required for TLS 1.3. It has no dependency on OpenSSL or any C cryptography library.

---

## Where It Fits

```
Valet (HTTPS server)
    └── Cryptosec (TLS 1.3)

Tempest (HTTPS client)
    └── Cryptosec (TLS 1.3)

Mausoleum (checksums)
    └── Cryptosec (SHA-256)
```

---

## Algorithm Coverage

### Hash Functions

| Algorithm | Status | Use |
|-----------|--------|-----|
| SHA-256 | Production | General hashing, TLS, certificates |
| SHA-384 | Production | TLS cipher suites |
| SHA-512 | Production | High-security hashing |

```ritz
import cryptosec.sha256 { sha256 }

let data: Vec<u8> = ...
let hash: [32]u8 = sha256(data)
```

### Message Authentication Codes

| Algorithm | Status | Use |
|-----------|--------|-----|
| HMAC-SHA-256 | Production | Message authentication |
| HMAC-SHA-384 | Production | TLS |
| HMAC-SHA-512 | Production | High-security MACs |
| Poly1305 | Production | ChaCha20-Poly1305 AEAD |

```ritz
import cryptosec.hmac { hmac_sha256 }

let key: Vec<u8> = ...
let msg: Vec<u8> = ...
let mac: [32]u8 = hmac_sha256(key, msg)
```

### Key Derivation Functions

| Algorithm | RFC | Status |
|-----------|-----|--------|
| HKDF | RFC 5869 | Production |

```ritz
import cryptosec.hkdf { hkdf_extract, hkdf_expand }

let prk = hkdf_extract(salt, ikm)
let okm = hkdf_expand(prk, info, 32)
```

### Symmetric Encryption

| Algorithm | Mode | Status |
|-----------|------|--------|
| AES-128 | GCM (AEAD) | Production |
| AES-256 | GCM (AEAD) | Production |
| ChaCha20 | Stream cipher | Production |
| ChaCha20-Poly1305 | AEAD | Production |

```ritz
import cryptosec.aes_gcm { AesGcm256 }

let cipher = AesGcm256.new(key)
let ciphertext = cipher.encrypt(nonce, plaintext, aad)?
let plaintext = cipher.decrypt(nonce, ciphertext, aad)?
```

### Asymmetric Cryptography

| Algorithm | Use | Status |
|-----------|-----|--------|
| X25519 | ECDH key exchange | Production |
| Ed25519 | Digital signatures | Production |
| RSA | Signature verification only | Production |

```ritz
import cryptosec.x25519 { x25519_keygen, x25519_diffie_hellman }

# Key exchange
let (private_key, public_key) = x25519_keygen()
let shared_secret = x25519_diffie_hellman(private_key, their_public_key)
```

### TLS 1.3

| Component | Status |
|-----------|--------|
| Key schedule | Production |
| Record layer | Production |
| Handshake | In progress |
| Session resumption | Planned |

### X.509 Certificates

| Feature | Status |
|---------|--------|
| ASN.1/DER parsing | Production |
| Certificate chain validation | Production |
| Signature verification | Production |

---

## TLS 1.3 Overview

TLS 1.3 is the protocol that secures HTTPS connections. Cryptosec implements the full handshake:

```
Client                          Server
  │                               │
  │  ──── ClientHello ──────────► │  (Key exchange, cipher suites)
  │                               │
  │  ◄─── ServerHello ──────────  │  (Key exchange response)
  │  ◄─── {Certificate} ───────   │  (Server certificate)
  │  ◄─── {CertificateVerify} ──  │  (Signature)
  │  ◄─── {Finished} ───────────  │
  │                               │
  │  ──── {Finished} ───────────► │
  │                               │
  │  ◄─── [Application Data] ─── │  (Encrypted)
```

Key exchange uses X25519 by default. The record layer uses AES-256-GCM or ChaCha20-Poly1305.

---

## Test Coverage

331 tests covering:

- All hash functions against NIST test vectors
- HMAC against RFC 2202 and RFC 4231 test vectors
- HKDF against RFC 5869 test vectors
- AES-GCM against NIST CAVP test vectors
- ChaCha20-Poly1305 against RFC 8439 test vectors
- X25519 against RFC 7748 test vectors
- Ed25519 against RFC 8032 test vectors
- TLS 1.3 handshake against known-good traces

---

## Security Properties

### Constant-Time Operations

All comparisons of security-sensitive values (MACs, signatures, keys) use constant-time comparison functions to prevent timing side-channel attacks.

### No External Dependencies

Cryptosec is pure Ritz. No OpenSSL, libsodium, or other C library dependencies. No supply chain exposure from C cryptography libraries.

### Algorithm Selection

Cryptosec implements only modern, well-analyzed algorithms. No MD5, no SHA-1, no DES, no RC4, no 3DES.

---

## Current Status

Active development. 331 tests passing. TLS 1.3 handshake in progress.

---

## Related Projects

- [Squeeze](squeeze.md) — Compression, often deployed alongside Cryptosec
- [Valet](valet.md) — Uses Cryptosec for HTTPS
- [Tempest](tempest.md) — Uses Cryptosec for HTTPS client
- [Mausoleum](mausoleum.md) — Uses Cryptosec for checksums
- [Security Subsystem](../subsystems/security.md)
