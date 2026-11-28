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
    # Root tables only: retired keys, as {table path: {key: where it went}}.
    # One is still an error, but one that says where the key goes now.
    moved_from: dict[tuple, dict[str, str]] = field(default_factory=dict)
    # Exactly one of these keys must be present (a dependency's `path` or
    # `version`, AGAST #4865).
    one_of: tuple[str, ...] = ()


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
MANIFEST_PY = "projects/ritz/manifest.py"
PIPELINE_PY = "projects/ritz/build_pipeline.py"
CLI_PY = "projects/ritz/build_cli.py"
RESOLVE = "projects/ritz/resolve.py"
RZ = "rz"

# A retired `sources` spelling's error (PACKAGE_SCHEMA.moved_from).
_MOVED_SOURCES = ("`sources` belongs in [package] (AGAST #3894): move it "
                  "under the [package] header")

_PROFILE_KEYS = {
    "opt-level": Value(INTEGER, "LLVM optimisation level, 0-3.",
                       (f"{MANIFEST_PY}::get_build_profile",), default="0"),
    "debug": Value(BOOL, "Emit debug info.",
                   (f"{MANIFEST_PY}::get_build_profile",), default="true"),
    "lto": Value(BOOL, "Link-time optimisation.",
                 (f"{MANIFEST_PY}::get_build_profile",), default="false"),
}


PACKAGE_SCHEMA = Table(
    doc="A package manifest: `ritz.toml` at the root of every package.",
    fields={
        "package": Table(
            "Package identity.",
            {
                "name": Value(
                    STRING, "Package name. Also its import namespace and, "
                    "with no [[bin]] or [[lib]], its binary's name.",
                    (f"{MANIFEST_PY}::plan_binaries", f"{PIPELINE_PY}::build_package",
                     f"{RESOLVE}::package_import_namespaces", f"{RZ}::cmd_list"),
                    required=True),
                "version": Value(STRING, "Package version, shown by `rz list`.",
                                 (f"{RZ}::cmd_list",)),
                "description": Value(STRING, "One line, shown by `rz list`.",
                                     (f"{RZ}::cmd_list",)),
                "sources": Value(
                    STRING_OR_LIST,
                    "Source roots, relative to the package. The only place "
                    "`sources` is read: one at the top level or under [build] "
                    "is an error.",
                    (f"{RESOLVE}::package_sources",), default='["src"]'),
            },
            read_by=(f"{MANIFEST_PY}::plan_binaries", f"{RZ}::cmd_list"),
            required=True),
        "build": Table(
            "Build settings. `opt-level`, `debug` and `lto` are the base every "
            "[profile.*] overrides.",
            {
                "test_only": Value(
                    BOOL, "The package has tests and no binaries or libraries: "
                    "`build` skips it, `test` runs it.",
                    (f"{MANIFEST_PY}::plan_binaries", f"{MANIFEST_PY}::discover_test_files"),
                    default="false"),
                **_PROFILE_KEYS,
            },
            read_by=(f"{MANIFEST_PY}::plan_binaries", f"{MANIFEST_PY}::get_build_profile")),
        "profile": Table(
            "Per-profile overrides of [build] `opt-level`, `debug` and `lto`. "
            "There are two profiles: `--release` selects `release`, anything "
            "else `debug`.",
            {
                "debug": Table("The default profile.", dict(_PROFILE_KEYS),
                               read_by=(f"{MANIFEST_PY}::get_build_profile",)),
                "release": Table("`build` / `test --release`.",
                                 dict(_PROFILE_KEYS),
                                 read_by=(f"{CLI_PY}::cmd_build",
                                          f"{CLI_PY}::cmd_test")),
            },
            read_by=(f"{MANIFEST_PY}::get_build_profile",)),
        "dependencies": Map(
            "Packages this one imports. Each is put on RITZ_PATH and its "
            "dependencies are followed transitively.",
            "dependency name (its import namespace)",
            Table("One dependency: a directory (`path`) or an installed "
                  "package (`version`), exactly one. A `path` directory "
                  "holding `ritz-package.toml` is a package too "
                  "(docs/PACKAGES.md §2).", {
                "path": Value(STRING, "Package directory, relative to this one.",
                              (f"{RESOLVE}::parse_dependencies",)),
                "version": Value(STRING, "An installed package's exact version: "
                                 "`$RITZ_PACKAGES/<name>/<version>/`, put there "
                                 "by `rz install`.",
                                 (f"{RESOLVE}::parse_dependencies",)),
                "source_sha256": Value(STRING, "Pins the package's source tree: "
                                       "its `ritz-package.toml` must record this "
                                       "`source_sha256`.",
                                       (f"{RESOLVE}::parse_dependencies",)),
                "prebuilt": Value(BOOL, "`false`: compile the package from its "
                                  "shipped source, never link its archive.",
                                  (f"{RESOLVE}::parse_dependencies",),
                                  default="true"),
                "sources": Value(
                    STRING_OR_LIST, "The dependency's source roots. Defaults to "
                    "the `sources` its own ritz.toml declares.",
                    (f"{RESOLVE}::parse_dependencies",)),
            }, one_of=("path", "version")),
            (f"{RESOLVE}::parse_dependencies",),
            shorthand=Value(STRING, 'Shorthand for `{ path = "..." }` with '
                            '`sources = ["src"]`.',
                            (f"{RESOLVE}::parse_dependencies",))),
        "lib": Array(
            "A library: every module under `sources`, compiled and archived. "
            "A package with [[lib]] and no [[bin]] builds no binary.",
            Table("One library.", {
                "name": Value(STRING, "Library name (archived as lib<name>).",
                              (f"{MANIFEST_PY}::plan_binaries",), required=True),
                "sources": Value(
                    STRING_OR_LIST, "Source roots; a `!path` entry excludes a "
                    "file. Defaults to the package's `sources`.",
                    (f"{MANIFEST_PY}::plan_binaries",)),
            }),
            (f"{MANIFEST_PY}::plan_binaries",)),
        "bin": Array(
            "A binary. With neither [[bin]] nor [[lib]] the package builds one "
            "binary named after it, from `main::main` under its sources.",
            Table(
                "One binary. Its source is `entry`, else `path`, else "
                "src/<name>.ritz.",
                {
                    "name": Value(STRING, "Binary name.",
                                  (f"{MANIFEST_PY}::plan_binaries",), required=True),
                    "entry": Value(STRING, '`"module::function"`: `module` '
                                   "selects the source file under `sources`; "
                                   "`function` is the target's entry fn, which "
                                   "the file must define (a hosted binary's is "
                                   "`main`).", (f"{MANIFEST_PY}::plan_binaries",)),
                    "path": Value(STRING, "Source file, relative to the package. "
                                  "A non-.ritz path is listed and skipped.",
                                  (f"{MANIFEST_PY}::plan_binaries",)),
                    "sources": Value(STRING_OR_LIST, "Source roots for this "
                                     "binary. Defaults to the package's.",
                                     (f"{MANIFEST_PY}::plan_binaries",)),
                    "freestanding": Value(BOOL, "No libc, no runtime.",
                                          (f"{MANIFEST_PY}::plan_binaries",),
                                          default="false"),
                    "target": Value(STRING, "LLVM target triple. Empty means "
                                    "the host.", (f"{MANIFEST_PY}::plan_binaries",),
                                    default='""'),
                    "target_os": Value(STRING, "Target OS for platform-specific "
                                       "modules (e.g. `harland`, `uefi`).",
                                       (f"{MANIFEST_PY}::plan_binaries",),
                                       default='""'),
                    "link_runtime": Value(BOOL, "Link the Ritz runtime's _start.",
                                          (f"{MANIFEST_PY}::plan_binaries",),
                                          default="false"),
                },
                self_named=Table(
                    "`[bin.NAME]`, where NAME is this entry's `name`: "
                    "per-binary link and codegen settings.",
                    {
                        "linker": Table("Linking.", {
                            "script": Value(STRING, "Linker script, relative "
                                            "to the package.",
                                            (f"{MANIFEST_PY}::plan_binaries",)),
                        }, read_by=(f"{MANIFEST_PY}::plan_binaries",)),
                        "asm": Table("Assembly.", {
                            "files": Value(STRING_LIST, "Assembly files to "
                                           "assemble and link in.",
                                           (f"{MANIFEST_PY}::plan_binaries",)),
                        }, read_by=(f"{MANIFEST_PY}::plan_binaries",)),
                        "flags": Table("Code generation.", {
                            "code-model": Value(STRING, "LLVM code model "
                                                "(e.g. `kernel`).",
                                                (f"{MANIFEST_PY}::plan_binaries",),
                                                default='""'),
                            "no-red-zone": Value(BOOL, "Disable the red zone.",
                                                 (f"{MANIFEST_PY}::plan_binaries",),
                                                 default="false"),
                            "stack-protector": Value(
                                BOOL, "Pass the compiler `--stack-protector`: "
                                "every function but a `[[naked]]` one gets "
                                "LLVM `sspstrong`. The binary must define "
                                "`__stack_chk_guard` and `__stack_chk_fail`.",
                                (f"{MANIFEST_PY}::plan_binaries",),
                                default="false"),
                            "pic": Value(BOOL, "Position-independent code.",
                                         (f"{MANIFEST_PY}::plan_binaries",),
                                         default="false"),
                        }, read_by=(f"{MANIFEST_PY}::plan_binaries",)),
                    })),
            (f"{MANIFEST_PY}::plan_binaries",)),
        "test": Table(
            "Test discovery. `rz test` always runs test/*.ritz, the "
            "package's own test_*.ritz and test.sh, plus every module with a "
            "`[[test]]` function under src/ and the directories listed here. "
            "There is no `[[test]]` array: a test is a `[[test]]` function, "
            "not a manifest entry.",
            {
                "sources": Value(STRING_LIST, "Extra directories searched "
                                 "(recursively) for `[[test]]` modules.",
                                 (f"{MANIFEST_PY}::_declared_test_source_files",)),
            },
            read_by=(f"{MANIFEST_PY}::_declared_test_source_files",)),
    },
    moved_from={(): {"sources": _MOVED_SOURCES},
                ("build",): {"sources": _MOVED_SOURCES}})


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


def _presence_errors(table: Table, value: dict, path: tuple) -> list[str]:
    """What `value` lacks: each required key, and exactly one `one_of` key."""
    errors = [f"{_where(path)} is missing required key '{k}'"
              for k, node in table.fields.items()
              if getattr(node, "required", False) and k not in value]
    if table.one_of and sum(k in value for k in table.one_of) != 1:
        names = ", ".join(f"'{k}'" for k in table.one_of)
        errors.append(f"{_where(path)} needs exactly one of {names}")
    return errors


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
            elif k in moved.get(path, {}):
                err(path + (k,), f"'{_dotted(path + (k,))}' is not read: "
                                 f"{moved[path][k]}")
            else:
                allowed = sorted(table.fields)
                if table.self_named is not None:
                    allowed.append(f"{own_name or 'NAME'} (= name)")
                err(path + (k,), f"unknown key '{k}' in {_where(path)} "
                                 f"(allowed: {', '.join(allowed)})")
        for msg in _presence_errors(table, value, path):
            err(path, msg)

    moved = schema.moved_from
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
# Package targets: [[bin]], [[lib]] and the build profile (AGAST #3632)
#
# What a loaded manifest asks to build. Moved here from build.py, next to
# the schema that validated the same keys. RFC #109 Phase 1: entry point
# resolution, source discovery, build profiles.
# ---------------------------------------------------------------------------

def resolve_entry_point(entry: str, pkg_dir: Path, sources: list[str]) -> tuple[Path, str] | None:
    """Resolve entry = "module::function" to (file_path, function_name).

    `module` selects the source file under `sources`; `function` names that
    binary target's entry function. Both halves are part of the contract
    (AGAST #4434, LARB R68):

    - a hosted binary's entry function is `main` (§5.7);
    - a freestanding target may name another function, and a UEFI link uses
      it as the PE entry symbol (`plan_binaries` refuses a function the file
      does not define).

    Returns (file_path, function_name), or None when no source file matches
    `module`, or `entry` has no `::`.

    Examples:
        main::main          → src/main.ritz, "main"
        main::kernel_main   → src/main.ritz, "kernel_main"
    """
    if "::" not in entry:
        return None

    module_path, fn_name = entry.rsplit("::", 1)

    # Convert module path (dots) to file path (slashes)
    # main → main.ritz
    # http.server → http/server.ritz
    file_rel_path = module_path.replace(".", "/") + ".ritz"

    # Search in each source directory
    for src_spec in sources:
        # Handle exclusion patterns (skip them for search)
        if src_spec.startswith("!"):
            continue

        # Normalize source spec to directory
        src_dir = pkg_dir / src_spec.split("*")[0].rstrip("/")
        if not src_dir.is_dir():
            continue

        candidate = src_dir / file_rel_path
        if candidate.exists():
            return (candidate, fn_name)

    return None


def defined_functions(source_path: Path) -> set[str] | None:
    """The fns `source_path` defines, or None if it cannot be parsed.

    Used to hold a manifest's `entry` function half to something real: a
    named function that the declared source file does not define is a build
    failure, not a silent fall-through to `main` (AGAST #4434). A parse
    failure is left to the compiler, whose diagnostic is more precise.
    """
    ritz0_dir = Path(__file__).resolve().parent / "ritz0"
    if str(ritz0_dir) not in sys.path:
        sys.path.insert(0, str(ritz0_dir))
    from lexer import Lexer
    from parser import Parser
    import ritz_ast as rast

    try:
        source = source_path.read_text(encoding="utf-8")
        module = Parser(Lexer(source, str(source_path)).tokenize()).parse_module()
    except Exception:
        return None
    return {item.name for item in module.items if isinstance(item, rast.FnDef)}


def _entry_function_error(entry: str, fn_name: str, src_path: Path,
                          pkg_dir: Path, freestanding: bool) -> str | None:
    """Why `entry` cannot name `fn_name` in `src_path`, or None.

    The language has one entry convention — `main` in one of §5.7's shapes —
    so a hosted binary cannot name another function. Freestanding targets may
    (harland's `kernel_main`/`efi_main`), but the function must still be
    defined by the file `entry` selected.
    """
    if not freestanding and fn_name != "main":
        return (f"entry '{entry}' names '{fn_name}'; a hosted binary's entry "
                f"function is 'main'")
    defined = defined_functions(src_path)
    if defined is not None and fn_name not in defined:
        try:
            where = src_path.relative_to(pkg_dir).as_posix()
        except ValueError:
            where = str(src_path)
        return f"entry '{entry}' names '{fn_name}', which {where} does not define"
    return None


def discover_sources(pkg_dir: Path, sources: list[str] | None) -> list[Path]:
    """Discover source files based on sources configuration.

    Per RFC #109 §2.2:
    - Directory entries expand to dir/**/*.ritz
    - Explicit globs are used as-is
    - Exclusion patterns (!path) filter out matching files
    - Default: ["src"] if src/ exists, else ["."]

    Args:
        pkg_dir: Package directory (where ritz.toml is)
        sources: List of source specs, or None for default

    Returns:
        List of .ritz file paths
    """
    import fnmatch

    # Handle default
    if sources is None:
        if (pkg_dir / "src").is_dir():
            sources = ["src"]
        else:
            sources = ["."]

    include_patterns = []
    exclude_patterns = []

    for spec in sources:
        if spec.startswith("!"):
            # Exclusion pattern
            exclude_patterns.append(spec[1:])
        else:
            include_patterns.append(spec)

    # Collect all matching files
    all_files = set()
    for pattern in include_patterns:
        pattern_path = pkg_dir / pattern

        if pattern_path.is_dir():
            # Directory → recursive glob
            for f in pattern_path.rglob("*.ritz"):
                all_files.add(f)
        elif "*" in pattern:
            # Explicit glob pattern
            for f in pkg_dir.glob(pattern):
                if f.is_file() and f.suffix == ".ritz":
                    all_files.add(f)
        else:
            # Single file
            if pattern_path.exists() and pattern_path.suffix == ".ritz":
                all_files.add(pattern_path)

    # Apply exclusions
    result = []
    for f in sorted(all_files):
        excluded = False
        rel_path = str(f.relative_to(pkg_dir))
        for excl in exclude_patterns:
            # Match against relative path
            excl_path = pkg_dir / excl
            if excl_path.is_dir():
                # Exclude entire directory
                if str(f).startswith(str(excl_path)):
                    excluded = True
                    break
            elif fnmatch.fnmatch(rel_path, excl) or fnmatch.fnmatch(rel_path, excl + "/**"):
                excluded = True
                break
        if not excluded:
            result.append(f)

    return result


def get_build_profile(config: dict, profile_name: str | None) -> dict:
    """Get build profile settings.

    Per RFC #109 §2.3:
    - Profiles inherit from [build] section
    - Override with [profile.debug] or [profile.release]
    - Default profile is "debug"

    Returns dict with:
        name: str - profile name
        opt_level: int - optimization level (0-3)
        debug: bool - include debug info
        lto: bool - link-time optimization
    """
    # Defaults
    result = {
        "name": profile_name or "debug",
        "opt_level": 0,
        "debug": True,
        "lto": False,
    }

    # Inherit from [build] section
    if "build" in config:
        build = config["build"]
        if "opt-level" in build:
            result["opt_level"] = build["opt-level"]
        if "debug" in build:
            result["debug"] = build["debug"]
        if "lto" in build:
            result["lto"] = build["lto"]

    # Apply profile-specific overrides
    # When profile_name is None, default to "debug" profile
    effective_profile_name = profile_name or "debug"
    if "profile" in config:
        profile = config["profile"].get(effective_profile_name, {})
        if "opt-level" in profile:
            result["opt_level"] = profile["opt-level"]
        if "debug" in profile:
            result["debug"] = profile["debug"]
        if "lto" in profile:
            result["lto"] = profile["lto"]

    return result


@dataclass
class BinaryConfig:
    """Complete configuration for a binary target.

    Supports both standard hosted builds and freestanding kernel builds.
    """
    name: str                    # Binary name
    src_path: Path               # Main source file
    additional_sources: list[Path]  # Extra sources (deprecated)
    entry_fn: str = "main"       # Entry function in src_path ([[bin]] entry's
                                 # function half; `main` for a hosted binary)
    freestanding: bool = False   # If True, no runtime, custom linker
    target: str = ""             # Target triple (e.g., "x86_64-none-elf")
    target_os: str = ""          # Target OS for conditional compilation (e.g., "harland", "linux")
    linker_script: Path | None = None  # Custom linker script
    asm_files: list[Path] | None = None  # Assembly files to compile
    code_model: str = ""         # LLC code model (e.g., "kernel")
    no_red_zone: bool = False    # Disable red zone (for kernels)
    stack_protector: bool = False  # Compiler's --stack-protector (AGAST #2590)
    bin_sources: list[str] | None = None  # Per-binary source directories
    pic: bool = False            # Generate position-independent code (for PIE executables)
    link_runtime: bool = False   # Link with Ritz runtime (_start that calls main and sys_exit)

    def __post_init__(self):
        if self.asm_files is None:
            self.asm_files = []
        if self.bin_sources is None:
            self.bin_sources = []


@dataclass
class LibraryConfig:
    """A [[lib]] target: every module under its sources, and no binary.

    `modules` is what `sources` matched, not what an entry point imports, so a
    module nothing imports is still compiled.
    """
    name: str
    modules: list[Path]


# =============================================================================
# End RFC #109 Phase 2
# =============================================================================


def find_package_at(path: Path) -> tuple[Path, dict] | None:
    """Find a package at the given path (looks for ritz.toml)."""
    path = path.resolve()

    # If path is a file, look in its parent directory
    if path.is_file():
        path = path.parent

    # Look for ritz.toml in this directory
    toml_path = path / "ritz.toml"
    if toml_path.exists():
        return (path, load(toml_path))

    return None


def find_package_by_name_or_path(name_or_path: str) -> tuple[Path, dict] | None:
    """Find a package by name or path.

    Tries in order:
    1. If it's a path to a directory with ritz.toml, use that
    2. If it's a path to a ritz.toml file, use its directory
    3. Look in current directory for matching subdirectory
    """
    path = Path(name_or_path)

    # Try as direct path
    if path.exists():
        return find_package_at(path)

    # Try as subdirectory of current working directory
    cwd = Path.cwd()
    subdir = cwd / name_or_path
    if subdir.exists():
        return find_package_at(subdir)

    return None


def _workspace_excluded_dirs(search_dir: Path) -> list[Path]:
    """The enclosing rz.toml's [workspace.exclude] dirs that apply to a walk
    from search_dir (AGAST #4644).

    rz validates the table (workspace_exclusions); this only reads its keys.
    An exclusion that contains search_dir is dropped: a walk that starts
    inside an excluded tree asked for it (tools/example_tests.py and `make
    examples` walk examples/ on purpose).
    """
    for root in (search_dir, *search_dir.parents):
        rz_toml = root / "rz.toml"
        if rz_toml.is_file():
            break
    else:
        return []
    with open(rz_toml, "rb") as f:
        table = tomllib.load(f).get("workspace", {}).get("exclude", {})
    dirs = [(root / rel).resolve() for rel in table]
    return [d for d in dirs if not (search_dir == d or d in search_dir.parents)]


def find_all_packages(search_dir: Path | None = None) -> list[tuple[Path, dict]]:
    """Find all packages with ritz.toml files under search_dir.

    Defaults to current working directory if not specified. Skips each
    directory the enclosing rz.toml's [workspace.exclude] names, and
    everything below it, matched by path component as `./rz --all` does;
    an excluded manifest is not even loaded.
    """
    if search_dir is None:
        search_dir = Path.cwd()

    search_dir = search_dir.resolve()
    excluded = _workspace_excluded_dirs(search_dir)
    packages = []

    # Search for all ritz.toml files recursively.  docs/archive is retired
    # code that nothing should build: rz.toml's [workspace.exclude] keeps it
    # out of the workspace, and `--all` skips it the same way (AGAST #4648).
    for toml_path in sorted(search_dir.glob("**/ritz.toml")):
        pkg = toml_path.parent
        parts = toml_path.relative_to(search_dir).parts
        if any(parts[i:i + 2] == ("docs", "archive") for i in range(len(parts))):
            continue
        if any(pkg == d or d in pkg.parents for d in excluded):
            continue
        packages.append((pkg, load(toml_path)))

    return packages


def find_packages() -> list[tuple[Path, dict]]:
    """Find all packages - searches from current directory."""
    return find_all_packages()


@dataclass
class SkippedBinary:
    """A declared [[bin]] that this build deliberately does not compile.

    A skip is only legitimate when it is *named*: which target, and why. An
    empty/short binary list must never be inferred to mean "nothing to do" —
    that is how a missing binary passes for a successful build.
    """
    name: str
    reason: str


@dataclass
class BinaryPlan:
    """What plan_binaries() decided about every declared target in a package.

    Four disjoint buckets, and every declared target lands in exactly one:

    - buildable:  binaries to compile; each must produce an artifact
    - libraries:  [[lib]] targets to compile; each must produce an archive
    - skipped:    deliberately not compiled, with a stated reason (success)
    - unresolved: declared as a Ritz target but its source could not be found
                  (failure — a target we were asked for and cannot deliver)
    """
    buildable: list[BinaryConfig]
    skipped: list[SkippedBinary]
    unresolved: list[SkippedBinary]
    libraries: list[LibraryConfig] = field(default_factory=list)


def wants_convenience_link(bin_config: BinaryConfig) -> bool:
    """Whether a build links `<pkg>/<name>` to the binary (AGAST #4131).

    The link exists so host tests running with cwd=<pkg> can exec `./<name>`.
    A freestanding binary (harland, uefi, x86_64-unknown-none) never runs on
    the host and its consumers copy `build/<profile>/*.elf`, so a link would
    only leave an untracked file in the package root that every new bin has
    to gitignore by hand (projects/indium/fault_child blocked room teardown).
    """
    return not bin_config.freestanding


def plan_binaries(pkg_dir: Path, config: dict) -> BinaryPlan:
    """Resolve every declared target into the buckets of a BinaryPlan.

    get_binaries() returns only the buildable bucket, which is all most callers
    need. Anything deciding whether a *package* built must use this instead, so
    that a target dropped during resolution is visibly accounted for rather
    than silently absent from the list.

    A package with neither [[bin]] nor [[lib]] gets one binary named after it,
    from main.ritz under its sources. A package with [[lib]] and no [[bin]] has
    no binary at all (AGAST #1340).
    """
    plan = BinaryPlan(buildable=[], skipped=[], unresolved=[])
    binaries = plan.buildable

    # Check if this is a test-only package
    is_test_only = config.get("build", {}).get("test_only", False)
    if is_test_only:
        return plan  # Test-only packages have no binaries

    # Package-level sources configuration (RFC #109)
    from resolve import package_sources  # resolve imports this module
    pkg_sources = package_sources(config)
    if pkg_sources is None:
        pkg_sources = ["src"]  # Default

    # [[lib]] sections. `sources` overrides the package's, as it does for
    # [[bin]]: zeus's package sources include test/, which is not library code.
    for lib_entry in config.get("lib", []):
        lib_sources = lib_entry.get("sources", pkg_sources)
        if isinstance(lib_sources, str):
            lib_sources = [lib_sources]
        modules = discover_sources(pkg_dir, lib_sources)
        if modules:
            plan.libraries.append(LibraryConfig(lib_entry["name"], modules))
        else:
            # A library that compiles nothing must not pass for a built one.
            plan.unresolved.append(SkippedBinary(
                lib_entry["name"], f"[[lib]] has no .ritz modules under {lib_sources}"))

    # Check for [[bin]] sections
    if "bin" in config:
        for bin_entry in config["bin"]:
            name = bin_entry["name"]
            # Read before entry resolution: whether the target is freestanding
            # decides which entry functions `entry` may name (AGAST #4434).
            freestanding = bin_entry.get("freestanding", False)

            # RFC #109: entry = "module::function". Both halves are honoured:
            # the module selects the source file, the function is the target's
            # entry function (AGAST #4434, LARB R68).
            if "entry" in bin_entry:
                entry = bin_entry["entry"]
                # Use bin-specific sources if provided, else package-level
                bin_sources_list = bin_entry.get("sources", pkg_sources)
                if isinstance(bin_sources_list, str):
                    bin_sources_list = [bin_sources_list]
                result = resolve_entry_point(entry, pkg_dir, bin_sources_list)
                if result is None:
                    # Not a skip: the package declares a Ritz binary whose
                    # source we cannot find. Record it as unresolved so the
                    # package build fails instead of quietly building N-1.
                    print(f"  ⚠ Could not resolve entry point: {entry}", file=sys.stderr)
                    plan.unresolved.append(SkippedBinary(
                        name, f"could not resolve entry point '{entry}'"))
                    continue
                src_path, entry_fn = result
                error = _entry_function_error(entry, entry_fn, src_path,
                                              pkg_dir, freestanding)
                if error is not None:
                    plan.unresolved.append(SkippedBinary(name, error))
                    continue
            # Legacy: path = "src/main.ritz"
            elif "path" in bin_entry:
                src_path = pkg_dir / bin_entry["path"]
                entry_fn = "main"
                # Legitimate skip: a [[bin]] pointing at a .py/.sh script is
                # not something this compiler builds. Named, not inferred.
                if not src_path.suffix == ".ritz":
                    plan.skipped.append(SkippedBinary(
                        name, f"not a Ritz source ({src_path.name})"))
                    continue
            # Default: src/{name}.ritz
            else:
                src_path = pkg_dir / "src" / f"{name}.ritz"
                entry_fn = "main"

            # Get additional sources if specified (legacy, deprecated)
            additional_sources = []
            if "sources" in bin_entry and isinstance(bin_entry["sources"], list):
                # Check if these are paths or directory specs
                for src in bin_entry["sources"]:
                    src_path_check = pkg_dir / src
                    if src_path_check.is_file():
                        additional_sources.append(src_path_check)

            # Parse freestanding build options
            target = bin_entry.get("target", "")
            target_os = bin_entry.get("target_os", "")

            # Parse [bin.NAME.linker] section
            # TOML puts [bin.harland.linker] as bin_entry["harland"]["linker"]
            nested_config = bin_entry.get(name, {})
            linker_config = nested_config.get("linker", {})
            linker_script = None
            if linker_config.get("script"):
                linker_script = pkg_dir / linker_config["script"]

            # Parse [bin.NAME.asm] section
            asm_config = nested_config.get("asm", {})
            asm_files = []
            for asm_file in asm_config.get("files", []):
                asm_files.append(pkg_dir / asm_file)

            # Parse [bin.NAME.flags] section
            flags_config = nested_config.get("flags", {})
            code_model = flags_config.get("code-model", "")
            no_red_zone = flags_config.get("no-red-zone", False)
            stack_protector = flags_config.get("stack-protector", False)
            pic = flags_config.get("pic", False)

            # Parse runtime linking options
            # link_runtime: bool - link with Ritz runtime (_start)
            link_runtime = bin_entry.get("link_runtime", False)

            # Per-binary source directories
            bin_sources = bin_entry.get("sources", [])
            if isinstance(bin_sources, str):
                bin_sources = [bin_sources]

            binaries.append(BinaryConfig(
                name=name,
                src_path=src_path,
                additional_sources=additional_sources,
                entry_fn=entry_fn,
                freestanding=freestanding,
                target=target,
                target_os=target_os,
                linker_script=linker_script,
                asm_files=asm_files,
                code_model=code_model,
                no_red_zone=no_red_zone,
                stack_protector=stack_protector,
                bin_sources=bin_sources,
                pic=pic,
                link_runtime=link_runtime,
            ))
    elif "lib" not in config:
        # Default: single binary with package name
        name = config["package"]["name"]
        result = resolve_entry_point("main::main", pkg_dir, pkg_sources)
        if result is None:
            plan.unresolved.append(SkippedBinary(
                name, f"no main.ritz under sources {pkg_sources}; "
                      "declare a [[bin]] or a [[lib]]"))
        else:
            binaries.append(BinaryConfig(
                name=name,
                src_path=result[0],
                additional_sources=[],
            ))

    return plan


def get_binaries(pkg_dir: Path, config: dict) -> list[BinaryConfig]:
    """Get list of BinaryConfig objects for all buildable binary targets.

    Returns empty list for test-only packages (no binary to build).

    Supports both RFC #109 syntax and legacy syntax:
    - RFC #109: entry = "module::main"  → resolves to src/module.ritz
    - Legacy:   path = "src/main.ritz"  → direct file path

    Also supports freestanding builds with:
    - freestanding = true
    - target = "x86_64-none-elf"
    - [bin.NAME.linker] script = "linker.ld"
    - [bin.NAME.asm] files = ["boot.s", "isr.s"]
    - [bin.NAME.flags] code-model = "kernel", no-red-zone = true,
      stack-protector = true

    NOTE: this is a lossy view — targets that were skipped or failed to resolve
    are simply absent. Use plan_binaries() when the difference matters.
    """
    return plan_binaries(pkg_dir, config).buildable



# ---------------------------------------------------------------------------
# Package tests: which .ritz files `test` runs (moved from build.py, #3632)
# ---------------------------------------------------------------------------

class StrayTestsDirError(Exception):
    """A package keeps .ritz files in `tests/`, which discovery never reads.

    Until AGAST #1386, five packages did this (284 [[test]] fns, run by no
    gate), following an `rz` comment that wrongly said build.py globbed
    `tests/`. Rather than add a second convention, a stray `tests/*.ritz` is
    an error that names every file that would otherwise never run.
    """

    def __init__(self, pkg_dir: Path, files: list[Path]):
        self.pkg_dir = pkg_dir
        self.files = files
        names = "\n".join(f"  {f.relative_to(pkg_dir)}" for f in files)
        super().__init__(
            f"{pkg_dir}: {len(files)} .ritz file(s) under tests/ would never "
            f"run; test discovery reads test/ only. Move them to test/ "
            f"(git mv) (AGAST #1386):\n{names}")


def stray_test_files(pkg_dir: Path) -> list[Path]:
    """Every .ritz under `pkg_dir/tests/`, sorted; [] when tests/ is absent,
    holds no .ritz (angelo's fixtures), or is its own package with a
    ritz.toml (ritzlib's `ritzlib/tests`)."""
    tests_dir = pkg_dir / "tests"
    if not tests_dir.is_dir() or (tests_dir / "ritz.toml").exists():
        return []
    return sorted(tests_dir.rglob("*.ritz"))


def discover_test_files(pkg_dir: Path, config: dict) -> list[Path]:
    """The package's .ritz test files, sorted: test/*.ritz, plus the root's
    test_*.ritz for a `test_only` package.

    The single owner of test-file discovery. `run_tests` (serial) and the
    `--unit-plan` entry point that `rz test --all -j N` schedules from both
    call this, so the parallel sweep cannot cover a different file set from
    the serial one (AGAST #1809).
    """
    stray = stray_test_files(pkg_dir)
    if stray:
        raise StrayTestsDirError(pkg_dir, stray)
    ritz_tests = []
    test_dir = pkg_dir / "test"
    if test_dir.exists():
        ritz_tests.extend(test_dir.glob("*.ritz"))
    if config.get("build", {}).get("test_only", False):
        ritz_tests.extend(pkg_dir.glob("test_*.ritz"))
    ritz_tests.extend(_declared_test_source_files(pkg_dir, config))
    return sorted(set(ritz_tests))  # Dedupe and sort


def _declared_test_source_files(pkg_dir: Path, config: dict) -> list[Path]:
    """Files under src/ and `[test] sources` dirs that define a `[[test]]` fn.

    For packages that keep [[test]] fns inside their modules rather than in
    test/ (angelo, prism). `ritz0 --test` runs only the given file's own
    [[test]] fns, so each such module is its own test file. Dirs are searched
    recursively; a module with no `[[test]]` line is not taken, since it
    would report "ran 0 tests" and fail. Until AGAST #3279 build.py read no
    key for this and angelo's tests ran under no gate.

    src/ is always searched: a [[test]] fn written there runs (or fails the
    package), whether or not ritz.toml mentions it. #3279 made it opt-in, so
    prism's src/text tests still ran nowhere (AGAST #1873).

    Only the `[test]` table adds dirs. ritz.toml has no `[[test]]` array:
    the two that existed (goliath, spire) were read by nothing and their
    modules already ran from test/, so AGAST #1837 removed them, and the
    manifest schema now rejects one.
    """
    test_cfg = config.get("test")
    dirs = ["src"]
    if isinstance(test_cfg, dict):
        dirs += test_cfg.get("sources", [])
    found = []
    for rel in dict.fromkeys(dirs):
        d = pkg_dir / rel
        if not d.is_dir():
            continue
        for f in d.rglob("*.ritz"):
            text = f.read_text(encoding="utf-8", errors="replace")
            if any(line.strip() == "[[test]]" for line in text.splitlines()):
                found.append(f)
    return found


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
