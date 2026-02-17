# Web Stack Subsystem

The Ritz web stack provides a complete, high-performance web platform — from raw HTTP parsing to a full application framework. Every layer is written in Ritz with no libc dependency.

---

## Projects in This Subsystem

| Project | Role | Status |
|---------|------|--------|
| [Valet](../projects/valet.md) | HTTP/1.1 server (1.47M req/s) | Production |
| [Zeus](../projects/zeus.md) | App server and process manager | Design |
| [Spire](../projects/spire.md) | MVRSPT web framework | Design |
| [HTTP](../projects/http.md) | HTTP client library | Active |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        YOUR APPLICATION                              │
│                   (or Nexus, or your Spire app)                     │
└─────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┴──────────────────────────────────┐
│                               SPIRE                                  │
│                     MVRSPT Web Framework                             │
│                                                                      │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌─────────┐  ┌───────────┐  ┌─────┐ │
│  │Model │  │ View │  │ Repo │  │ Service │  │ Presenter │  │Tests│ │
│  └──────┘  └──────┘  └──────┘  └─────────┘  └───────────┘  └─────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┴──────────────────────────────────┐
│                               ZEUS                                   │
│                       App Server / Process Manager                   │
│                                                                      │
│     Process spawning │ Load balancing │ Zero-downtime deploys       │
└─────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┴──────────────────────────────────┐
│                              VALET                                   │
│                       HTTP/1.1 Server                                │
│                                                                      │
│     io_uring async │ Zero-copy send │ Multi-process SO_REUSEPORT    │
│     1.47M req/s   │ TLS 1.3        │ Static files, routing          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Valet: The HTTP Server

Valet is a production-ready HTTP/1.1 server benchmarked at 1.47 million requests per second — 10.7x faster than nginx.

**Performance features:**

- **io_uring** — Async I/O via the Linux io_uring interface (no blocking syscalls)
- **Zero-copy send** — Files served with `sendfile`/splice, never copied into userspace
- **Memory pools** — Pre-allocated connection and buffer pools
- **Multi-process** — Fork multiple workers, all share port via `SO_REUSEPORT`

**Feature phases:**

| Phase | Features |
|-------|----------|
| 0 | Async I/O, HTTP parsing, keep-alive |
| 1 | Zero-copy send, memory pools |
| 2 | JSON config, graceful shutdown |
| 3 | Static files, Range requests, ETag |
| 4 | Routing, middleware, interceptors |
| 5 | gzip/deflate compression (via Squeeze) |
| 6 | TLS 1.3 (via Cryptosec) |

---

## Zeus: The App Server

Zeus sits between Valet and application frameworks like Spire:

- **Process management** — Spawn, monitor, and restart worker processes
- **Load balancing** — Distribute requests across worker pool
- **Zero-downtime deploys** — Drain existing workers while spinning up new ones
- **IPC** — Shared memory ring buffers for fast process communication

Zeus is the Ritz equivalent of Gunicorn, PM2, or Puma — a supervisor that manages the lifecycle of application processes.

---

## Spire: The Web Framework

Spire implements the MVRSPT (Model-View-Repository-Service-Presenter-Tests) pattern:

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **M** Model | `models/` | Pure data structs, no behavior |
| **V** View | `views/` | Templates, HTML/JSON rendering |
| **R** Repository | `repos/` | Data access abstraction |
| **S** Service | `services/` | Business logic and workflows |
| **P** Presenter | `presenters/` | HTTP handlers and routing |
| **T** Tests | `tests/` | Unit and integration tests |

**Why MVRSPT instead of MVC?**

Traditional MVC accumulates business logic in models. Spire separates:
- **Repository** — Abstracts the database. Services call repositories, not the database directly. Repositories are easily mocked.
- **Service** — All business rules live here. Testable without a database or HTTP.
- **Presenter** — Thin HTTP adapter. No business logic here.

**Example:**

```ritz
// services/task_service.ritz — Business logic
fn create_task(self:& TaskService, user: User, title: StrView) -> Result<Task, Error>
    if title.len() < 3
        return Err(ValidationError("Title too short"))
    let pending = self.repo.count_pending(user.id)
    if pending >= 100
        return Err(LimitError("Too many pending tasks"))
    self.repo.create(Task { ... })

// presenters/task_presenter.ritz — HTTP layer
[[route("POST", "/tasks")]]
fn create(self:& TaskPresenter, req: Request) -> Response
    let form = req.parse_json::<CreateTaskForm>()?
    match self.service.create_task(req.user, form.title)
        Ok(task) => Response.json(task, status: 201)
        Err(ValidationError(msg)) => Response.bad_request(msg)
        Err(LimitError(msg)) => Response.conflict(msg)
```

---

## HTTP: The Client Library

The HTTP library provides client-side HTTP functionality. It is used by Tempest (the browser) and any Ritz application that needs to make outbound requests.

---

## Request Lifecycle

A request from browser to response:

```
1. Client connects to port 443
2. Valet accepts connection (io_uring)
3. TLS handshake (Cryptosec)
4. HTTP request parsed
5. Valet passes request to Zeus via IPC
6. Zeus routes to a Spire worker
7. Spire Presenter handles route
8. Service executes business logic
9. Repository queries Mausoleum
10. Response built and returned up the chain
11. Valet sends response (zero-copy if static)
12. gzip compression applied (Squeeze)
```

---

## See Also

- [Valet project page](../projects/valet.md)
- [Zeus project page](../projects/zeus.md)
- [Spire project page](../projects/spire.md)
- [HTTP project page](../projects/http.md)
- [Security Subsystem](security.md) — TLS and compression
- [Data Subsystem](data.md) — Mausoleum and Tome
- [Architecture overview](../architecture.md)
