# `ritzlib.net` and `ritzlib.async_net` duplicate `sys_*` syscall wrappers

> **STATUS: RESOLVED** in the wedge that landed shortly after this doc
> was written.  `ritzlib/async_net.ritz` now imports the duplicated
> wrappers from `ritzlib.net` instead of declaring its own.  Kept here
> as historical context for the fix.

## Summary

`ritz/ritzlib/net.ritz` and `ritz/ritzlib/async_net.ritz` both declare the
exact same set of socket syscall wrappers as `pub fn`.  The two modules
cannot be linked into the same binary — the linker rejects the duplicate
symbols.

This blocks any project that wants to link in **both** valet (which uses
`async_net` indirectly via `ritzlib.async_tasks`) **and** mausoleum's
`lib/client.ritz` (which uses `net`).  In particular, it blocks the obvious
"valet handler calls mausoleum client_get(...)" integration.

## Symbols affected

```
sys_socket    sys_bind    sys_listen  sys_accept   sys_accept4
sys_connect   sys_setsockopt           sys_getsockopt
sys_shutdown  sys_getsockname
```

(net.ritz also has `sys_epoll_*`; async_net.ritz also has `sys_send` /
`sys_recv` — both unique to their module.)

## Reproduction

```bash
# Repro 1: declare both as deps in any package's ritz.toml,
# then import both directly or transitively, build:
python3 projects/ritz/build.py build <pkg>
# → /usr/bin/ld: /tmp/net_*.o: in function `sys_listen':
#    multiple definition of `sys_listen';
#    /tmp/async_net_*.o: first defined here
```

The blast radius hit during the valet+mausoleum e2e wedge: adding
`mausoleum = { path = "../mausoleum", sources = ["lib"] }` to
`projects/valet/ritz.toml` and importing `mausoleum.client` from
`projects/valet/src/main.ritz`.

## Fix sketch

The cleanest fix is to **extract the syscall wrappers into a single module**
— say `ritzlib/sys_socket.ritz` — and have both `net.ritz` and `async_net.ritz`
re-export from there.  Both modules would `import ritzlib.sys_socket` and
either alias the wrappers or expose typed APIs that delegate.

Alternative: **rename** one set of wrappers (e.g. `async_net.ritz` →
`async_sys_listen`).  Mechanical, no semantic change, but every caller of
the renamed set has to update.

The first option is preferred — it's the right factoring even if duplication
weren't a problem.

## Until it's fixed

`projects/valet/src/main.ritz` reads `wiki/<slug>.md` directly from disk for
the `/docs/:slug` route, instead of calling `mausoleum.client_get(...)`.  See
the comment block on `handle_docs` and the placeholder block in
`projects/valet/ritz.toml`.

A separate, unrelated cleanup landed alongside this discovery: mausoleum's
`Span` struct in `lib/m7m_types.ritz` was renamed to `ByteSpan` to avoid
clashing with `ritzlib.span.Span<T>` once mausoleum is pulled in as a dep.
Keep that.
