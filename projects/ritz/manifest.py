"""The ritz.toml / rz.toml schema, its strict validator, and the spec generator.

One description of every manifest key is the source of truth for three
things (AGAST #1837):

* **Validation.** `load(path)` parses a manifest and rejects any key the
  schema does not name, or a value of the wrong type, as
  ``<file>:<line>: <message>``. `rz build`, `rz test` and build.py all load
  manifests through it, so a misspelt key fails the build instead of being
  silently ignored.
* **The spec.** ``python3 manifest.py --spec`` renders docs/RITZ_TOML_SPEC.md.
  ``make check-manifest-spec`` fails if the committed copy has drifted.
* **Liveness.** Every key names the functions that read it (`read_by`).
  tools/test_manifest_schema.py checks that each named function really
  reads the key, so the schema (and therefore every manifest it accepts)
  cannot carry a key that nothing reads.

Standard library only: rz and resolve.py import this without loading the
compiler.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib


# ---------------------------------------------------------------------------
# Schema nodes
# ---------------------------------------------------------------------------

# Value types, as written in the spec.
STRING = "string"
BOOL = "bool"
INTEGER = "integer"
STRING_LIST = "string list"
STRING_OR_LIST = "string or string list"


@dataclass(frozen=True)
class Value:
    """A scalar or list value."""
    type: str
    doc: str
    read_by: tuple[str, ...]
    default: str | None = None
    required: bool = False


@dataclass(frozen=True)
class Table:
    """A table with a fixed set of keys.

    `self_named` describes the `[bin.NAME]` quirk: a sub-table of an array
    entry keyed by that entry's own `name` value.
    """
    doc: str
    fields: dict[str, Node] = field(default_factory=dict)
    read_by: tuple[str, ...] = ()
    self_named: Table | None = None
    required: bool = False


@dataclass(frozen=True)
class Map:
    """A table whose keys are chosen by the author (dependency names, paths).

    `shorthand`, if set, is a scalar form also accepted for a value
    (`dep = "../path"` for `dep = { path = "../path" }`).
    """
    doc: str
    key_doc: str
    value: Table | Value
    read_by: tuple[str, ...]
    shorthand: Value | None = None


@dataclass(frozen=True)
class Array:
    """An array of tables (`[[bin]]`)."""
    doc: str
    item: Table
    read_by: tuple[str, ...]


Node = Value | Table | Map | Array


# Reader locations, as "<repo-relative file>::<function>".
BUILD = "projects/ritz/build.py"
RESOLVE = "projects/ritz/resolve.py"
RZ = "rz"

_SOURCES_READERS = (f"{BUILD}::plan_binaries", f"{BUILD}::build_package",
                    f"{RESOLVE}::package_import_namespaces")

_PROFILE_KEYS = {
    "opt-level": Value(INTEGER, "LLVM optimisation level, 0-3.",
                       (f"{BUILD}::get_build_profile",), default="0"),
    "debug": Value(BOOL, "Emit debug info.",
                   (f"{BUILD}::get_build_profile",), default="true"),
    "lto": Value(BOOL, "Link-time optimisation.",
                 (f"{BUILD}::get_build_profile",), default="false"),
}


PACKAGE_SCHEMA = Table(
    doc="A package manifest: `ritz.toml` at the root of every package.",
    fields={
        "sources": Value(
            STRING_OR_LIST,
            "Source roots, relative to the package. Also accepted under "
            "[package] or [build]; the first one present wins, in the order "
            "top level, [package], [build].",
            _SOURCES_READERS, default='["src"]'),
        "package": Table(
            "Package identity.",
            {
                "name": Value(
                    STRING, "Package name. Also its import namespace and, "
                    "with no [[bin]] or [[lib]], its binary's name.",
                    (f"{BUILD}::plan_binaries", f"{BUILD}::build_package",
                     f"{RESOLVE}::package_import_namespaces", f"{RZ}::cmd_list"),
                    required=True),
                "version": Value(STRING, "Package version, shown by `rz list`.",
                                 (f"{RZ}::cmd_list",)),
                "description": Value(STRING, "One line, shown by `rz list`.",
                                     (f"{RZ}::cmd_list",)),
                "sources": Value(STRING_OR_LIST, "See top-level `sources`.",
                                 _SOURCES_READERS),
            },
            read_by=(f"{BUILD}::plan_binaries", f"{RZ}::cmd_list"),
            required=True),
        "build": Table(
            "Build settings. `opt-level`, `debug` and `lto` are the base every "
            "[profile.*] overrides.",
            {
                "sources": Value(STRING_OR_LIST, "See top-level `sources`.",
                                 _SOURCES_READERS),
                "test_only": Value(
                    BOOL, "The package has tests and no binaries or libraries: "
                    "`build` skips it, `test` runs it.",
                    (f"{BUILD}::plan_binaries", f"{BUILD}::discover_test_files"),
                    default="false"),
                **_PROFILE_KEYS,
            },
            read_by=(f"{BUILD}::plan_binaries", f"{BUILD}::get_build_profile")),
        "profile": Table(
            "Per-profile overrides of [build] `opt-level`, `debug` and `lto`. "
            "There are two profiles: `--release` selects `release`, anything "
            "else `debug`.",
            {
                "debug": Table("The default profile.", dict(_PROFILE_KEYS),
                               read_by=(f"{BUILD}::get_build_profile",)),
                "release": Table("`build` / `test --release`.",
                                 dict(_PROFILE_KEYS),
                                 read_by=(f"{BUILD}::cmd_build",
                                          f"{BUILD}::cmd_test")),
            },
            read_by=(f"{BUILD}::get_build_profile",)),
        "dependencies": Map(
            "Packages this one imports. Each is put on RITZ_PATH and its "
            "dependencies are followed transitively.",
            "dependency name (its import namespace)",
            Table("One dependency.", {
                "path": Value(STRING, "Package directory, relative to this one.",
                              (f"{RESOLVE}::parse_dependencies",), required=True),
                "sources": Value(
                    STRING_OR_LIST, "The dependency's source roots. Defaults to "
                    "the `sources` its own ritz.toml declares.",
                    (f"{RESOLVE}::parse_dependencies",)),
            }),
            (f"{RESOLVE}::parse_dependencies",),
            shorthand=Value(STRING, 'Shorthand for `{ path = "..." }` with '
                            '`sources = ["src"]`.',
                            (f"{RESOLVE}::parse_dependencies",))),
        "lib": Array(
            "A library: every module under `sources`, compiled and archived. "
            "A package with [[lib]] and no [[bin]] builds no binary.",
            Table("One library.", {
                "name": Value(STRING, "Library name (archived as lib<name>).",
                              (f"{BUILD}::plan_binaries",), required=True),
                "sources": Value(
                    STRING_OR_LIST, "Source roots; a `!path` entry excludes a "
                    "file. Defaults to the package's `sources`.",
                    (f"{BUILD}::plan_binaries",)),
            }),
            (f"{BUILD}::plan_binaries",)),
        "bin": Array(
            "A binary. With neither [[bin]] nor [[lib]] the package builds one "
            "binary named after it, from `main::main` under its sources.",
            Table(
                "One binary. Its source is `entry`, else `path`, else "
                "src/<name>.ritz.",
                {
                    "name": Value(STRING, "Binary name.",
                                  (f"{BUILD}::plan_binaries",), required=True),
                    "entry": Value(STRING, '`"module::function"`, resolved under '
                                   "`sources`.", (f"{BUILD}::plan_binaries",)),
                    "path": Value(STRING, "Source file, relative to the package. "
                                  "A non-.ritz path is listed and skipped.",
                                  (f"{BUILD}::plan_binaries",)),
                    "sources": Value(STRING_OR_LIST, "Source roots for this "
                                     "binary. Defaults to the package's.",
                                     (f"{BUILD}::plan_binaries",)),
                    "freestanding": Value(BOOL, "No libc, no runtime.",
                                          (f"{BUILD}::plan_binaries",),
                                          default="false"),
                    "target": Value(STRING, "LLVM target triple. Empty means "
                                    "the host.", (f"{BUILD}::plan_binaries",),
                                    default='""'),
                    "target_os": Value(STRING, "Target OS for platform-specific "
                                       "modules (e.g. `harland`, `uefi`).",
                                       (f"{BUILD}::plan_binaries",),
                                       default='""'),
                    "link_runtime": Value(BOOL, "Link the Ritz runtime's _start.",
                                          (f"{BUILD}::plan_binaries",),
                                          default="false"),
                    "main_args": Value(INTEGER, "Arguments main() takes: 0, 2 "
                                       "or 3.", (f"{BUILD}::plan_binaries",),
                                       default="0"),
                },
                self_named=Table(
                    "`[bin.NAME]`, where NAME is this entry's `name`: "
                    "per-binary link and codegen settings.",
                    {
                        "linker": Table("Linking.", {
                            "script": Value(STRING, "Linker script, relative "
                                            "to the package.",
                                            (f"{BUILD}::plan_binaries",)),
                        }, read_by=(f"{BUILD}::plan_binaries",)),
                        "asm": Table("Assembly.", {
                            "files": Value(STRING_LIST, "Assembly files to "
                                           "assemble and link in.",
                                           (f"{BUILD}::plan_binaries",)),
                        }, read_by=(f"{BUILD}::plan_binaries",)),
                        "flags": Table("Code generation.", {
                            "code-model": Value(STRING, "LLVM code model "
                                                "(e.g. `kernel`).",
                                                (f"{BUILD}::plan_binaries",),
                                                default='""'),
                            "no-red-zone": Value(BOOL, "Disable the red zone.",
                                                 (f"{BUILD}::plan_binaries",),
                                                 default="false"),
                            "pic": Value(BOOL, "Position-independent code.",
                                         (f"{BUILD}::plan_binaries",),
                                         default="false"),
                        }, read_by=(f"{BUILD}::plan_binaries",)),
                    })),
            (f"{BUILD}::plan_binaries",)),
        "test": Table(
            "Test discovery. `rz test` always runs test/*.ritz, the "
            "package's own test_*.ritz and test.sh, plus every module with a "
            "`[[test]]` function under src/ and the directories listed here. "
            "There is no `[[test]]` array: a test is a `[[test]]` function, "
            "not a manifest entry.",
            {
                "sources": Value(STRING_LIST, "Extra directories searched "
                                 "(recursively) for `[[test]]` modules.",
                                 (f"{BUILD}::_declared_test_source_files",)),
            },
            read_by=(f"{BUILD}::_declared_test_source_files",)),
    })


WORKSPACE_SCHEMA = Table(
    doc="The workspace manifest: `rz.toml` at the repository root, read by `rz`.",
    fields={
        "workspace": Table(
            "The workspace.",
            {
                "name": Value(STRING, "Workspace name, shown by `rz list`.",
                              (f"{RZ}::cmd_list",)),
                "version": Value(STRING, "Workspace version, shown by `rz list`.",
                                 (f"{RZ}::cmd_list",)),
                "description": Value(STRING, "Shown by `rz list`.",
                                     (f"{RZ}::cmd_list",)),
                "members": Value(
                    STRING_LIST, "Globs (`**` walks any depth) naming the "
                    "packages `--all` sweeps. A pattern that matches nothing is "
                    "an error.", (f"{RZ}::discover_projects",)),
                "exclude": Map(
                    "Packages under a member pattern that `--all` skips, each "
                    "with the gate that covers it instead. An empty reason, or "
                    "an entry that matches no package, is an error.",
                    "directory, relative to the workspace",
                    Value(STRING, "Why it is excluded, and what covers it.",
                          (f"{RZ}::workspace_exclusions",)),
                    (f"{RZ}::workspace_exclusions",)),
            },
            read_by=(f"{RZ}::discover_projects", f"{RZ}::cmd_list")),
        "build": Table(
            "Defaults for `rz build` / `rz test`.",
            {
                "parallel": Value(BOOL, "`false` runs one job at a time.",
                                  (f"{RZ}::resolve_jobs",), default="true"),
                "max_jobs": Value(INTEGER, "Worker count when `-j` is not given.",
                                  (f"{RZ}::resolve_jobs",),
                                  default="os.cpu_count()"),
            },
            read_by=(f"{RZ}::resolve_jobs",)),
        "ci": Table(
            "CI gate policy.",
            {
                "known_failing": Table(
                    "Known failures. There is deliberately no `test` table.",
                    {
                        "build": Map(
                            "Projects whose `rz build --all` failure is advisory. "
                            "An excused project that passes fails the gate.",
                            "project id",
                            Value(STRING, "Reason; must cite an AGAST task "
                                  "(`#NNNN`).",
                                  (f"{RZ}::known_failing_from_config",)),
                            # The kind is a parameter: its callers name it.
                            (f"{RZ}::cmd_build", f"{RZ}::cmd_test")),
                    },
                    read_by=(f"{RZ}::known_failing_from_config",)),
            },
            read_by=(f"{RZ}::known_failing_from_config",)),
    })


SCHEMAS = {"ritz.toml": PACKAGE_SCHEMA, "rz.toml": WORKSPACE_SCHEMA}


def schema_for(path: Path) -> Table:
    """rz.toml gets the workspace schema; any other name, the package one."""
    return WORKSPACE_SCHEMA if Path(path).name == "rz.toml" else PACKAGE_SCHEMA


# ---------------------------------------------------------------------------
# Line numbers
# ---------------------------------------------------------------------------

_KEY_PART = r'(?:[A-Za-z0-9_-]+|"(?:[^"\\]|\\.)*"|\'[^\']*\')'
_DOTTED = rf'{_KEY_PART}(?:\s*\.\s*{_KEY_PART})*'
_HEADER_RE = re.compile(rf'^\s*(\[\[?)\s*({_DOTTED})\s*\]\]?')
_ASSIGN_RE = re.compile(rf'^\s*({_DOTTED})\s*=')
_PART_RE = re.compile(_KEY_PART)


def _split_key(dotted: str) -> tuple[str, ...]:
    parts = []
    for m in _PART_RE.finditer(dotted):
        p = m.group(0)
        if p[0] in "\"'":
            p = p[1:-1]
        parts.append(p)
    return tuple(parts)


def key_lines(text: str) -> dict[tuple, int]:
    """Map each key path to the 1-based line that defines it.

    A path is a tuple of keys and array indices: ("bin", 2, "name"). Keys
    inside an inline table or a multi-line value have no entry of their own;
    `line_of` falls back to the nearest ancestor that has one. This is a
    line scanner, not a TOML parser: it only has to be right for files
    tomllib has already accepted.
    """
    lines: dict[tuple, int] = {}
    array_counts: dict[tuple, int] = {}
    current: tuple = ()
    in_multiline = None  # the open triple quote, if any
    depth = 0            # open [ / { brackets of a multi-line value
    for lineno, line in enumerate(text.splitlines(), start=1):
        if in_multiline:
            if line.count(in_multiline) % 2 == 1:
                in_multiline = None
            continue
        if depth > 0:
            depth += _bracket_delta(line)
            continue
        m = _HEADER_RE.match(line)
        if m:
            key = _split_key(m.group(2))
            if m.group(1) == "[[":
                idx = array_counts.get(key, 0)
                array_counts[key] = idx + 1
                lines.setdefault(key, lineno)
                current = _resolve_arrays(key, array_counts) + (idx,)
            else:
                current = _resolve_arrays(key, array_counts)
            lines.setdefault(current, lineno)
            continue
        m = _ASSIGN_RE.match(line)
        if m:
            path = current + _split_key(m.group(1))
            lines.setdefault(path, lineno)
            rest = line[m.end():]
            for q in ('"""', "'''"):
                if rest.count(q) % 2 == 1:
                    in_multiline = q
            if not in_multiline:
                depth = max(0, _bracket_delta(rest))
    return lines


def _resolve_arrays(key: tuple, counts: dict[tuple, int]) -> tuple:
    """`[bin.harland.linker]` after the third `[[bin]]` is bin[2].harland.linker."""
    out: tuple = ()
    for i, part in enumerate(key):
        out += (part,)
        prefix = key[:i + 1]
        if prefix != key and prefix in counts:
            out += (counts[prefix] - 1,)
    return out


def _bracket_delta(s: str) -> int:
    s = re.sub(r'"(?:[^"\\]|\\.)*"|\'[^\']*\'', "", s)
    s = s.split("#", 1)[0]
    return s.count("[") + s.count("{") - s.count("]") - s.count("}")


def line_of(lines: dict[tuple, int], path: tuple) -> int:
    while path:
        if path in lines:
            return lines[path]
        path = path[:-1]
    return 1


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ManifestError(Exception):
    """A manifest the schema rejects. str() is `<file>:<line>: <message>`."""

    def __init__(self, path, line: int, message: str):
        self.path = Path(path)
        self.line = line
        self.message = message
        super().__init__(f"{path}:{line}: {message}")


def _type_ok(kind: str, v) -> bool:
    if kind == STRING:
        return isinstance(v, str)
    if kind == BOOL:
        return isinstance(v, bool)
    if kind == INTEGER:
        return isinstance(v, int) and not isinstance(v, bool)
    if kind == STRING_LIST:
        return isinstance(v, list) and all(isinstance(x, str) for x in v)
    if kind == STRING_OR_LIST:
        return isinstance(v, str) or _type_ok(STRING_LIST, v)
    raise ValueError(kind)


def _where(path: tuple) -> str:
    """Display a key path as TOML: bin[2].harland.linker -> [bin.harland.linker]."""
    keys = [p for p in path if not isinstance(p, int)]
    return "[" + ".".join(keys) + "]" if keys else "the top level"


def _dotted(path: tuple) -> str:
    return ".".join(p for p in path if not isinstance(p, int))


def validate(data: dict, schema: Table, lines: dict[tuple, int] | None = None
             ) -> list[tuple[int, str]]:
    """Every (line, message) the schema has against `data`, in file order."""
    lines = lines or {}
    errors: list[tuple[int, str]] = []

    def err(path: tuple, msg: str) -> None:
        errors.append((line_of(lines, path), msg))

    def check(node: Node, value, path: tuple) -> None:
        if isinstance(node, Value):
            if not _type_ok(node.type, value):
                err(path, f"'{_dotted(path)}' must be a {node.type}, "
                          f"got {type(value).__name__} {value!r}")
        elif isinstance(node, Table):
            if not isinstance(value, dict):
                err(path, f"'{_dotted(path)}' must be a table")
                return
            check_table(node, value, path)
        elif isinstance(node, Map):
            if not isinstance(value, dict):
                err(path, f"'{_dotted(path)}' must be a table")
                return
            for k, v in value.items():
                if node.shorthand is not None and not isinstance(v, dict):
                    check(node.shorthand, v, path + (k,))
                else:
                    check(node.value, v, path + (k,))
        elif isinstance(node, Array):
            if not isinstance(value, list) or not all(isinstance(e, dict) for e in value):
                err(path, f"'{_dotted(path)}' must be an array of tables "
                          f"([[{_dotted(path)}]])")
                return
            for i, entry in enumerate(value):
                check(node.item, entry, path + (i,))

    def check_table(table: Table, value: dict, path: tuple) -> None:
        own_name = value.get("name") if table.self_named else None
        for k, v in value.items():
            if k in table.fields:
                check(table.fields[k], v, path + (k,))
            elif table.self_named is not None and k == own_name:
                check(table.self_named, v, path + (k,))
            else:
                allowed = sorted(table.fields)
                if table.self_named is not None:
                    allowed.append(f"{own_name or 'NAME'} (= name)")
                err(path + (k,), f"unknown key '{k}' in {_where(path)} "
                                 f"(allowed: {', '.join(allowed)})")
        for k, node in table.fields.items():
            if getattr(node, "required", False) and k not in value:
                err(path, f"{_where(path)} is missing required key '{k}'")

    check_table(schema, data, ())
    errors.sort(key=lambda e: e[0])
    return errors


def loads(text: str, path, schema: Table | None = None) -> dict:
    """Parse and validate manifest text. Raises ManifestError on the first
    problem (TOML syntax included), naming `path` and the line."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        m = re.search(r"line (\d+)", str(e))
        raise ManifestError(path, int(m.group(1)) if m else 1, str(e)) from None
    errors = validate(data, schema or schema_for(Path(path)), key_lines(text))
    if errors:
        line, msg = errors[0]
        extra = f" (and {len(errors) - 1} more)" if len(errors) > 1 else ""
        raise ManifestError(path, line, msg + extra)
    return data


def load(path) -> dict:
    """Read, parse and validate a ritz.toml or rz.toml."""
    path = Path(path)
    return loads(path.read_text(encoding="utf-8"), path)


# ---------------------------------------------------------------------------
# Spec generation
# ---------------------------------------------------------------------------

_SPEC_INTRO = """\
<!-- GENERATED by projects/ritz/manifest.py. Do not edit: change the schema
     there and run `make -C projects/ritz manifest-spec`. CI runs
     `make check-manifest-spec`, which fails if this file has drifted. -->

# ritz.toml / rz.toml specification

Every key a Ritz manifest may contain. The schema in
`projects/ritz/manifest.py` is the source of truth: `rz` and `build.py` load
every manifest through it, so **an unknown key, or a value of the wrong type,
fails the build** as `<file>:<line>: <message>`. Each key lists the code that
reads it; `tools/test_manifest_schema.py` checks those functions really do,
and that every committed manifest validates.

To add a key: add it to the schema with its reader, implement the read,
regenerate this file.

Two manifests exist:

* `ritz.toml`, one per package.
* `rz.toml`, one per workspace (the repository root), read only by `rz`.
"""


def _type_cell(node: Node) -> str:
    if isinstance(node, Value):
        return node.type
    if isinstance(node, Array):
        return "array of tables"
    return "table"


def _readers(read_by: tuple[str, ...], sep: str = "<br>") -> str:
    return sep.join(f"`{r.replace('::', ' ')}`" for r in read_by)


def _render_table(title: str, table: Table, out: list[str],
                  lead: str | None = None) -> None:
    """One section per table: a key table, then sections for sub-tables.
    `lead` is an array's own doc, printed before its entries' doc."""
    out.append(f"### `{title}`\n")
    if lead:
        out.append(lead + "\n")
    out.append(table.doc + "\n")
    scalars = [(k, n) for k, n in table.fields.items() if isinstance(n, Value)]
    if scalars:
        out.append("| Key | Type | Default | Read by | Description |")
        out.append("|---|---|---|---|---|")
        for k, n in scalars:
            default = "**required**" if n.required else (
                f"`{n.default}`" if n.default is not None else "")
            out.append(f"| `{k}` | {n.type} | {default} | {_readers(n.read_by)} "
                       f"| {n.doc} |")
        out.append("")
    base = title.strip("[]")
    for k, n in table.fields.items():
        sub = f"{base}.{k}" if base else k
        if isinstance(n, Table):
            _render_table(f"[{sub}]", n, out)
        elif isinstance(n, Array):
            _render_table(f"[[{sub}]]", n.item, out, lead=n.doc)
        elif isinstance(n, Map):
            key = f"<{n.key_doc}>"
            out.append(f"### `[{sub}]`\n")
            out.append(n.doc + "\n")
            if isinstance(n.value, Value):
                out.append(f"Each key is a {n.key_doc}; each value a "
                           f"{n.value.type}: {n.value.doc} Read by "
                           f"{_readers(n.read_by, ', ')}.\n")
            else:
                shorthand = (f" A value may also be a {n.shorthand.type}: "
                             f"{n.shorthand.doc}" if n.shorthand else "")
                out.append(f"Each key is a {n.key_doc}; each value a table, "
                           f"described next.{shorthand} Read by "
                           f"{_readers(n.read_by, ', ')}.\n")
                _render_table(f"[{sub}.{key}]", n.value, out)
    if table.self_named is not None:
        _render_table(f"[{base}.NAME]", table.self_named, out)


def render_spec() -> str:
    out = [_SPEC_INTRO]
    out.append("## ritz.toml\n")
    _render_table("", PACKAGE_SCHEMA, out)
    out.append("## rz.toml\n")
    _render_table("", WORKSPACE_SCHEMA, out)
    text = "\n".join(out)
    # The root table renders as "### ``"; give it a readable name.
    text = text.replace("### ``\n\nA package manifest", "### Top level\n\nA package manifest")
    text = text.replace("### ``\n\nThe workspace manifest", "### Top level\n\nThe workspace manifest")
    return text.rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--spec", action="store_true", help="print the generated spec")
    g.add_argument("--check-spec", metavar="SPEC",
                   help="exit 1, with a diff, if SPEC is not the generated spec")
    g.add_argument("--check", nargs="+", metavar="MANIFEST",
                   help="validate manifests; exit 1 if any is bad")
    args = p.parse_args(argv)
    if args.spec:
        sys.stdout.write(render_spec())
        return 0
    if args.check_spec:
        import difflib
        committed = Path(args.check_spec).read_text(encoding="utf-8")
        fresh = render_spec()
        if committed == fresh:
            print(f"✓ {args.check_spec} matches manifest.py")
            return 0
        sys.stdout.writelines(difflib.unified_diff(
            committed.splitlines(True), fresh.splitlines(True),
            args.check_spec, "manifest.py --spec"))
        print(f"❌ {args.check_spec} has drifted from manifest.py. Edit the "
              "schema there, then: make -C projects/ritz manifest-spec")
        return 1
    status = 0
    for m in args.check:
        try:
            load(m)
        except ManifestError as e:
            print(e, file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
