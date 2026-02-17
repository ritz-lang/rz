# Zeus

*King of the application tier.*

Application server and process manager for the Ritz web stack. Design phase.

---

## Overview

Zeus manages the lifecycle of Ritz application workers. It sits between Valet (the HTTP server) and Spire (the web framework), providing process supervision, load balancing, and zero-downtime deployments.

Zeus is the Ritz equivalent of Gunicorn, Puma, PM2, or Unicorn — but written in Ritz, with direct integration into the Ritz ecosystem.

---

## Where It Fits

```
SPIRE (application code)
        │
        ▼
      ZEUS (process manager)
        │ Spawns and manages N worker processes
        │ Balances connections across workers
        ▼
     VALET (HTTP server)
        │ Passes requests via IPC
```

---

## Responsibilities

### Process Management

```
Zeus supervisor process
    ├── Worker 0 (PID: 12345)
    ├── Worker 1 (PID: 12346)
    ├── Worker 2 (PID: 12347)
    └── Worker 3 (PID: 12348)
```

- Spawns N worker processes on startup
- Monitors worker health (heartbeat, memory, request count)
- Restarts crashed workers automatically
- Gracefully drains workers on shutdown (finish in-flight requests)

### Load Balancing

Zeus distributes incoming connections across workers. The default strategy is round-robin, but least-connections is also supported for workloads with variable request durations.

### Zero-Downtime Deploys

```
Phase 1: Old workers running (serving traffic)
         [Old W0] [Old W1] [Old W2] [Old W3]

Phase 2: Start new workers (not yet serving)
         [Old W0] [Old W1] [New W0] [New W1]

Phase 3: New workers ready, drain old workers
         Sending traffic to: [New W0] [New W1]
         Draining: [Old W0] [Old W1]

Phase 4: Old workers finish and exit
         [New W0] [New W1] [New W2] [New W3]
```

No dropped requests during deployment.

### IPC via Shared Memory

Zeus enables zero-copy communication between workers via shared memory ring buffers. Tome can operate in IPC mode where cache reads bypass the network entirely.

---

## Configuration

```toml
[zeus]
workers = 4
max_requests_per_worker = 10000   # Restart after N requests (memory safety)
restart_policy = "on-crash"        # or "always", "on-error"

[zeus.deploy]
strategy = "rolling"               # or "blue-green"
drain_timeout = 30                 # Seconds to wait for in-flight requests

[zeus.health]
check_interval = 5                 # Seconds between heartbeats
check_timeout = 3                  # Kill worker if no response
```

---

## Starting a Zeus-Managed Application

```bash
# Start with 4 workers
zeus start --workers 4 ./myapp

# Start from config file
zeus start --config zeus.toml

# Zero-downtime reload (rolling restart)
zeus reload

# Graceful shutdown
zeus stop --drain
```

---

## Programmatic API

```ritz
import zeus { Zeus, WorkerConfig }

fn main() -> Result<(), Error>
    var server = Zeus.new(WorkerConfig {
        workers: 4,
        entry: "myapp::serve",
        max_requests: 10000,
    })

    server.set_shutdown_signal(Signal.SIGTERM)
    server.start()?

    Ok(())
```

---

## Current Status

Design phase. Architecture defined. Implementation pending.

---

## Related Projects

- [Valet](valet.md) — HTTP server that Zeus manages workers for
- [Spire](spire.md) — Web framework that runs under Zeus
- [Tome](tome.md) — Can operate in zero-copy IPC mode via Zeus
- [Web Stack Subsystem](../subsystems/web-stack.md)
