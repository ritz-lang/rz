# LARB v4 Review: infrastructure packages (spire, cryptosec, http, valet, zeus, squeeze, mausoleum, tome)

**Reviewed:** 2026-10-25 · **Metrics:** [metrics-packages.md](metrics-packages.md) (sections spire → tome) · **Status:** CRITICAL
**Scope:** ROADMAP "Parked" (PHASE 8, #50). These packages get low priority unless a finding is a security bug, a ritzlib gap or a language gap.
**Method:** `INSTRUCTIONS_v4.md`, read-only. Nothing was built or run. C1 and C2 were checked by tracing every call site and buffer size by hand, and re-checked by the LARB lead in the source before filing (`tls13_record.ritz:128-183`, `tls13_handshake.ritz:740-830`). Security findings below give location, impact and fix direction only.

## Summary

Only two of these packages carry real risk: **valet's TLS termination and cryptosec's TLS layer**.
- **valet + cryptosec (C1):** with TLS enabled (`tls.enabled`), wire-supplied lengths reach fixed buffers without a bound check.
- **cryptosec (C2):** the TLS client is fail-open (no certificate, chain, hostname or CertificateVerify check), and every caller of the record decryptor frames its input wrongly, so no real TLS session can complete. The tests exercise error paths only.
- **cryptosec's own February review is still open:** `cryptosec/REVIEW.md` (2026-02-20) HIGH items H-1, H-2, H-4, H-7 and H-10 are unfixed and were never ticketed. They are now folded into #1862.

Outside TLS the problems are structural:
- **Duplicate subsystems inside a package:** a dead copy of the http package in spire, a dead second TLS stack in valet, four server loops in mausoleum, three servers in tome, four DEFLATE encoders in squeeze.
- **Hand-rolled infrastructure ritzlib should provide:** 22 integer formatters and 19 integer parsers, 8 byte-order helpers, a string-keyed hash table, argument parsing.
- **Language gaps** behind some of that: no secure-zero/volatile store; private names leak through imports into one flat namespace; element-list table literals unspecified; no generic `HashMap<K,V>`.

| Package | SLOC | Status | Worst issue |
|---|---|---|---|
| valet | 11.6k | CRITICAL | TLS record and handshake paths trust wire-supplied lengths (C1) |
| cryptosec | 27k | CRITICAL | TLS client authenticates nothing; record decrypt called with the wrong framing everywhere (C2) |
| http | 16.5k | NEEDS WORK | Request framing ignores `Transfer-Encoding`; invalid `Content-Length` means "no body" (M2); HTTP/2, HTTP/3, QUIC modules are test-only |
| spire | 25k | NEEDS WORK | `spire/httplib` is a 7.3k-line dead copy of `http/lib` (#1680); 5 modules (2.2k lines) have no importers or tests |
| mausoleum | 21k | NEEDS WORK | Four server loops and four M7SP dispatch tables; epoll `lib/server.ritz` is test-only |
| tome | 10.5k | NEEDS WORK | Three servers (one an undeclared bin); hash-table probe prologue pasted 15×; AUTH compares with `strcmp` |
| squeeze | 11.3k | NEEDS WORK | Four copies of the fixed-Huffman encoder; `gzip_stream`/`zlib_stream` 88% identical |
| zeus | 11.4k | minor | Four test-only modules (hotreload, runtime, streaming, worksteal: 1.3k lines) |

## Findings

### C1. TLS: wire-supplied lengths overflow fixed buffers [bug][security] — Critical → #1861
- `tls13_record_decrypt` (`cryptosec/lib/tls13_record.ritz:128`) takes `ciphertext_len` from the record header (`:143`), checks only `inner_len >= 1` (`:149`), then decrypts into `var inner: [1024]u8` (`:168`). The `out_cap` check (`:183`) comes after the write. GCM verifies the tag first, so the peer must hold the session keys, but with C2 any server qualifies, and valet derives keys with any client.
- `handshake_header_parse` (`cryptosec/lib/tls13_handshake.ritz:812-820`) never bounds the 24-bit handshake length by the record length; valet uses it to parse and hash its 4096-byte receive buffer (`valet/lib/tls.ritz:952`, `:990`).
- **Fix:** bound `inner_len` and the handshake length before use; replace hand-counted sizes with `sizeof`.

### C2. TLS client fails open; record-decrypt framing is wrong at every caller [bug][security] — Critical → #1862
- `certificate_verify_verify` returns success without verifying (`tls13_handshake.ritz:754-756`, `# TODO: Call RSA verification`).
- The client never verifies the chain, the hostname or CertificateVerify (`tls13_client.ritz:493`).
- `tls13_record_decrypt` expects the full record (the header is the AAD; its own tests pass the full record), but all four callers pass `buf+5`: `valet/lib/tls.ritz:1214`, `:1350`; `tls13_client.ritz:404`, `:641`.
- **Fix:** fail closed until verification exists; fix caller framing; add an end-to-end loopback test (cryptosec client ↔ valet server) exchanging application data.

### M1. Secrets and randomness [security] — Major → #1863, language half #1864
- `random_bytes`/`getrandom` return ignored at 7 sites; `random_u64` returns 0 on failure.
- 9 sites zero secrets with hand-counted sizes; 2 are short (key schedule 296 of 348 bytes; ClientHello 400 of 440).
- `mem_zero` is not volatile: safe only because nothing builds with LTO. Ritz needs a secure-zero intrinsic (#1864).
- tome AUTH compares passwords with plain `strcmp` (timing).

### M2. HTTP/1 framing [bug] — Major → #1865
- valet treats one `recv()` as one request and drops leftover bytes; `Content-Length` parsed into `i32`; `Transfer-Encoding` ignored (also in `http`); invalid `Content-Length` treated as "no body".
- Open-ended `Range` can yield a negative `Content-Length` (`valet/lib/static.ritz:573`).

### M3. 22 integer formatters, 19 parsers across 7 packages [cleanup] — Major → #1856 (appended), #1824
- `json_write_int` and tome's `resp_write_int` print only `-` for `i64::MIN`, the same bug as ritzlib's `print_int` (#1856). ritzlib's `strview_parse_i64` is already correct and should replace the parsers.

### M4. Duplicate and dead subsystems [cleanup] — Major → #1867 (pri 20), #1680, #1855
- spire/httplib (#1680); valet `lib/tls/` second TLS stack (1.6k lines, no importers); mausoleum epoll `server.ritz` (tests only); tome `server_blocking` + undeclared bin; squeeze encoder copies; http's own io_uring layer next to ritzlib's five async runtimes (#1855).

### M5. Static tables written as if-ladders [language-gap] — Major → #1866
- `qpack_static_get` (383 lines, CC 101, two copies), hpack static table, `status_reason`, `get_k`/`get_k512`. Integer tables can already be const arrays; arrays of strings or structs need spec §3.3 element-list literals.

### M6. Private names leak through imports [language-gap] — Major → #1858 (appended)
- Imported names land in one flat namespace (spec §15.3), so a module's private helpers clash with an importer's. Packages prefix-rename; this is why there are 8 copies of byte-order helpers. ritzlib also needs an endian module.

### M7. tome's hand-rolled string-keyed map [cleanup] — Major → #1858 (appended)
- Exists because ritzlib has no generic `HashMap<K,V>`.

### M8. Functions over the v4 thresholds [cleanup] — Major → #1867
- `qpack_static_get`, `get_k512`, `x509_parse_extensions` (depth 12), `valet_handle_tls_connection` (197 lines), `handle_task_event_encrypted`, `deflate_dynamic`.

### Minor → #1867, #1875, #1495
- 86 debug prints in valet's TLS hot path; 276K of chat transcripts under `spire/logs`, `tome/logs`; broken symlink `valet/lib_squeeze`; unused `mausoleum/runtime/bcmp.s`; `squeeze/lib/bytes.ritz`, `http/lib/json_stub.ritz` have no importers; stale per-package review docs; argument parsing re-implemented in four packages (#1495).

## Not findings
- valet's path-traversal guard; squeeze's inflate bounds checks; mausoleum's frame-length checks.
- Non-constant-time RSA verify (it compares public data only).
- GCM checks the tag before writing plaintext.

## Tickets filed

| Ticket | Pri | Findings | Acceptance (each can fail) |
|---|---|---|---|
| #1861 TLS: wire lengths overflow fixed buffers | 80 | C1 | Red-then-green tests for oversized records and handshake lengths; no hand-counted sizes in TLS code |
| #1862 TLS client fails open; `buf+5` framing; e2e test | 70 | C2, REVIEW.md H-items | Invalid CertificateVerify fails; client refuses an unverifiable server; cryptosec client ↔ valet exchanges application data |
| #1863 Secrets and randomness | 60 | M1 | No ignored RNG return (grep); every secret zeroing uses `sizeof`; tome AUTH constant-time |
| #1864 Language: secure-zero intrinsic | 45 | M1 | Spec section; both compilers emit volatile memset (IR test); cryptosec uses it |
| #1865 HTTP/1 framing | 50 | M2 | Tests: CL+TE, duplicate CL, invalid CL, body split across `recv()`, pipelining, out-of-range Range |
| #1866 Language: element-list array literals | 45 | M5 | Spec §3.3; const arrays of structs and strings compile under both compilers; tables become data |
| #1867 Infra dead/duplicate modules, over-threshold fns | 20 | M4, M8, minors | Listed modules deleted or given importer + test; no listed fn above critical thresholds |
| #1856, #1858 (appended) | — | M3, M6, M7 | See tickets |

All are under EPIC #50 (parked) except the language tickets, which are under #47. The security tickets are `ready` despite the parking, because valet with TLS enabled is reachable today.
