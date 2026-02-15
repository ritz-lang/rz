"""
Ritz Module Metadata (.ritz-meta)

Extracts and caches module metadata for fast incremental compilation.
Metadata includes exports (functions, types, constants) and imports,
enabling the linker to verify symbol resolution without re-parsing.

Format: JSON with indentation for readability.
Location: .ritz-cache/<module_path>.ritz-meta

Cache invalidation: Timestamp-based. If source file is newer than
.ritz-meta, regenerate metadata.
"""

import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Dict, Optional, Any
import ritz_ast as rast


@dataclass
class FnSignature:
    """Function signature for metadata."""
    name: str
    params: List[Dict[str, Any]]  # [{name, type}]
    ret_type: Optional[str]
    is_extern: bool
    is_generic: bool
    type_params: List[str]


@dataclass
class StructMeta:
    """Struct metadata."""
    name: str
    fields: List[Dict[str, Any]]  # [{name, type}]
    is_generic: bool
    type_params: List[str]


@dataclass
class EnumMeta:
    """Enum metadata."""
    name: str
    variants: List[Dict[str, Any]]  # [{name, fields}]
    type_params: List[str] = field(default_factory=list)

    @property
    def is_generic(self) -> bool:
        return len(self.type_params) > 0


@dataclass
class ConstMeta:
    """Constant metadata."""
    name: str
    type: str
    value: Any  # Integer value, or list of integers for array constants


@dataclass
class TypeAliasMeta:
    """Type alias metadata."""
    name: str
    target: str


@dataclass
class TraitMeta:
    """Trait metadata."""
    name: str
    methods: List[Dict[str, Any]]  # [{name, params, ret_type}]


@dataclass
class ImplMeta:
    """Impl block metadata."""
    trait_name: Optional[str]  # None for inherent impls
    type_name: str  # Base type name (e.g., "String", "Vec")
    type_params: List[str]  # e.g., ["T"] for impl<T>
    impl_type: Optional[str]  # Full type string with args
    methods: List[Dict[str, Any]]  # [{name, params, ret_type}]


@dataclass
class ModuleMetadata:
    """Complete module metadata."""
    source_path: str
    source_mtime: float

    # Exports
    functions: List[FnSignature]
    structs: List[StructMeta]
    enums: List[EnumMeta]
    constants: List[ConstMeta]
    type_aliases: List[TypeAliasMeta]
    traits: List[TraitMeta]
    impls: List[ImplMeta]  # Impl blocks (trait implementations)

    # Imports (module paths)
    imports: List[str]


def type_to_string(t: rast.Type) -> str:
    """Convert a Type AST node to a string representation."""
    if t is None:
        return "void"

    if isinstance(t, rast.NamedType):
        if t.args:
            args = ", ".join(type_to_string(a) for a in t.args)
            return f"{t.name}<{args}>"
        return t.name

    elif isinstance(t, rast.PtrType):
        mut = "mut " if t.mutable else ""
        return f"*{mut}{type_to_string(t.inner)}"

    elif isinstance(t, rast.RefType):
        mut = "mut " if t.mutable else ""
        return f"&{mut}{type_to_string(t.inner)}"

    elif isinstance(t, rast.ArrayType):
        return f"[{t.size}]{type_to_string(t.inner)}"

    elif isinstance(t, rast.SliceType):
        return f"[]{type_to_string(t.inner)}"

    elif isinstance(t, rast.FnType):
        params = ", ".join(type_to_string(p) for p in t.params)
        ret = type_to_string(t.ret) if t.ret else "void"
        return f"fn({params}) -> {ret}"

    elif isinstance(t, rast.UnionType):
        return " | ".join(type_to_string(v) for v in t.variants)

    return str(t)


def _extract_int_literal(name: str, expr: rast.Expr) -> int:
    """Extract an integer literal value from an expression."""
    if isinstance(expr, rast.IntLit):
        return expr.value
    elif isinstance(expr, rast.UnaryOp) and expr.op == '-':
        if isinstance(expr.operand, rast.IntLit):
            return -expr.operand.value
    raise ValueError(f"Constant '{name}' element must be an integer literal")


def _extract_const_value(name: str, value: rast.Expr) -> Any:
    """Extract a constant value from an expression.

    Supports:
    - Integer literals (positive and negative)
    - Array literals with integer elements
    - Array fill expressions with integer values
    """
    # Simple integer literal
    if isinstance(value, rast.IntLit):
        return value.value

    # Negative integer literal
    if isinstance(value, rast.UnaryOp) and value.op == '-':
        if isinstance(value.operand, rast.IntLit):
            return -value.operand.value
        raise ValueError(f"Constant '{name}' must have integer literal value")

    # Array literal: [a, b, c]
    if isinstance(value, rast.ArrayLit):
        return [_extract_int_literal(name, elem) for elem in value.elements]

    # Array fill: [value; count]
    if isinstance(value, rast.ArrayFill):
        fill_value = _extract_int_literal(name, value.value)
        return [fill_value] * value.count

    raise ValueError(f"Constant '{name}' must have integer literal or array literal value")


def extract_metadata(module: rast.Module, source_path: str) -> ModuleMetadata:
    """Extract metadata from a parsed module AST."""

    source_mtime = os.path.getmtime(source_path) if os.path.exists(source_path) else 0.0

    functions = []
    structs = []
    enums = []
    constants = []
    type_aliases = []
    traits = []
    impls = []
    imports = []

    for item in module.items:
        if isinstance(item, rast.FnDef):
            params = [
                {"name": p.name, "type": type_to_string(p.type)}
                for p in item.params
            ]
            functions.append(FnSignature(
                name=item.name,
                params=params,
                ret_type=type_to_string(item.ret_type),
                is_extern=item.is_extern,
                is_generic=item.is_generic(),
                type_params=item.type_params or []
            ))

        elif isinstance(item, rast.ExternFn):
            params = [
                {"name": p.name, "type": type_to_string(p.type)}
                for p in item.params
            ]
            functions.append(FnSignature(
                name=item.name,
                params=params,
                ret_type=type_to_string(item.ret_type),
                is_extern=True,
                is_generic=False,
                type_params=[]
            ))

        elif isinstance(item, rast.StructDef):
            fields = [
                {"name": name, "type": type_to_string(ftype)}
                for name, ftype in item.fields
            ]
            structs.append(StructMeta(
                name=item.name,
                fields=fields,
                is_generic=item.is_generic(),
                type_params=item.type_params or []
            ))

        elif isinstance(item, rast.EnumDef):
            variants = [
                {"name": v.name, "fields": [type_to_string(f) for f in v.fields]}
                for v in item.variants
            ]
            enums.append(EnumMeta(
                name=item.name,
                variants=variants,
                type_params=item.type_params or []
            ))

        elif isinstance(item, rast.ConstDef):
            # Extract actual constant value
            const_value = _extract_const_value(item.name, item.value)
            constants.append(ConstMeta(
                name=item.name,
                type=type_to_string(item.type),
                value=const_value
            ))

        elif isinstance(item, rast.TypeAlias):
            type_aliases.append(TypeAliasMeta(
                name=item.name,
                target=type_to_string(item.target)
            ))

        elif isinstance(item, rast.TraitDef):
            methods = []
            for m in item.methods:
                params = [
                    {"name": p.name, "type": type_to_string(p.type)}
                    for p in m.params
                ]
                methods.append({
                    "name": m.name,
                    "params": params,
                    "ret_type": type_to_string(m.ret_type)
                })
            traits.append(TraitMeta(
                name=item.name,
                methods=methods
            ))

        elif isinstance(item, rast.ImplBlock):
            methods = []
            for m in item.methods:
                params = [
                    {"name": p.name, "type": type_to_string(p.type)}
                    for p in m.params
                ]
                methods.append({
                    "name": m.name,
                    "params": params,
                    "ret_type": type_to_string(m.ret_type)
                })
            impls.append(ImplMeta(
                trait_name=item.trait_name,
                type_name=item.type_name,
                type_params=item.type_params or [],
                impl_type=type_to_string(item.impl_type) if item.impl_type else None,
                methods=methods
            ))

        elif isinstance(item, rast.Import):
            imports.append(".".join(item.path))

    return ModuleMetadata(
        source_path=str(source_path),
        source_mtime=source_mtime,
        functions=functions,
        structs=structs,
        enums=enums,
        constants=constants,
        type_aliases=type_aliases,
        traits=traits,
        impls=impls,
        imports=imports
    )


# =============================================================================
# JSON Serialization
# =============================================================================

def metadata_to_json(meta: ModuleMetadata) -> str:
    """Serialize metadata to JSON format with indentation."""
    data = {
        "source_path": meta.source_path,
        "source_mtime": meta.source_mtime,
        "imports": meta.imports,
        "functions": [asdict(f) for f in meta.functions],
        "structs": [asdict(s) for s in meta.structs],
        "enums": [asdict(e) for e in meta.enums],
        "constants": [asdict(c) for c in meta.constants],
        "type_aliases": [asdict(t) for t in meta.type_aliases],
        "traits": [asdict(t) for t in meta.traits],
        "impls": [asdict(i) for i in meta.impls],
    }
    return json.dumps(data, indent=2)


def metadata_from_json(json_str: str) -> ModuleMetadata:
    """Parse metadata from JSON string."""
    data = json.loads(json_str)

    functions = [FnSignature(**f) for f in data.get('functions', [])]
    structs = [StructMeta(**s) for s in data.get('structs', [])]
    enums = [EnumMeta(**e) for e in data.get('enums', [])]
    # Handle old metadata without value field (default to 0 for backwards compat)
    constants = []
    for c in data.get('constants', []):
        if 'value' not in c:
            c['value'] = 0  # Backwards compat for old cached metadata
        constants.append(ConstMeta(**c))
    type_aliases = [TypeAliasMeta(**t) for t in data.get('type_aliases', [])]
    traits = [TraitMeta(**t) for t in data.get('traits', [])]
    impls = [ImplMeta(**i) for i in data.get('impls', [])]

    return ModuleMetadata(
        source_path=data.get('source_path', ''),
        source_mtime=data.get('source_mtime', 0.0),
        functions=functions,
        structs=structs,
        enums=enums,
        constants=constants,
        type_aliases=type_aliases,
        traits=traits,
        impls=impls,
        imports=data.get('imports', [])
    )


# =============================================================================
# Cache Management
# =============================================================================

def get_cache_path(source_path: str, cache_dir: str = ".ritz-cache") -> Path:
    """Get the cache path for a source file's metadata.

    Converts: /path/to/foo.ritz -> .ritz-cache/path/to/foo.ritz-meta
    """
    # Make path relative if absolute
    src = Path(source_path)
    if src.is_absolute():
        # Try to make relative to cwd
        try:
            src = src.relative_to(Path.cwd())
        except ValueError:
            # Keep just the name if can't make relative
            src = Path(src.name)

    cache = Path(cache_dir) / src.with_suffix(".ritz-meta")
    return cache


def save_metadata(meta: ModuleMetadata, cache_dir: str = ".ritz-cache") -> Path:
    """Save metadata to cache file in JSON format."""
    cache_path = get_cache_path(meta.source_path, cache_dir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    with open(cache_path, 'w') as f:
        f.write(metadata_to_json(meta))

    return cache_path


def load_metadata(source_path: str, cache_dir: str = ".ritz-cache") -> Optional[ModuleMetadata]:
    """Load metadata from cache if valid.

    Returns None if cache doesn't exist or is stale.
    """
    cache_path = get_cache_path(source_path, cache_dir)

    if not cache_path.exists():
        return None

    try:
        with open(cache_path, 'r') as f:
            json_str = f.read()

        meta = metadata_from_json(json_str)

        # Check if cache is stale
        if os.path.exists(source_path):
            current_mtime = os.path.getmtime(source_path)
            if current_mtime > meta.source_mtime:
                return None  # Source is newer, cache is stale

        return meta

    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def is_cache_valid(source_path: str, cache_dir: str = ".ritz-cache") -> bool:
    """Check if cached metadata exists and is still valid."""
    return load_metadata(source_path, cache_dir) is not None


class MetadataCache:
    """In-memory cache for module metadata during compilation."""

    def __init__(self, cache_dir: str = ".ritz-cache"):
        self.cache_dir = cache_dir
        self._memory_cache: Dict[str, ModuleMetadata] = {}

    def get(self, source_path: str) -> Optional[ModuleMetadata]:
        """Get metadata, checking memory cache first, then disk."""
        # Normalize path
        source_path = str(Path(source_path).resolve())

        # Check memory cache
        if source_path in self._memory_cache:
            return self._memory_cache[source_path]

        # Check disk cache
        meta = load_metadata(source_path, self.cache_dir)
        if meta:
            self._memory_cache[source_path] = meta

        return meta

    def put(self, meta: ModuleMetadata) -> None:
        """Store metadata in memory and persist to disk."""
        source_path = str(Path(meta.source_path).resolve())
        self._memory_cache[source_path] = meta
        save_metadata(meta, self.cache_dir)

    def invalidate(self, source_path: str) -> None:
        """Invalidate cache entry for a source file."""
        source_path = str(Path(source_path).resolve())
        self._memory_cache.pop(source_path, None)

        cache_path = get_cache_path(source_path, self.cache_dir)
        if cache_path.exists():
            cache_path.unlink()

    def get_exports(self, source_path: str) -> Dict[str, Any]:
        """Get all exported symbols from a module.

        Returns dict with keys: functions, structs, enums, constants, type_aliases, traits
        """
        meta = self.get(source_path)
        if not meta:
            return {}

        return {
            "functions": {f.name: f for f in meta.functions},
            "structs": {s.name: s for s in meta.structs},
            "enums": {e.name: e for e in meta.enums},
            "constants": {c.name: c for c in meta.constants},
            "type_aliases": {t.name: t for t in meta.type_aliases},
            "traits": {t.name: t for t in meta.traits},
        }
