# ritz.toml specification: moved

The ritz.toml / rz.toml specification is now generated from the schema the
build validates against:
[`projects/ritz/docs/RITZ_TOML_SPEC.md`](../../ritz/docs/RITZ_TOML_SPEC.md)
(schema: `projects/ritz/manifest.py`, AGAST #1837).

The hand-written copy that lived here documented features nothing implemented
(`[build]` custom commands, `[[test]]` entry points, `[dev-dependencies]`) and
missed keys that were read. A key that is not in the generated spec now fails
the build.
