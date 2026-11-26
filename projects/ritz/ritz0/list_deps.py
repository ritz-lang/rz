#!/usr/bin/env python3
"""
List all source file dependencies for a Ritz source file.

Usage:
    python ritz0/list_deps.py source.ritz
    python ritz0/list_deps.py source.ritz --deps name:path:sources ...

Outputs one file path per line, in dependency order (imports first, main last).
With --record, prints one JSON object instead: {"files": [...], "misses":
[...], "configs": [...]} (import_resolver.collect_closure), what build.py
records to skip re-resolving an unchanged closure (AGAST #4775).

Dependencies are passed as name:path:sources where sources is comma-separated.
Example: --deps squeeze:/path/to/squeeze:src,lib
"""

import sys
import json
from pathlib import Path

# Ensure ritz0 is in path
ritz0_dir = Path(__file__).parent
sys.path.insert(0, str(ritz0_dir))

from import_resolver import collect_closure, DependencyMapping

def parse_deps_arg(deps_json: str) -> dict:
    """Parse JSON dependency spec.

    Format: {"name": {"path": "/abs/path", "sources": ["src"]}, ...}
    """
    if not deps_json:
        return {}

    data = json.loads(deps_json)
    result = {}
    for name, spec in data.items():
        result[name] = DependencyMapping(
            name=name,
            path=Path(spec["path"]),
            sources=spec["sources"]
        )
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="List source file dependencies")
    parser.add_argument("source", help="Source file to analyze")
    parser.add_argument("--deps", help="JSON dependency specification")
    parser.add_argument("--project-root", help="Explicit project root for import resolution")
    parser.add_argument("--sources", help="JSON list of source directories to search for imports")
    parser.add_argument("--record", action="store_true",
                        help="Print the closure and what it depends on, as JSON")
    args = parser.parse_args()

    source_path = args.source
    dependencies = parse_deps_arg(args.deps) if args.deps else None
    project_root = args.project_root
    source_roots = json.loads(args.sources) if args.sources else None

    try:
        closure = collect_closure(source_path, project_root=project_root,
                                  dependencies=dependencies, source_roots=source_roots)
        if args.record:
            print(json.dumps(closure))
        else:
            for f in closure["files"]:
                print(f)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
