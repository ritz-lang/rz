# Archived packages

Packages taken out of the workspace. `rz.toml` `members` covers `projects/**`
and `bench/...` only, so nothing here is built or tested by `rz build --all`,
`rz test --all` or any CI gate. **This code is not maintained and will rot.**
Treat it as history with a working tree, not as a dependency.

To revive one, `git mv archive/<name> projects/<name>` (its manifest paths,
such as `../ritz/ritzlib`, are relative to `projects/`), make it build and
test green, and say why in the commit.

Archived by AGAST #1875 (LARB v4 review/4/packages.md M10).

## spectree

An in-memory spec/plan tree library (`lib/` plus five test files, 91 tests
passing when archived). Its README promised an MCP server and an executable;
neither existed (`[build] test_only = true`, no `[[bin]]`). No package
imported it. Keeping it in the workspace cost a gate slot every run for a
library with no consumer. AGAST tracks task planning, which was spectree's
intended job.

## angelo-simple

A 55-line program that writes a 50×50 grey gradient as a PGM. Despite the
name, it never imported angelo: it exercised only `ritzlib.gvec` and raw
syscalls, so it was not a smoke test of anything angelo does. angelo's own
`[[bin]]` demos (`projects/angelo/ritz.toml`) and its test suite render real
glyphs from `tests/fixtures/aadhunik.ttf` and cover the path it claimed to.
