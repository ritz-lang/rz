# Valet

High-performance async HTTP/1.1 server. Production ready.

**1.47 million requests per second — 10.7x faster than nginx.**

---

## Overview

Valet is the HTTP server layer of the Ritz web stack. It handles raw TCP connections, TLS termination, HTTP parsing, and response delivery. Applications run on top of Zeus and Spire, which delegate to Valet for I/O.

---

## Where It Fits

```
Your Application / Spire
         │
         ▼
      ZEUS (app server)
         │
         ▼
      VALET (HTTP server)
         │
    ┌────┴────┐
  Mausoleum  Tome
         │
    ┌────┴────┐
  Cryptosec Squeeze
```

---

## Performance

| Metric | Value |
|--------|-------|
| Peak throughput | 1.47M req/s |
| vs nginx | 10.7x faster |
| I/O model | io_uring (Linux async I/O) |
| File serving | Zero-copy (sendfile/splice) |
| Concurrency | Multi-process with SO_REUSEPORT |

---

## Key Features

### io_uring Async I/O

Valet uses `io_uring` — the modern Linux async I/O interface — for all network operations. Unlike epoll-based servers, io_uring allows multiple I/O operations to be submitted in a batch with a single syscall:

```ritz
import ritzlib.uring { Ring }

fn accept_loop(ring:& Ring, listener_fd: i32)
    loop
        let conn_fd = ring.accept(listener_fd).await?
        spawn handle_connection(ring, conn_fd)
```

### Zero-Copy File Serving

Static files are served without copying data into userspace. The kernel transfers bytes directly from the file's page cache to the socket buffer.

### Multi-Process Architecture

Valet forks multiple worker processes. All workers share a port via `SO_REUSEPORT`. The kernel load-balances incoming connections across workers automatically.

### Keep-Alive Connections

HTTP/1.1 persistent connections are fully supported. A single TCP connection can handle many requests sequentially.

---

## Feature Phases

| Phase | Features | Status |
|-------|----------|--------|
| 0 | Async I/O, HTTP parsing, keep-alive | Complete |
| 1 | Zero-copy send, memory pools | Complete |
| 2 | JSON config, graceful shutdown | Complete |
| 3 | Static files, Range requests, ETag | Complete |
| 4 | Routing, middleware, interceptors | Complete |
| 5 | gzip/deflate compression (Squeeze) | Complete |
| 6 | TLS 1.3 (Cryptosec) | In progress |

---

## Usage

### Simple Request Handler

```ritz
import valet { Server, Request, Response }

fn handle(req: Request) -> Response
    match req.path
        "/" => Response.ok("<h1>Hello from Valet!</h1>")
        "/health" => Response.ok("ok")
        _ => Response.not_found("Not found")

fn main() -> Result<(), Error>
    var server = Server.new()
    server.set_handler(handle)
    server.listen(":8080")?
    Ok(())
```

### JSON API

```ritz
import valet { Server, Request, Response }
import ritzlib.json { to_json }

struct User
    id: i32
    name: String

fn get_user(req: Request) -> Response
    let id = req.path_param("id")?.parse::<i32>()?
    match db.find_user(id)
        Some(user) => Response.json(to_json(user))
        None => Response.not_found("User not found")

fn main() -> Result<(), Error>
    var server = Server.new()
    server.get("/users/:id", get_user)
    server.listen(":8080")?
    Ok(())
```

### Static File Server

```ritz
import valet { Server }

fn main() -> Result<(), Error>
    var server = Server.new()
    server.serve_static("/", "./public/")
    server.listen(":8080")?
    Ok(())
```

### TLS (HTTPS)

```ritz
import valet { Server }

fn main() -> Result<(), Error>
    var server = Server.new()
    server.set_tls("cert.pem", "key.pem")
    server.set_handler(handle)
    server.listen(":443")?
    Ok(())
```

---

## Configuration

Valet can be configured via JSON:

```json
{
  "workers": 4,
  "listen": ":8080",
  "keepalive_timeout": 60,
  "max_request_size": 10485760,
  "static_files": {
    "/static": "./public"
  },
  "compression": {
    "enabled": true,
    "min_size": 1024
  }
}
```

---

## Middleware

```ritz
fn logging_middleware(req: Request, next: Handler) -> Response
    let start = now()
    let resp = next(req)
    let duration = now() - start
    print("{req.method} {req.path} → {resp.status} ({duration}ms)\n")
    resp

fn auth_middleware(req: Request, next: Handler) -> Response
    let token = req.header("Authorization")?
    if not verify_token(token)
        return Response.unauthorized("Invalid token")
    next(req)

fn main() -> Result<(), Error>
    var server = Server.new()
    server.use(logging_middleware)
    server.use(auth_middleware)
    server.set_handler(handle)
    server.listen(":8080")?
    Ok(())
```

---

## Testing

85 tests covering all features. Tests use a mock HTTP client to make requests against a real server started on a random port.

```ritz
[[test]]
fn test_basic_request() -> i32
    let server = TestServer.start(handle)
    defer server.stop()

    let resp = server.get("/")
    assert resp.status == 200
    assert resp.body.contains("Hello")
    0
```

---

## Current Status

Production ready. Used as the HTTP layer for Nexus and all Ritz web applications.

---

## Related Projects

- [Zeus](zeus.md) — App server that sits on top of Valet
- [Spire](spire.md) — Web framework that uses Zeus and Valet
- [Cryptosec](cryptosec.md) — TLS 1.3 for HTTPS
- [Squeeze](squeeze.md) — gzip compression for responses
- [HTTP](http.md) — HTTP client library
- [Web Stack Subsystem](../subsystems/web-stack.md)
