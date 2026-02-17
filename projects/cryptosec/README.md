# Cryptosec

Cryptographic primitives and security library for Ritz - pure Ritz implementation targeting TLS 1.3.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Cryptosec provides the cryptographic foundation for the Ritz ecosystem. It implements hashing, symmetric encryption, asymmetric cryptography, and the full TLS 1.3 handshake in pure Ritz with no C dependencies. The primary integration target is the Valet HTTP server, which uses cryptosec for HTTPS support.

All implementations aim for constant-time execution to resist timing side-channel attacks. The library uses the `getrandom` syscall for cryptographically secure random number generation. SIMD acceleration via AES-NI and AVX2 is planned for hot paths.

Cryptosec is also used by Goliath (content-addressable filesystem) for SHA-256 content hashing.

## Features

- SHA-256, SHA-384, SHA-512 hash functions
- HMAC-SHA256, HMAC-SHA384
- HKDF key derivation (RFC 5869)
- AES-128-GCM and AES-256-GCM (AEAD)
- ChaCha20-Poly1305 (AEAD)
- X25519 key exchange (Diffie-Hellman)
- Ed25519 digital signatures
- P-256/ECDSA (for TLS compatibility)
- Full TLS 1.3 handshake support
- Certificate validation
- Constant-time implementations (side-channel resistant)
- No C dependencies - pure Ritz

## Installation

```bash
# As a dependency in ritz.toml:
# [dependencies]
# cryptosec = { path = "../cryptosec" }

# Build from source
export RITZ_PATH=/path/to/ritz
./ritz build .
```

## Usage

```ritz
import lib.sha256

# SHA-256 hash
var digest: [32]u8
sha256(data, data_len, @digest[0])

# HMAC-SHA256
var mac: [32]u8
hmac_sha256(key, key_len, message, msg_len, @mac[0])
```

```ritz
import lib.aes_gcm

# AES-256-GCM encryption
var ciphertext: [MAX_LEN]u8
var tag: [16]u8
aes256_gcm_encrypt(key, nonce, plaintext, pt_len, @ciphertext[0], @tag[0])

# AES-256-GCM decryption (authenticated)
let ok: i32 = aes256_gcm_decrypt(key, nonce, ciphertext, ct_len, tag, @plaintext[0])
```

```ritz
import lib.x25519

# X25519 key exchange
var public_key: [32]u8
var shared_secret: [32]u8
x25519_keygen(private_key, @public_key[0])
x25519_shared(private_key, peer_public, @shared_secret[0])
```

## Dependencies

- `ritzlib` - Standard library (uses `getrandom` syscall for entropy)

## Status

**Active development** - SHA-256, HMAC, and foundational primitives are implemented. AES-GCM, ChaCha20-Poly1305, X25519, and TLS 1.3 handshake are in progress as part of Valet HTTPS integration.

## License

MIT License - see LICENSE file
