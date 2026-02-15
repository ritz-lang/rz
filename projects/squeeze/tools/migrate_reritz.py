#!/usr/bin/env python3
"""
Migrate Squeeze codebase to RERITZ syntax.

Usage:
    python3 tools/migrate_reritz.py [--dry-run] [--phase N]

Phases:
    1: Attributes (@test -> [[test]])
    2: Address-of (&x -> @x)
    3: C-strings (c"..." -> "...".as_cstr())

By default, runs phases 1-2. Phase 3 requires ritzlib updates.
"""

import re
import sys
import argparse
from pathlib import Path
from typing import Tuple, List


def migrate_attributes(content: str) -> Tuple[str, int]:
    """
    Migrate @attr to [[attr]] syntax.

    Examples:
        @test           -> [[test]]
        @inline         -> [[inline]]
        @packed         -> [[packed]]
    """
    count = 0

    def replace(m):
        nonlocal count
        count += 1
        return f'[[{m.group(1)}]]'

    # Match @identifier at start of line (attributes)
    content = re.sub(r'^@(\w+)\s*$', replace, content, flags=re.MULTILINE)

    return content, count


def migrate_address_of(content: str) -> Tuple[str, int]:
    """
    Migrate &x to @x for address-of operations.

    Must carefully avoid:
    - Bitwise AND: a & b
    - Reference types in signatures (handled separately in future)

    Patterns we convert:
        &var[      -> @var[       (array element address)
        &var)      -> @var)       (in function call)
        &var,      -> @var,       (in argument list)
        (&var      -> (@var       (address in parens)
        = &var     -> = @var      (assignment)
        : &var     -> : @var      (after colon - struct field init)
    """
    count = 0

    def make_replacer():
        def replace(m):
            nonlocal count
            count += 1
            groups = m.groups()
            # Reconstruct with @ instead of &
            prefix = groups[0] if groups[0] else ''
            ident = groups[1]
            suffix = groups[2] if len(groups) > 2 and groups[2] else ''
            return f'{prefix}@{ident}{suffix}'
        return replace

    patterns = [
        # &ident[ -> @ident[  (array indexing)
        (r'&([a-zA-Z_][a-zA-Z0-9_]*)\[', r'@\1['),

        # &ident) -> @ident)  (end of function arg)
        (r'&([a-zA-Z_][a-zA-Z0-9_]*)\)', r'@\1)'),

        # &ident, -> @ident,  (function arg separator)
        (r'&([a-zA-Z_][a-zA-Z0-9_]*),', r'@\1,'),

        # (&ident -> (@ident  (start of parens)
        (r'\(&([a-zA-Z_][a-zA-Z0-9_]*)', r'(@\1'),

        # = &ident -> = @ident  (assignment)
        (r'= &([a-zA-Z_][a-zA-Z0-9_]*)', r'= @\1'),

        # : &ident -> : @ident  (struct field or type annotation)
        (r': &([a-zA-Z_][a-zA-Z0-9_]*)', r': @\1'),

        # return &ident -> return @ident
        (r'\breturn &([a-zA-Z_][a-zA-Z0-9_]*)', r'return @\1'),
    ]

    for pattern, replacement in patterns:
        matches = len(re.findall(pattern, content))
        count += matches
        content = re.sub(pattern, replacement, content)

    return content, count


def migrate_cstrings(content: str) -> Tuple[str, int]:
    """
    Migrate c"..." to "...".as_cstr().

    Note: This requires ritzlib to provide as_cstr() method on StrView.
    """
    count = 0

    def replace(m):
        nonlocal count
        count += 1
        string_content = m.group(1)
        return f'"{string_content}".as_cstr()'

    # Match c"..." strings
    content = re.sub(r'c"([^"]*)"', replace, content)

    return content, count


def migrate_file(path: Path, phases: List[int], dry_run: bool = False) -> dict:
    """Migrate a single file through specified phases."""
    content = path.read_text()
    original = content
    stats = {'attributes': 0, 'address_of': 0, 'cstrings': 0}

    if 1 in phases:
        content, count = migrate_attributes(content)
        stats['attributes'] = count

    if 2 in phases:
        content, count = migrate_address_of(content)
        stats['address_of'] = count

    if 3 in phases:
        content, count = migrate_cstrings(content)
        stats['cstrings'] = count

    changed = content != original

    if changed and not dry_run:
        path.write_text(content)

    return {'path': path, 'changed': changed, 'stats': stats}


def main():
    parser = argparse.ArgumentParser(description='Migrate Squeeze to RERITZ syntax')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would change without modifying files')
    parser.add_argument('--phase', type=int, action='append',
                        help='Run specific phase(s). Can be specified multiple times.')
    parser.add_argument('--all-phases', action='store_true',
                        help='Run all phases including c-string migration')
    parser.add_argument('files', nargs='*',
                        help='Specific files to migrate (default: lib/*.ritz test/*.ritz)')
    args = parser.parse_args()

    # Determine phases to run
    if args.all_phases:
        phases = [1, 2, 3]
    elif args.phase:
        phases = args.phase
    else:
        phases = [1, 2]  # Default: attributes and address-of only

    # Determine files to migrate
    if args.files:
        paths = [Path(f) for f in args.files]
    else:
        paths = list(Path('lib').glob('*.ritz')) + list(Path('test').glob('*.ritz'))

    if not paths:
        print("No .ritz files found to migrate")
        return 1

    print(f"RERITZ Migration - Phases: {phases}")
    print(f"{'DRY RUN - ' if args.dry_run else ''}Processing {len(paths)} files...")
    print()

    total_stats = {'attributes': 0, 'address_of': 0, 'cstrings': 0}
    changed_files = 0

    for path in sorted(paths):
        result = migrate_file(path, phases, args.dry_run)

        if result['changed']:
            changed_files += 1
            stats = result['stats']
            changes = []
            if stats['attributes']:
                changes.append(f"@attr→[[attr]]: {stats['attributes']}")
            if stats['address_of']:
                changes.append(f"&x→@x: {stats['address_of']}")
            if stats['cstrings']:
                changes.append(f'c"..."→as_cstr(): {stats["cstrings"]}')

            print(f"  {path}: {', '.join(changes)}")

            for key in total_stats:
                total_stats[key] += stats[key]

    print()
    print(f"Summary:")
    print(f"  Files changed: {changed_files}/{len(paths)}")
    print(f"  Attributes migrated: {total_stats['attributes']}")
    print(f"  Address-of migrated: {total_stats['address_of']}")
    print(f"  C-strings migrated: {total_stats['cstrings']}")

    if args.dry_run:
        print()
        print("(Dry run - no files were modified)")

    return 0


if __name__ == '__main__':
    sys.exit(main())
