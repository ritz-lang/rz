# Mausoleum

*Where data is entombed forever.*

Mausoleum is the embedded document database for the Ritz ecosystem.  It is
intended to back this very `/docs/:slug` handler — but right now the pages
are read directly from disk (`wiki/{slug}.md`) because of a ritzlib
duplicate-symbol bug between `net.ritz` and `async_net.ritz`.

## What works today

- B-tree storage with WAL
- 373 unit tests passing
- TCP wire protocol over X25519 + ChaCha20-Poly1305
- `wiki-seed --seed` populates a working content set

## What's next

- Resolve the ritzlib net/async_net symbol collision
- Re-link `mausoleum` into valet as a dep
- Replace the file-based stub here with `client_get(slug → doc → content)`
