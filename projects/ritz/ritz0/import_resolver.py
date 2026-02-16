"""
Import Resolver for ritz0

Handles import statements by resolving import paths to files,
parsing them, and merging their definitions into the main module.

Import resolution order:
  1. Same directory as importing file: foo.ritz, foo/bar.ritz
  2. Project root (detected via .git or ritzlib/): ritzlib/sys.ritz
  3. RITZ_PATH environment variable (colon-separated directories)

Duplicate handling:
  - Structs: Error if same name with different definition
  - Functions: Error if same name with different signature
  - Constants: Error if same name with different value
  - Imported items are marked to avoid re-processing

Metadata caching:
  - .ritz-meta files store module exports for fast lookup
  - Cache invalidated based on source file timestamps
  - Allows incremental compilation without re-parsing unchanged files
"""

from pathlib import Path
from typing import Set, Dict, Optional, List
from dataclasses import replace
import os
import ritz_ast as rast
from lexer import Lexer
from parser import Parser
from metadata import MetadataCache, extract_metadata, ModuleMetadata


class ImportError(Exception):
    """Error during import resolution."""
    pass


# ============================================================================
# Export Map Types - Track public items exported by modules
# ============================================================================

class ExportEntry:
    """Represents a single exported item from a module."""

    def __init__(
        self,
        name: str,
        kind: str,  # "fn", "struct", "enum", "const", "var", "type_alias", "trait", "extern_fn"
        module_path: str,
        is_pub: bool = True,
        is_reexport: bool = False,
        original_module: Optional[str] = None
    ):
        self.name = name
        self.kind = kind
        self.module_path = module_path
        self.is_pub = is_pub
        self.is_reexport = is_reexport
        self.original_module = original_module or module_path

    def __repr__(self):
        return f"ExportEntry({self.name!r}, kind={self.kind!r}, pub={self.is_pub})"


class ModuleExports:
    """Collection of exports from a single module."""

    def __init__(self, module_path: str):
        self.module_path = module_path
        self.exports: Dict[str, ExportEntry] = {}

    def add_export(self, entry: ExportEntry):
        """Add an export entry."""
        self.exports[entry.name] = entry

    def has_export(self, name: str) -> bool:
        """Check if an export exists."""
        return name in self.exports

    def get_export(self, name: str) -> Optional[ExportEntry]:
        """Get an export entry by name."""
        return self.exports.get(name)

    def __repr__(self):
        return f"ModuleExports({self.module_path!r}, {len(self.exports)} exports)"


class DependencyMapping:
    """Represents a dependency namespace mapping for import resolution.

    Per RFC #109 §2.6:
    - import squeeze.gzip → squeeze/src/gzip.ritz (if squeeze is a dependency)
    """

    def __init__(self, name: str, path: Path, sources: List[str]):
        self.name = name          # Dependency name (used as import namespace)
        self.path = path          # Path to dependency root
        self.sources = sources    # Source directories within dependency

    def resolve_import(self, module_parts: List[str]) -> Optional[str]:
        """Resolve an import path within this dependency.

        Args:
            module_parts: Path parts after the dependency name
                         e.g., for "squeeze.gzip", this would be ["gzip"]

        Returns:
            Path to the .ritz file if found, None otherwise
        """
        if not module_parts:
            return None

        # Convert module path to file path: gzip → gzip.ritz
        file_rel = "/".join(module_parts[:-1] + [module_parts[-1] + ".ritz"]) if module_parts else ""

        # Search in dependency's source directories
        for src_dir in self.sources:
            src_path = self.path / src_dir
            if not src_path.is_dir():
                continue
            candidate = src_path / file_rel
            if candidate.exists():
                return str(candidate.resolve())

        return None


class ImportResolver:
    """Resolves and processes import statements."""

    def __init__(
        self,
        project_root: Optional[str] = None,
        use_cache: bool = True,
        dependencies: Optional[Dict[str, DependencyMapping]] = None,
        source_roots: Optional[List[str]] = None
    ):
        # Track which files have been processed to avoid cycles
        self.processed_files: Set[str] = set()
        # Track which files are currently being processed (for cycle detection)
        self.processing_stack: List[str] = []
        # Collected items from all imports
        self.structs: Dict[str, rast.StructDef] = {}
        self.enums: Dict[str, rast.EnumDef] = {}
        # Functions stored as lists to support multiple definitions with different
        # [[target_os]] attributes. The correct one is selected after target_os filtering.
        self.functions: Dict[str, List[rast.FnDef]] = {}
        self.extern_fns: Dict[str, rast.ExternFn] = {}
        # Constants stored as lists to support multiple definitions with different
        # [[target_os]] attributes. The correct one is selected after target_os filtering.
        self.constants: Dict[str, List[rast.ConstDef]] = {}
        self.variables: Dict[str, rast.VarDef] = {}
        self.type_aliases: Dict[str, rast.TypeAlias] = {}
        self.traits: Dict[str, rast.TraitDef] = {}
        # Impl blocks indexed by (trait_name or None, type_name)
        self.impls: List[rast.ImplBlock] = []
        # Static assertions (not exported, but kept for const eval)
        self.static_asserts: List[rast.StaticAssert] = []
        # Project root for absolute imports (e.g., ritzlib.sys)
        self.project_root: Optional[Path] = Path(project_root).resolve() if project_root else None
        # Additional import paths from RITZ_PATH environment variable
        self.import_paths: List[Path] = []
        ritz_path = os.environ.get('RITZ_PATH', '')
        if ritz_path:
            for p in ritz_path.split(':'):
                if p and Path(p).exists():
                    self.import_paths.append(Path(p).resolve())
        # Metadata cache for incremental compilation
        self.use_cache = use_cache
        self.metadata_cache = MetadataCache() if use_cache else None
        # Track generated metadata for saving
        self.generated_metadata: Dict[str, ModuleMetadata] = {}
        # Export map: module_path -> ModuleExports
        self.module_exports: Dict[str, ModuleExports] = {}
        # Import aliases: from_file -> {alias -> module_path}
        self.import_aliases: Dict[str, Dict[str, str]] = {}
        # RFC #109 Phase 2: Dependency mappings for namespace resolution
        self.dependencies: Dict[str, DependencyMapping] = dependencies or {}
        # Source roots: directories to search for imports (e.g., ["src", "kernel/src"])
        # These are searched after relative imports but before project root
        self.source_roots: List[Path] = []
        if source_roots:
            for sr in source_roots:
                sr_path = Path(sr)
                if not sr_path.is_absolute() and self.project_root:
                    sr_path = self.project_root / sr_path
                if sr_path.exists():
                    self.source_roots.append(sr_path.resolve())

    # ============================================================================
    # Export Map Building
    # ============================================================================

    def _build_export_map(self, module: rast.Module, module_path: str) -> ModuleExports:
        """Build an export map for a module, tracking public items."""
        exports = ModuleExports(module_path)

        for item in module.items:
            # Skip imports and impl blocks - they don't export at module level
            if isinstance(item, rast.Import):
                continue
            if isinstance(item, rast.ImplBlock):
                continue

            # Check if item has is_pub attribute and it's True
            is_pub = getattr(item, 'is_pub', False)
            if not is_pub:
                continue

            # Determine kind and name
            if isinstance(item, rast.FnDef):
                kind = "fn"
                name = item.name
            elif isinstance(item, rast.ExternFn):
                kind = "extern_fn"
                name = item.name
            elif isinstance(item, rast.StructDef):
                kind = "struct"
                name = item.name
            elif isinstance(item, rast.EnumDef):
                kind = "enum"
                name = item.name
            elif isinstance(item, rast.ConstDef):
                kind = "const"
                name = item.name
            elif isinstance(item, rast.VarDef):
                kind = "var"
                name = item.name
            elif isinstance(item, rast.TypeAlias):
                kind = "type_alias"
                name = item.name
            elif isinstance(item, rast.TraitDef):
                kind = "trait"
                name = item.name
            else:
                continue

            entry = ExportEntry(
                name=name,
                kind=kind,
                module_path=module_path,
                is_pub=True
            )
            exports.add_export(entry)

        return exports

    def _validate_selective_import(
        self,
        import_node: rast.Import,
        exports: ModuleExports
    ) -> Dict[str, ExportEntry]:
        """Validate a selective import and return matched exports.

        Args:
            import_node: The import AST node
            exports: The module's export map

        Returns:
            Dict mapping item names to their export entries

        Raises:
            ImportError if a requested item is not exported
        """
        result = {}

        # If import has specific items, validate each one
        items = getattr(import_node, 'items', None)
        if items:
            for item_name in items:
                entry = exports.get_export(item_name)
                if entry is None:
                    raise ImportError(
                        f"'{item_name}' is not exported by module "
                        f"'{'.'.join(import_node.path)}'"
                    )
                result[item_name] = entry
        else:
            # Non-selective import - return all exports
            result = dict(exports.exports)

        return result

    def _register_import_alias(self, alias: str, module_path: str, from_file: str):
        """Register an import alias for qualified name resolution.

        Args:
            alias: The alias name (e.g., 'sys' for 'import ritzlib.sys')
            module_path: Full path to the imported module
            from_file: The file that contains the import
        """
        if from_file not in self.import_aliases:
            self.import_aliases[from_file] = {}
        self.import_aliases[from_file][alias] = module_path

    def resolve_qualified_name(
        self,
        qualifier: str,
        name: str,
        from_file: str
    ) -> Optional[ExportEntry]:
        """Resolve a qualified name (e.g., sys::prints).

        Args:
            qualifier: The module alias (e.g., 'sys')
            name: The item name (e.g., 'prints')
            from_file: The file context

        Returns:
            ExportEntry if found, None otherwise
        """
        # Get the module path for the alias
        aliases = self.import_aliases.get(from_file, {})
        module_path = aliases.get(qualifier)
        if module_path is None:
            return None

        # Get exports for that module
        exports = self.module_exports.get(module_path)
        if exports is None:
            return None

        return exports.get_export(name)

    def _transform_qualified_idents(self, module: rast.Module, source_path: str) -> rast.Module:
        """Transform QualifiedIdent nodes to regular Ident nodes.

        Walks the AST and replaces `sys::write` with `write` after verifying
        that `sys` is a registered alias. This desugars qualified imports to
        allow the emitter to work with simple Ident nodes.

        Issue #99: Qualified import name resolution not implemented
        """
        source_path = str(Path(source_path).resolve())
        aliases = self.import_aliases.get(source_path, {})

        if not aliases:
            # No aliases registered for this file - no transformation needed
            return module

        # Walk and transform items
        transformed_items = []
        for item in module.items:
            transformed_items.append(self._transform_item(item, aliases))

        return rast.Module(module.span, transformed_items)

    def _transform_item(self, item: rast.Item, aliases: Dict[str, str]) -> rast.Item:
        """Transform QualifiedIdent nodes in an item."""
        # Helper to preserve source_file attribute through replace()
        def copy_source_file(old_item: rast.Item, new_item: rast.Item) -> rast.Item:
            source_file = getattr(old_item, 'source_file', None)
            if source_file is not None:
                new_item.source_file = source_file
            return new_item

        if isinstance(item, rast.FnDef):
            if item.body:
                new_body = self._transform_block(item.body, aliases)
                return copy_source_file(item, replace(item, body=new_body))
            return item
        elif isinstance(item, rast.ImplBlock):
            # Transform method bodies
            new_methods = []
            for method in item.methods:
                if method.body:
                    new_body = self._transform_block(method.body, aliases)
                    new_method = copy_source_file(method, replace(method, body=new_body))
                    new_methods.append(new_method)
                else:
                    new_methods.append(method)
            return copy_source_file(item, replace(item, methods=new_methods))
        elif isinstance(item, rast.ConstDef):
            if item.value:
                new_value = self._transform_expr(item.value, aliases)
                return copy_source_file(item, replace(item, value=new_value))
            return item
        elif isinstance(item, rast.VarDef):
            if item.value:
                new_value = self._transform_expr(item.value, aliases)
                return copy_source_file(item, replace(item, value=new_value))
            return item
        # Other items don't contain expressions that need transformation
        return item

    def _transform_block(self, block: rast.Block, aliases: Dict[str, str]) -> rast.Block:
        """Transform expressions in a block."""
        new_stmts = [self._transform_stmt(stmt, aliases) for stmt in block.stmts]
        new_expr = self._transform_expr(block.expr, aliases) if block.expr else None
        return replace(block, stmts=new_stmts, expr=new_expr)

    def _transform_stmt(self, stmt: rast.Stmt, aliases: Dict[str, str]) -> rast.Stmt:
        """Transform expressions in a statement."""
        if isinstance(stmt, rast.LetStmt):
            if stmt.value:
                new_value = self._transform_expr(stmt.value, aliases)
                return replace(stmt, value=new_value)
            return stmt
        elif isinstance(stmt, rast.VarStmt):
            if stmt.value:
                new_value = self._transform_expr(stmt.value, aliases)
                return replace(stmt, value=new_value)
            return stmt
        elif isinstance(stmt, rast.AssignStmt):
            new_target = self._transform_expr(stmt.target, aliases)
            new_value = self._transform_expr(stmt.value, aliases)
            return replace(stmt, target=new_target, value=new_value)
        elif isinstance(stmt, rast.ExprStmt):
            new_expr = self._transform_expr(stmt.expr, aliases)
            return replace(stmt, expr=new_expr)
        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                new_value = self._transform_expr(stmt.value, aliases)
                return replace(stmt, value=new_value)
            return stmt
        elif isinstance(stmt, rast.WhileStmt):
            new_cond = self._transform_expr(stmt.cond, aliases)
            new_body = self._transform_block(stmt.body, aliases)
            return replace(stmt, cond=new_cond, body=new_body)
        elif isinstance(stmt, rast.ForStmt):
            new_iter = self._transform_expr(stmt.iter_expr, aliases)
            new_body = self._transform_block(stmt.body, aliases)
            return replace(stmt, iter_expr=new_iter, body=new_body)
        return stmt

    def _transform_expr(self, expr: rast.Expr, aliases: Dict[str, str]) -> rast.Expr:
        """Transform QualifiedIdent and recursively transform sub-expressions."""
        if expr is None:
            return None

        # KEY TRANSFORMATION: QualifiedIdent -> Ident
        if isinstance(expr, rast.QualifiedIdent):
            if expr.qualifier in aliases:
                # Transform sys::write -> write
                return rast.Ident(expr.span, expr.name)
            else:
                raise RitzImportError(
                    f"Unknown import alias: '{expr.qualifier}' in '{expr.qualifier}::{expr.name}'",
                    expr.span
                )

        # Recursively transform sub-expressions using replace()
        if isinstance(expr, rast.BinOp):
            new_left = self._transform_expr(expr.left, aliases)
            new_right = self._transform_expr(expr.right, aliases)
            return replace(expr, left=new_left, right=new_right)
        elif isinstance(expr, rast.UnaryOp):
            new_operand = self._transform_expr(expr.operand, aliases)
            return replace(expr, operand=new_operand)
        elif isinstance(expr, rast.Call):
            new_func = self._transform_expr(expr.func, aliases)
            new_args = [self._transform_expr(arg, aliases) for arg in expr.args]
            return replace(expr, func=new_func, args=new_args)
        elif isinstance(expr, rast.Index):
            new_base = self._transform_expr(expr.expr, aliases)
            new_index = self._transform_expr(expr.index, aliases)
            return replace(expr, expr=new_base, index=new_index)
        elif isinstance(expr, rast.Field):
            new_base = self._transform_expr(expr.expr, aliases)
            return replace(expr, expr=new_base)
        elif isinstance(expr, rast.If):
            new_cond = self._transform_expr(expr.cond, aliases)
            new_then = self._transform_block(expr.then_block, aliases)
            new_else = self._transform_block(expr.else_block, aliases) if expr.else_block else None
            return replace(expr, cond=new_cond, then_block=new_then, else_block=new_else)
        elif isinstance(expr, rast.Match):
            new_match_expr = self._transform_expr(expr.expr, aliases)
            new_arms = []
            for arm in expr.arms:
                new_body = self._transform_block(arm.body, aliases)
                new_arms.append(replace(arm, body=new_body))
            return replace(expr, expr=new_match_expr, arms=new_arms)
        elif isinstance(expr, rast.Cast):
            new_inner = self._transform_expr(expr.expr, aliases)
            return replace(expr, expr=new_inner)
        elif isinstance(expr, rast.StructLit):
            new_fields = [(name, self._transform_expr(val, aliases)) for name, val in expr.fields]
            return replace(expr, fields=new_fields)
        elif isinstance(expr, rast.ArrayLit):
            new_elements = [self._transform_expr(elem, aliases) for elem in expr.elements]
            return replace(expr, elements=new_elements)
        elif isinstance(expr, rast.ArrayFill):
            new_value = self._transform_expr(expr.value, aliases)
            return replace(expr, value=new_value)
        elif isinstance(expr, rast.Lambda):
            new_body = self._transform_expr(expr.body, aliases)
            return replace(expr, body=new_body)
        elif isinstance(expr, rast.Closure):
            new_body = self._transform_block(expr.body, aliases)
            return replace(expr, body=new_body)
        elif isinstance(expr, rast.Block):
            return self._transform_block(expr, aliases)
        elif isinstance(expr, rast.TryOp):
            new_inner = self._transform_expr(expr.expr, aliases)
            return replace(expr, expr=new_inner)
        elif isinstance(expr, rast.Await):
            new_inner = self._transform_expr(expr.expr, aliases)
            return replace(expr, expr=new_inner)
        elif isinstance(expr, rast.SliceExpr):
            new_base = self._transform_expr(expr.expr, aliases)
            new_start = self._transform_expr(expr.start, aliases) if expr.start else None
            new_end = self._transform_expr(expr.end, aliases) if expr.end else None
            return replace(expr, expr=new_base, start=new_start, end=new_end)
        elif isinstance(expr, rast.Range):
            new_start = self._transform_expr(expr.start, aliases) if expr.start else None
            new_end = self._transform_expr(expr.end, aliases) if expr.end else None
            return replace(expr, start=new_start, end=new_end)

        # Leaf expressions that don't contain sub-expressions
        return expr

    def _process_re_exports(
        self,
        module: rast.Module,
        module_path: str,
        module_exports: ModuleExports
    ):
        """Process pub import statements and add re-exported items.

        Args:
            module: The module containing potential pub import statements
            module_path: Path to the module
            module_exports: The ModuleExports to add re-exports to
        """
        for item in module.items:
            if not isinstance(item, rast.Import):
                continue

            # Check if this is a pub import (re-export)
            is_pub = getattr(item, 'is_pub', False)
            if not is_pub:
                continue

            # Get exports from the imported module
            imported_module_path = self._resolve_import_path(item.path, module_path)
            if imported_module_path is None or imported_module_path not in self.module_exports:
                # If we haven't built the export map yet, skip for now
                # This will be handled in a second pass
                continue

            imported_exports = self.module_exports[imported_module_path]

            # Validate and get the items to re-export
            re_exported_items = self._validate_selective_import(item, imported_exports)

            # Add each re-exported item to our module's exports
            for item_name, entry in re_exported_items.items():
                # Create a new entry that marks this as a re-export
                re_export_entry = ExportEntry(
                    name=entry.name,
                    kind=entry.kind,
                    module_path=module_path,
                    is_pub=True,
                    is_reexport=True,
                    original_module=entry.original_module
                )
                module_exports.add_export(re_export_entry)

    # ============================================================================
    # Import Resolution
    # ============================================================================

    def resolve(self, module: rast.Module, source_path: str) -> rast.Module:
        """Resolve all imports in a module and return merged module.

        Args:
            module: The parsed module with potential Import nodes
            source_path: Path to the source file (for resolving relative imports)

        Returns:
            New module with all imported items merged in
        """
        source_path = str(Path(source_path).resolve())
        self.processed_files.add(source_path)

        # Auto-detect project root if not provided
        if self.project_root is None:
            self.project_root = self._find_project_root(Path(source_path).parent)

        # Process imports first
        imports = [item for item in module.items if isinstance(item, rast.Import)]
        non_imports = [item for item in module.items if not isinstance(item, rast.Import)]

        for imp in imports:
            self._process_import(imp, source_path)

        # Collect items from this module
        for item in non_imports:
            self._register_item(item, source_path)

        # Build merged module
        merged_items = []

        # Add all collected items in order: structs, enums, type_aliases, traits, constants, variables, extern_fns, impls, functions
        merged_items.extend(self.structs.values())
        merged_items.extend(self.enums.values())
        merged_items.extend(self.type_aliases.values())
        merged_items.extend(self.traits.values())
        # Flatten constant lists (multiple constants with same name may exist
        # due to [[target_os]] attributes - filtering happens later)
        for const_list in self.constants.values():
            merged_items.extend(const_list)
        merged_items.extend(self.variables.values())
        merged_items.extend(self.extern_fns.values())
        merged_items.extend(self.impls)
        # Flatten function lists (multiple functions with same name may exist
        # due to [[target_os]] attributes - filtering happens later)
        for fn_list in self.functions.values():
            merged_items.extend(fn_list)
        merged_items.extend(self.static_asserts)

        result = rast.Module(module.span, merged_items)

        # Transform QualifiedIdent nodes to regular Ident nodes (Issue #99)
        # e.g., sys::write -> write (after verifying sys alias is valid)
        result = self._transform_qualified_idents(result, source_path)

        # Extract and cache metadata for the main module
        # IMPORTANT: Extract from original `module` (has Import nodes) not `result` (merged)
        if self.use_cache:
            meta = extract_metadata(module, source_path)
            self.generated_metadata[source_path] = meta
            self.metadata_cache.put(meta)

        return result

    def _process_import(self, imp: rast.Import, from_file: str):
        """Process a single import statement."""
        import_path = self._resolve_import_path(imp.path, from_file)

        if import_path is None:
            raise ImportError(f"Cannot find module: {'.'.join(imp.path)}")

        # Register import alias if present (Issue #99: qualified import support)
        # e.g., import ritzlib.sys as sys -> register 'sys' alias for from_file
        if imp.alias:
            self._register_import_alias(imp.alias, import_path, from_file)

        # Skip if already processed
        if import_path in self.processed_files:
            return

        # Check for cycles
        if import_path in self.processing_stack:
            cycle = ' -> '.join(self.processing_stack + [import_path])
            raise ImportError(f"Circular import detected: {cycle}")

        # Mark as being processed
        self.processing_stack.append(import_path)
        self.processed_files.add(import_path)

        try:
            # Try to use cached metadata first (faster incremental compilation)
            if self.use_cache and self.metadata_cache:
                cached_meta = self.metadata_cache.get(import_path)
                if cached_meta is not None:
                    # Skip cache if module has generic functions, structs, or impls
                    # We need the actual bodies for monomorphization
                    has_generics = any(fn.is_generic for fn in cached_meta.functions)
                    has_generics = has_generics or any(s.is_generic for s in cached_meta.structs)
                    has_generics = has_generics or any(len(i.type_params) > 0 for i in cached_meta.impls)
                    if not has_generics:
                        # Use cached metadata - convert to AST items without reparsing
                        self._register_items_from_metadata(cached_meta, import_path)
                        # Recursively process cached imports
                        for nested_import_path in cached_meta.imports:
                            nested_imp = rast.Import(rast.Span("<cached>", 0, 0, 0), nested_import_path.split('.'))
                            self._process_import(nested_imp, import_path)
                        return

            # Cache miss or disabled - read and parse the imported file
            source = Path(import_path).read_text()
            lexer = Lexer(source, import_path)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            imported_module = parser.parse_module()

            # Process imports in the imported module
            for item in imported_module.items:
                if isinstance(item, rast.Import):
                    self._process_import(item, import_path)
                else:
                    self._register_item(item, import_path)

            # Extract and cache metadata for this imported module
            if self.use_cache:
                meta = extract_metadata(imported_module, import_path)
                self.generated_metadata[import_path] = meta
                self.metadata_cache.put(meta)

        finally:
            self.processing_stack.pop()

    def _find_project_root(self, start_dir: Path) -> Optional[Path]:
        """Walk up from start_dir looking for project root indicators.

        Project root is detected by presence of:
          - .git directory (most reliable)
          - ritzlib/ directory (indicates project with standard library)

        Note: We don't use ritz.toml because packages within a project
        each have their own ritz.toml, and we want the workspace root.
        """
        current = start_dir.resolve()
        while current != current.parent:
            if (current / '.git').exists():
                return current
            if (current / 'ritzlib').is_dir():
                return current
            current = current.parent
        return None

    def _resolve_import_path(self, path_parts: List[str], from_file: str) -> Optional[str]:
        """Resolve an import path to an actual file path.

        Resolution order:
        1. Relative to importing file: foo.ritz, foo/bar.ritz
        2. From source roots (e.g., ["src", "kernel/src"])
        3. From project root: ritzlib/sys.ritz
        4. From RITZ_PATH directories
        """
        base_dir = Path(from_file).parent

        # RFC #109 Phase 2: Check if first part is a dependency namespace
        # e.g., "squeeze.gzip" → check if "squeeze" is a dependency
        if len(path_parts) >= 1 and path_parts[0] in self.dependencies:
            dep = self.dependencies[path_parts[0]]
            result = dep.resolve_import(path_parts[1:])
            if result:
                return result
            # If not found in dependency, don't fall through to other resolution
            # This prevents accidental shadowing of dependency names
            return None

        # Try 1: Relative to importing file - foo/bar.ritz
        relative_path = Path(*path_parts[:-1]) / f"{path_parts[-1]}.ritz" if len(path_parts) > 1 else Path(f"{path_parts[0]}.ritz")
        candidate = base_dir / relative_path
        if candidate.exists():
            return str(candidate.resolve())

        # Try 1b: Relative to importing file - foo.bar.ritz
        flat_name = '.'.join(path_parts) + '.ritz'
        candidate = base_dir / flat_name
        if candidate.exists():
            return str(candidate.resolve())

        # Try 2: From source roots (e.g., ["src", "kernel/src"])
        for source_root in self.source_roots:
            candidate = source_root / relative_path
            if candidate.exists():
                return str(candidate.resolve())
            candidate = source_root / flat_name
            if candidate.exists():
                return str(candidate.resolve())

        # Try 4: From project root
        if self.project_root:
            candidate = self.project_root / relative_path
            if candidate.exists():
                return str(candidate.resolve())
            candidate = self.project_root / flat_name
            if candidate.exists():
                return str(candidate.resolve())

        # Try 5: From RITZ_PATH directories
        for import_path in self.import_paths:
            candidate = import_path / relative_path
            if candidate.exists():
                return str(candidate.resolve())
            candidate = import_path / flat_name
            if candidate.exists():
                return str(candidate.resolve())

        return None

    def _register_items_from_metadata(self, meta: ModuleMetadata, source_file: str):
        """Register AST items from cached metadata (avoids re-parsing).

        Creates minimal AST nodes from metadata. For functions, we create FnDef
        nodes with empty bodies (suitable for generating `declare` statements
        in separate compilation mode).
        """
        from metadata import FnSignature, StructMeta, EnumMeta, ConstMeta, TypeAliasMeta, TraitMeta

        dummy_span = rast.Span("<cached>", 0, 0, 0)

        def parse_type_string(type_str: str) -> rast.Type:
            """Parse a type string back to a Type AST node."""
            if type_str is None or type_str == "void":
                return None
            if type_str.startswith('*'):
                # Pointer type
                mutable = False
                inner_str = type_str[1:]
                if inner_str.startswith('mut '):
                    mutable = True
                    inner_str = inner_str[4:]
                return rast.PtrType(dummy_span, parse_type_string(inner_str), mutable)
            if type_str.startswith('&'):
                # Reference type
                mutable = False
                inner_str = type_str[1:]
                if inner_str.startswith('mut '):
                    mutable = True
                    inner_str = inner_str[4:]
                return rast.RefType(dummy_span, parse_type_string(inner_str), mutable)
            if type_str.startswith('[') and ']' in type_str:
                # Array or slice type
                bracket_end = type_str.index(']')
                size_str = type_str[1:bracket_end]
                inner_str = type_str[bracket_end + 1:]
                if size_str == '':
                    # Slice type: []T
                    return rast.SliceType(dummy_span, parse_type_string(inner_str))
                else:
                    # Array type: [N]T
                    return rast.ArrayType(dummy_span, int(size_str), parse_type_string(inner_str))
            if type_str.startswith('fn('):
                # Function type: fn(params) -> ret
                # Parse to proper FnType AST node
                try:
                    # Find the matching closing paren for params
                    depth = 0
                    params_end = -1
                    for i, c in enumerate(type_str):
                        if c == '(':
                            depth += 1
                        elif c == ')':
                            depth -= 1
                            if depth == 0:
                                params_end = i
                                break

                    if params_end == -1:
                        # Malformed, fall back to NamedType
                        return rast.NamedType(dummy_span, type_str, [])

                    # Extract params and return type
                    params_str = type_str[3:params_end]  # Skip 'fn('
                    remainder = type_str[params_end + 1:].strip()

                    # Parse params (simple split, doesn't handle nested fn types perfectly)
                    param_types = []
                    if params_str.strip():
                        # Split by comma, but be careful with nested types
                        parts = []
                        current = ""
                        depth = 0
                        for c in params_str:
                            if c == '(' or c == '<':
                                depth += 1
                            elif c == ')' or c == '>':
                                depth -= 1
                            if c == ',' and depth == 0:
                                parts.append(current.strip())
                                current = ""
                            else:
                                current += c
                        if current.strip():
                            parts.append(current.strip())
                        param_types = [parse_type_string(p) for p in parts]

                    # Parse return type (after ' -> ')
                    ret_type = None
                    if remainder.startswith('-> '):
                        ret_str = remainder[3:].strip()
                        if ret_str and ret_str != 'void':
                            ret_type = parse_type_string(ret_str)

                    return rast.FnType(dummy_span, param_types, ret_type)
                except Exception:
                    # On any parse error, fall back to NamedType
                    return rast.NamedType(dummy_span, type_str, [])
            if ' | ' in type_str:
                # Union type
                variants = [parse_type_string(v.strip()) for v in type_str.split(' | ')]
                return rast.UnionType(dummy_span, variants)
            if '<' in type_str and type_str.endswith('>'):
                # Generic type: Name<Args>
                bracket_pos = type_str.index('<')
                name = type_str[:bracket_pos]
                args_str = type_str[bracket_pos + 1:-1]
                # Simple split by comma (doesn't handle nested generics perfectly)
                args = [parse_type_string(a.strip()) for a in args_str.split(',') if a.strip()]
                return rast.NamedType(dummy_span, name, args)
            # Simple named type
            return rast.NamedType(dummy_span, type_str, [])

        # Register functions
        for fn_sig in meta.functions:
            params = [
                rast.Param(
                    span=dummy_span,
                    name=p['name'],
                    type=parse_type_string(p['type'])
                )
                for p in fn_sig.params
            ]

            if fn_sig.is_extern:
                # ExternFn - just a declaration
                extern_fn = rast.ExternFn(
                    span=dummy_span,
                    name=fn_sig.name,
                    params=params,
                    ret_type=parse_type_string(fn_sig.ret_type),
                    varargs=False
                )
                extern_fn.source_file = source_file
                if fn_sig.name not in self.extern_fns:
                    self.extern_fns[fn_sig.name] = extern_fn
            else:
                # FnDef with empty body (for declarations in separate compilation)
                # The body=Block([]) makes this suitable for `declare` emission
                fn_def = rast.FnDef(
                    span=dummy_span,
                    name=fn_sig.name,
                    params=params,
                    ret_type=parse_type_string(fn_sig.ret_type),
                    body=rast.Block(dummy_span, [], None),  # Empty body - import only needs signature
                    is_extern=False,
                    type_params=fn_sig.type_params if fn_sig.is_generic else None
                )
                fn_def.source_file = source_file
                if fn_sig.name not in self.functions:
                    self.functions[fn_sig.name] = fn_def

        # Register structs
        for struct_meta in meta.structs:
            fields = [
                (f['name'], parse_type_string(f['type']))
                for f in struct_meta.fields
            ]
            struct_def = rast.StructDef(
                span=dummy_span,
                name=struct_meta.name,
                fields=fields,
                type_params=struct_meta.type_params if struct_meta.is_generic else None
            )
            struct_def.source_file = source_file
            if struct_meta.name not in self.structs:
                self.structs[struct_meta.name] = struct_def

        # Register enums
        for enum_meta in meta.enums:
            variants = []
            for v in enum_meta.variants:
                variant_fields = [parse_type_string(f) for f in v['fields']]
                variants.append(rast.Variant(dummy_span, v['name'], variant_fields))
            enum_def = rast.EnumDef(
                span=dummy_span,
                name=enum_meta.name,
                variants=variants,
                type_params=enum_meta.type_params or []
            )
            enum_def.source_file = source_file
            if enum_meta.name not in self.enums:
                self.enums[enum_meta.name] = enum_def

        # Register constants
        for const_meta in meta.constants:
            # Use actual value from metadata (required for compile-time resolution)
            # Handle array vs scalar values
            if isinstance(const_meta.value, list):
                # Array constant - create ArrayLit
                elements = [rast.IntLit(dummy_span, v) for v in const_meta.value]
                value_ast = rast.ArrayLit(dummy_span, elements)
            else:
                # Scalar constant - create IntLit
                value_ast = rast.IntLit(dummy_span, const_meta.value)
            const_def = rast.ConstDef(
                span=dummy_span,
                name=const_meta.name,
                type=parse_type_string(const_meta.type),
                value=value_ast
            )
            const_def.source_file = source_file
            if const_meta.name not in self.constants:
                self.constants[const_meta.name] = [const_def]

        # Register type aliases
        for alias_meta in meta.type_aliases:
            type_alias = rast.TypeAlias(
                span=dummy_span,
                name=alias_meta.name,
                target=parse_type_string(alias_meta.target)
            )
            type_alias.source_file = source_file
            if alias_meta.name not in self.type_aliases:
                self.type_aliases[alias_meta.name] = type_alias

        # Register traits
        for trait_meta in meta.traits:
            methods = []
            for m in trait_meta.methods:
                params = [
                    rast.Param(span=dummy_span, name=p['name'], type=parse_type_string(p['type']))
                    for p in m['params']
                ]
                method = rast.FnDef(
                    span=dummy_span,
                    name=m['name'],
                    params=params,
                    ret_type=parse_type_string(m['ret_type']),
                    body=rast.Block(dummy_span, [], None),
                    is_extern=False,
                    type_params=None
                )
                methods.append(method)
            trait_def = rast.TraitDef(
                span=dummy_span,
                name=trait_meta.name,
                methods=methods
            )
            trait_def.source_file = source_file
            if trait_meta.name not in self.traits:
                self.traits[trait_meta.name] = trait_def

        # Register impl blocks
        from metadata import ImplMeta
        for impl_meta in meta.impls:
            methods = []
            for m in impl_meta.methods:
                params = [
                    rast.Param(span=dummy_span, name=p['name'], type=parse_type_string(p['type']))
                    for p in m['params']
                ]
                method = rast.FnDef(
                    span=dummy_span,
                    name=m['name'],
                    params=params,
                    ret_type=parse_type_string(m['ret_type']),
                    body=rast.Block(dummy_span, [], None),
                    is_extern=False,
                    type_params=None
                )
                method.source_file = source_file
                methods.append(method)
            impl_block = rast.ImplBlock(
                span=dummy_span,
                trait_name=impl_meta.trait_name,
                type_name=impl_meta.type_name,
                methods=methods,
                type_params=impl_meta.type_params if impl_meta.type_params else [],
                impl_type=parse_type_string(impl_meta.impl_type) if impl_meta.impl_type else None
            )
            impl_block.source_file = source_file
            self.impls.append(impl_block)

    def _register_item(self, item: rast.Item, source_file: str):
        """Register an item, checking for duplicates."""
        # Track which file this item came from (for separate compilation)
        item.source_file = source_file

        if isinstance(item, rast.StructDef):
            if item.name in self.structs:
                existing = self.structs[item.name]
                # Allow duplicate if identical definition
                if not self._structs_equal(existing, item):
                    raise ImportError(
                        f"Conflicting struct definition for '{item.name}': "
                        f"defined in both {source_file} and previous import"
                    )
            else:
                self.structs[item.name] = item

        elif isinstance(item, rast.FnDef):
            # Store functions as lists to support multiple definitions with different
            # [[target_os]] attributes. The correct one is selected by target_os filtering.
            if item.name not in self.functions:
                self.functions[item.name] = []

            # Check if this function has a target_os attribute
            item_target_os = None
            if hasattr(item, 'get_attr_value'):
                item_target_os = item.get_attr_value('target_os')

            if item_target_os is not None:
                # This function has a target_os attribute - always add it
                # (filtering will pick the right one later)
                self.functions[item.name].append(item)
            else:
                # No target_os attribute - check for duplicates
                # Keep only one non-conditional function per name
                has_non_conditional = any(
                    (f.get_attr_value('target_os') if hasattr(f, 'get_attr_value') else None) is None
                    for f in self.functions[item.name]
                )
                if has_non_conditional:
                    # Replace existing non-conditional function (last one wins)
                    self.functions[item.name] = [
                        f for f in self.functions[item.name]
                        if (f.get_attr_value('target_os') if hasattr(f, 'get_attr_value') else None) is not None
                    ]
                self.functions[item.name].append(item)

        elif isinstance(item, rast.ExternFn):
            if item.name in self.extern_fns:
                pass  # Duplicate extern declarations are OK
            else:
                self.extern_fns[item.name] = item

        elif isinstance(item, rast.ConstDef):
            # Constants with [[target_os]] can have multiple definitions with same name
            # Add to list if it has target_os attribute, or if name doesn't exist
            has_target_os = hasattr(item, 'get_attr_value') and item.get_attr_value('target_os') is not None
            if item.name in self.constants:
                existing_list = self.constants[item.name]
                # Check if any existing constant conflicts (same target_os or neither has target_os)
                for existing in existing_list:
                    existing_has_target_os = hasattr(existing, 'get_attr_value') and existing.get_attr_value('target_os') is not None
                    if has_target_os and existing_has_target_os:
                        # Both have target_os - OK if different values
                        if item.get_attr_value('target_os') == existing.get_attr_value('target_os'):
                            if not self._consts_equal(existing, item):
                                raise ImportError(
                                    f"Conflicting constant definition for '{item.name}': "
                                    f"defined differently for same target_os"
                                )
                            # Same definition - skip adding duplicate
                            break
                    elif not has_target_os and not existing_has_target_os:
                        # Neither has target_os - must be identical
                        if not self._consts_equal(existing, item):
                            raise ImportError(
                                f"Conflicting constant definition for '{item.name}': "
                                f"defined differently in multiple files"
                            )
                        # Same definition - skip adding duplicate
                        break
                    # else: one has target_os and one doesn't - this is OK, both should be kept
                else:
                    # No conflict found - add to list
                    self.constants[item.name].append(item)
            else:
                self.constants[item.name] = [item]

        elif isinstance(item, rast.VarDef):
            if item.name in self.variables:
                raise ImportError(
                    f"Duplicate module-level variable '{item.name}': "
                    f"defined in both {source_file} and previous import"
                )
            else:
                self.variables[item.name] = item

        elif isinstance(item, rast.EnumDef):
            if item.name in self.enums:
                existing = self.enums[item.name]
                # Allow duplicate if identical definition
                if not self._enums_equal(existing, item):
                    raise ImportError(
                        f"Conflicting enum definition for '{item.name}': "
                        f"defined in both {source_file} and previous import"
                    )
            else:
                self.enums[item.name] = item

        elif isinstance(item, rast.TypeAlias):
            if item.name in self.type_aliases:
                existing = self.type_aliases[item.name]
                # Allow duplicate if identical definition
                if not self._type_aliases_equal(existing, item):
                    raise ImportError(
                        f"Conflicting type alias definition for '{item.name}': "
                        f"defined in both {source_file} and previous import"
                    )
            else:
                self.type_aliases[item.name] = item

        elif isinstance(item, rast.TraitDef):
            if item.name in self.traits:
                existing = self.traits[item.name]
                # For now, last one wins (like functions)
                pass
            self.traits[item.name] = item

        elif isinstance(item, rast.ImplBlock):
            # Impl blocks are collected into a list
            # Duplicates are allowed and merged by the emitter
            # Propagate source_file to methods for separate compilation
            for method in item.methods:
                method.source_file = source_file
            self.impls.append(item)

        elif isinstance(item, rast.StaticAssert):
            # Static asserts are collected for compile-time evaluation
            # Only keep asserts from the main module (not imports)
            self.static_asserts.append(item)

    def _structs_equal(self, a: rast.StructDef, b: rast.StructDef) -> bool:
        """Check if two struct definitions are equivalent."""
        if a.name != b.name:
            return False
        if len(a.fields) != len(b.fields):
            return False
        for (aname, atype), (bname, btype) in zip(a.fields, b.fields):
            if aname != bname:
                return False
            if not self._types_equal(atype, btype):
                return False
        return True

    def _enums_equal(self, a: rast.EnumDef, b: rast.EnumDef) -> bool:
        """Check if two enum definitions are equivalent."""
        if a.name != b.name:
            return False
        if len(a.variants) != len(b.variants):
            return False
        for av, bv in zip(a.variants, b.variants):
            if av.name != bv.name:
                return False
            # Compare variant fields
            if len(av.fields) != len(bv.fields):
                return False
            for af, bf in zip(av.fields, bv.fields):
                if not self._types_equal(af, bf):
                    return False
        return True

    def _consts_equal(self, a: rast.ConstDef, b: rast.ConstDef) -> bool:
        """Check if two constant definitions are equivalent."""
        if a.name != b.name:
            return False
        if not self._types_equal(a.type, b.type):
            return False
        # Compare values
        return self._exprs_equal(a.value, b.value)

    def _exprs_equal(self, a: rast.Expr, b: rast.Expr) -> bool:
        """Check if two expressions are structurally equivalent."""
        if type(a) != type(b):
            return False
        if isinstance(a, rast.IntLit):
            return a.value == b.value
        if isinstance(a, rast.BoolLit):
            return a.value == b.value
        if isinstance(a, rast.StringLit):
            return a.value == b.value
        if isinstance(a, rast.ArrayLit):
            if len(a.elements) != len(b.elements):
                return False
            return all(self._exprs_equal(ae, be) for ae, be in zip(a.elements, b.elements))
        if isinstance(a, rast.ArrayFill):
            return self._exprs_equal(a.value, b.value) and self._exprs_equal(a.count, b.count)
        # For other expression types, conservatively return False
        return False

    def _types_equal(self, a: rast.Type, b: rast.Type) -> bool:
        """Check if two types are equivalent."""
        if type(a) != type(b):
            return False
        if isinstance(a, rast.NamedType):
            return a.name == b.name
        if isinstance(a, rast.PtrType):
            return a.mutable == b.mutable and self._types_equal(a.inner, b.inner)
        if isinstance(a, rast.RefType):
            return a.mutable == b.mutable and self._types_equal(a.inner, b.inner)
        if isinstance(a, rast.ArrayType):
            return a.size == b.size and self._types_equal(a.inner, b.inner)
        if isinstance(a, rast.SliceType):
            return self._types_equal(a.inner, b.inner)
        if isinstance(a, rast.UnionType):
            if len(a.variants) != len(b.variants):
                return False
            return all(self._types_equal(av, bv) for av, bv in zip(a.variants, b.variants))
        return True

    def _type_aliases_equal(self, a: rast.TypeAlias, b: rast.TypeAlias) -> bool:
        """Check if two type alias definitions are equivalent."""
        if a.name != b.name:
            return False
        return self._types_equal(a.target, b.target)


def resolve_imports(
    module: rast.Module,
    source_path: str,
    project_root: Optional[str] = None,
    use_cache: bool = True,
    dependencies: Optional[Dict[str, DependencyMapping]] = None,
    source_roots: Optional[List[str]] = None
) -> rast.Module:
    """Convenience function to resolve all imports in a module.

    Args:
        module: The parsed module with potential Import nodes
        source_path: Path to the source file
        project_root: Optional explicit project root (auto-detected if not provided)
        use_cache: Whether to use .ritz-meta caching (default True)
        dependencies: RFC #109 dependency mappings for namespace resolution
        source_roots: List of source directories to search for imports

    Returns:
        New module with all imported items merged in
    """
    resolver = ImportResolver(project_root, use_cache=use_cache, dependencies=dependencies, source_roots=source_roots)
    return resolver.resolve(module, source_path)


def collect_all_source_files(
    source_path: str,
    project_root: Optional[str] = None,
    dependencies: Optional[Dict[str, DependencyMapping]] = None,
    source_roots: Optional[List[str]] = None
) -> List[str]:
    """Collect all source files needed for a module (main + all imports).

    This does a "dry run" of import resolution to discover all required files.
    Used by build systems to know what files to compile before linking.

    Args:
        source_path: Path to the main source file
        project_root: Optional explicit project root (auto-detected if not provided)
        dependencies: RFC #109 dependency mappings for namespace resolution
        source_roots: List of source directories to search for imports

    Returns:
        List of absolute paths to all required source files, in dependency order
        (imports first, main file last)
    """
    # Ensure ritz0 directory is in path for local imports
    import sys
    ritz0_dir = str(Path(__file__).parent)
    if ritz0_dir not in sys.path:
        sys.path.insert(0, ritz0_dir)

    from parser import Parser
    from lexer import Lexer

    # Don't use cache - this is just for discovery, not compilation.
    # Using cache here would write stub metadata that could interfere
    # with later compilation that needs full function bodies.
    resolver = ImportResolver(project_root, use_cache=False, dependencies=dependencies, source_roots=source_roots)
    source_path = str(Path(source_path).resolve())

    # Parse main module
    source_code = Path(source_path).read_text()
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    module = parser.parse_module()

    # Resolve imports (this populates resolver.processed_files)
    resolver.resolve(module, source_path)

    # Return all files in dependency order (imports first, then main)
    result = [f for f in resolver.processed_files if f != source_path]
    result.append(source_path)
    return result
