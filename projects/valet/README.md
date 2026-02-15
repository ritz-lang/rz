# Valet

A high-performance async HTTP server written in [Ritz](https://github.com/ritz-lang/ritz).

## Features

- **Async I/O** - Built on Linux io_uring for minimal syscall overhead
- **Zero-copy parsing** - HTTP/1.1 request parsing without allocations
- **Multi-process** - Worker processes with SO_REUSEPORT load balancing
- **Keep-alive** - Connection reuse for reduced latency
- **Vectored I/O** - Zero-copy responses via writev

## Requirements

- Linux 5.1+ (io_uring support)
- Linux 5.19+ for multishot accept (`-m` flag)
- Ritz compiler (sibling `langdev` directory)
- clang-19

## Quick Start

```bash
# Set Ritz compiler path
export RITZ_PATH=/path/to/langdev

# Build
./build.sh

# Run
./valet

# Test
curl http://localhost:8080/
```

## Usage

```
./valet [options]

Options:
  -p, --port PORT     Listen port (default: 8080)
  -w, --workers N     Number of worker processes (default: 1)
  -m, --multishot     Use multishot accept (kernel 5.19+)
  -h, --help          Show help message

Examples:
  ./valet                    # Single worker on port 8080
  ./valet -p 3000            # Custom port
  ./valet -w 4               # 4 workers for multi-core
  ./valet -m -w 4            # 4 workers with multishot accept
```

## Benchmarks

Test with [wrk](https://github.com/wg/wrk):

```bash
# Start server with 4 workers
./valet -w 4 -m

# Benchmark
wrk -t4 -c100 -d10s http://localhost:8080/
```

## Project Structure

```
valet/
├── src/
│   └── main.ritz        # Entry point, CLI parsing
├── lib/
│   ├── server.ritz      # Server core, connection handling
│   ├── request.ritz     # HTTP request parser
│   └── response.ritz    # HTTP response builder
├── tests/
│   ├── run_all.sh       # Test runner
│   ├── test_basic.sh    # Basic HTTP tests
│   ├── test_multishot.sh
│   └── test_workers.sh
├── static/              # Static files (for testing)
├── build.sh             # Build script
├── CLAUDE.md            # Development context
└── README.md
```

## Endpoints

| Path | Description |
|------|-------------|
| `/` | Hello World (benchmark endpoint) |
| `/hello` | Hello from Valet |
| `/iov` | Hello World via vectored I/O |
| `/json` | JSON response |

## Roadmap

- [ ] Routing framework with pattern matching
- [ ] Static file serving
- [ ] Request body parsing
- [ ] Middleware system
- [ ] Graceful shutdown

## License

MIT
