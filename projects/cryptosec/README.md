# Cryptosec

A cryptographic & security library for [Ritz](../langdev), targeting TLS 1.3 for the [Valet](../valet) webserver.

## Goals

- **TLS 1.3 support** for Valet HTTP server
- **Pure Ritz implementation** - no C dependencies
- **Constant-time operations** - side-channel resistant
- **SIMD acceleration** - AVX2/AES-NI where beneficial
- **Test-driven development** - comprehensive test coverage

## Supported Algorithms

### Hash Functions
- SHA-256, SHA-384, SHA-512
- HMAC-SHA256, HMAC-SHA384
- HKDF (RFC 5869)

### Symmetric Ciphers
- AES-128-GCM, AES-256-GCM (AEAD)
- ChaCha20-Poly1305 (AEAD)

### Asymmetric Cryptography
- X25519 (key exchange)
- Ed25519 (signatures)
- P-256/ECDSA (optional, for compatibility)

### TLS 1.3
- Full handshake support
- Certificate validation
- Integration with io_uring async I/O

## Requirements

- Linux (uses getrandom syscall)
- Ritz compiler (sibling `langdev` directory)
- x86-64 CPU (AVX2 for accelerated paths)

## Building

```bash
export RITZ_PATH=/path/to/langdev
./build.sh
```

## Testing

```bash
ritz test
```

## Project Structure

```
cryptosec/
├── lib/          # Library modules
├── test/         # Test files
├── fixtures/     # Test vectors
└── src/          # Example programs
```

## Status

**Current Phase:** 1 - Foundations

See [TODO.md](TODO.md) for detailed progress.

## License

TBD
