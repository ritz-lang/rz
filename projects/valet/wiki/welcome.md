# Welcome to Valet

This is a wiki page served dynamically by **Valet**, a high-performance HTTP/1.1
server written in [Ritz](https://github.com/ritz-lang/rz).

## Try these pages

- [`/docs/welcome`](/docs/welcome) — this page
- [`/docs/getting-started`](/docs/getting-started)
- [`/docs/ritz`](/docs/ritz)
- [`/docs/mausoleum`](/docs/mausoleum)

## How it works

The handler in `src/main.ritz` reads `wiki/{slug}.md` from disk and returns
the contents.  Eventually this lookup will be backed by [Mausoleum][m], the
document database, but a direct cross-project link is currently blocked on
a ritzlib net/async_net symbol collision.

[m]: /docs/mausoleum
