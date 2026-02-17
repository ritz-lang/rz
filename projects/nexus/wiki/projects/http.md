# HTTP

HTTP client library for Ritz. Active development.

---

## Overview

The HTTP library provides client-side HTTP functionality for Ritz applications. It is the networking layer used by Tempest (browser), Spire (for outbound requests), and any Ritz application that needs to call external HTTP APIs.

---

## Where It Fits

```
TEMPEST (browser)
    └── HTTP (client requests)
            └── CRYPTOSEC (TLS for HTTPS)

SPIRE applications
    └── HTTP (API calls, webhooks)
```

---

## Key Features

- HTTP/1.1 client with keep-alive connection pooling
- HTTPS via Cryptosec TLS 1.3
- Async I/O via io_uring
- Streaming responses (for large downloads)
- Redirect following
- Cookie management
- Custom headers
- Request/response middleware

---

## Usage

### Simple GET

```ritz
import http { get }

fn fetch_json(url: StrView) -> Result<String, Error>
    let resp = get(url)?
    if resp.status != 200
        return Err(Error.http(resp.status))
    Ok(resp.body_as_string())
```

### Builder API

```ritz
import http { Client, Request }

let client = Client.new()

# GET with headers
let resp = client.request(
    Request.get("https://api.example.com/users")
        .header("Authorization", "Bearer {token}")
        .header("Accept", "application/json")
).await?

# POST with body
let resp = client.request(
    Request.post("https://api.example.com/users")
        .json(body)
        .header("Authorization", "Bearer {token}")
).await?
```

### Streaming

```ritz
import http { Client }

# Stream a large response without buffering it all in memory
let resp = client.get("https://example.com/large-file.zip").await?
let mut file = create_file("download.zip")?
defer file.close()

while let Some(chunk) = resp.body.next_chunk().await?
    file.write(chunk)?
```

### Connection Pool

```ritz
# Client reuses connections automatically
let client = Client.new()
client.set_max_connections_per_host(10)
client.set_idle_timeout(60)

# Multiple requests to the same host reuse the connection
for url in urls
    let resp = client.get(url).await?
    process(resp)
```

---

## Request Types

```ritz
struct Request
    method: Method
    url: String
    headers: Headers
    body: Option<Body>

enum Method
    Get
    Post
    Put
    Patch
    Delete
    Head
    Options

struct Response
    status: u16
    headers: Headers
    body: Body
```

---

## HTTPS

HTTPS is handled transparently via Cryptosec TLS 1.3. When the URL starts with `https://`, the HTTP library automatically performs TLS negotiation before sending the request.

```ritz
# Same API — HTTPS is transparent
let resp = client.get("https://api.example.com/data").await?
```

---

## Error Handling

```ritz
enum HttpError
    ConnectionRefused(String)
    Timeout
    TlsError(CryptoError)
    ParseError(String)
    StatusError(u16)

fn call_api(url: StrView) -> Result<Value, HttpError>
    let resp = client.get(url).await
        .map_err(|e| HttpError.ConnectionRefused(e.to_string()))?

    if resp.status >= 400
        return Err(HttpError.StatusError(resp.status))

    parse_json(resp.body_as_string())
        .map_err(|e| HttpError.ParseError(e.to_string()))
```

---

## Current Status

Active development. HTTP/1.1 client implementation in progress.

---

## Related Projects

- [Valet](valet.md) — The server-side HTTP implementation
- [Cryptosec](cryptosec.md) — TLS 1.3 for HTTPS
- [Squeeze](squeeze.md) — gzip decompression for Content-Encoding
- [Tempest](tempest.md) — Primary consumer of the HTTP library
