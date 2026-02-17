# Security Subsystem

The security subsystem provides cryptographic primitives and compression — the infrastructure that makes the web stack secure and efficient.

---

## Projects in This Subsystem

| Project | Role | Status |
|---------|------|--------|
| [Cryptosec](../projects/cryptosec.md) | TLS 1.3, hashes, symmetric/asymmetric crypto | Active (331 tests) |
| [Squeeze](../projects/squeeze.md) | gzip/deflate/zlib compression | Production (132 tests) |

---

## Cryptosec: Cryptographic Primitives

Cryptosec is a pure-Ritz cryptography library implementing TLS 1.3 and the underlying primitives it requires.

### Algorithm Coverage

| Category | Algorithms |
|----------|------------|
| Hash functions | SHA-256, SHA-384, SHA-512 |
| MACs | HMAC-SHA-256, HMAC-SHA-384, HMAC-SHA-512, Poly1305 |
| KDFs | HKDF |
| Symmetric | AES-128-GCM, AES-256-GCM, ChaCha20, ChaCha20-Poly1305 |
| Asymmetric | X25519 (key exchange), Ed25519 (signatures), RSA (verify only) |
| TLS 1.3 | Key schedule, record layer, handshake |
| X.509 | ASN.1/DER parsing, certificate validation |

### TLS 1.3 Integration

Cryptosec provides TLS for Valet (as the HTTP server) and for Tempest (as an HTTPS client):

```
Valet (port 443)
    │
    ▼
Cryptosec TLS 1.3 handshake
    │ X25519 key exchange
    │ Ed25519 or RSA certificate verification
    │ AES-256-GCM or ChaCha20-Poly1305 record encryption
    ▼
Encrypted HTTP/1.1 channel
```

### Usage Example

```ritz
import cryptosec.sha256 { sha256 }
import cryptosec.aes_gcm { AesGcm256 }
import cryptosec.hkdf { hkdf_expand }

# Hashing
let hash = sha256(data)

# Symmetric encryption
let key: [32]u8 = ...
let nonce: [12]u8 = ...
let cipher = AesGcm256.new(key)
let ciphertext = cipher.encrypt(nonce, plaintext, aad)?

# Key derivation
let session_key = hkdf_expand(prk, info, 32)?
```

### Test Coverage

331 tests cover:
- Correctness of all algorithms against known test vectors
- NIST test vectors for AES
- RFC test vectors for HMAC, HKDF
- TLS 1.3 handshake test vectors

---

## Squeeze: Compression

Squeeze is a pure-Ritz implementation of the gzip, deflate, and zlib compression standards. It includes SIMD-accelerated implementations of CRC-32 and Adler-32.

### Standards Support

| Algorithm | RFC / Standard | Status |
|-----------|----------------|--------|
| CRC-32 | ISO 3309 | Production + SIMD |
| Adler-32 | RFC 1950 | Production + SIMD |
| DEFLATE | RFC 1951 | Production |
| GZIP | RFC 1952 | Production |
| ZLIB | RFC 1950 | Production |

### SIMD Acceleration

| Operation | Instruction | Speedup |
|-----------|-------------|---------|
| CRC-32 | PCLMULQDQ folding | ~15x |
| Adler-32 | PSADBW vectorization | ~4x |

### Usage in Valet

When a client sends `Accept-Encoding: gzip`, Valet uses Squeeze to compress the response:

```ritz
import squeeze.gzip { gzip_compress }

fn compress_response(body: Vec<u8>) -> Vec<u8>
    gzip_compress(body)
```

### Usage in Tempest

When a server sends a gzip-compressed response body, Tempest uses Squeeze to decompress it:

```ritz
import squeeze.gzip { gzip_decompress }

fn decode_body(compressed: Vec<u8>) -> Result<Vec<u8>, Error>
    gzip_decompress(compressed)
```

---

## How They Work Together

Both libraries are used by Valet and Tempest:

```
VALET (server side)          TEMPEST (client side)
        │                            │
        ├── Cryptosec TLS            ├── Cryptosec TLS
        │   (HTTPS server)           │   (HTTPS client)
        │                            │
        └── Squeeze gzip             └── Squeeze gzip
            (response compression)       (response decompression)
```

They also provide foundational services to Mausoleum:

- Cryptosec provides SHA-256 for content addressing and checksum validation
- Squeeze could optionally compress stored data pages

---

## Security Philosophy

### No External Dependencies

Both Cryptosec and Squeeze are implemented from scratch in pure Ritz. There are no OpenSSL, zlib, or other C library dependencies.

This means:
- No supply chain attacks via C library vulnerabilities
- Direct control over cryptographic implementations
- No FFI overhead

### Constant-Time Operations

Cryptosec implements constant-time comparisons for all security-sensitive operations to prevent timing attacks.

### Test Vectors

All cryptographic algorithms are validated against official test vectors from:
- NIST Cryptographic Algorithm Validation Program (CAVP)
- RFC test vectors
- Project Wycheproof (Google's test cases for cryptographic libraries)

---

## See Also

- [Cryptosec project page](../projects/cryptosec.md)
- [Squeeze project page](../projects/squeeze.md)
- [Valet](../projects/valet.md) — Uses both for HTTPS and compression
- [Tempest](../projects/tempest.md) — Uses both for HTTPS client
- [Web Stack Subsystem](web-stack.md)
