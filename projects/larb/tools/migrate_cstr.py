#!/usr/bin/env python3
"""
RFC String API Migration Tool

Migrates Ritz code from C-style strings to idiomatic StrView/String usage.

Transformations:
1. c"string" -> "string" (when used with StrView APIs)
2. c"string" -> "string".as_ptr() (when passed to *u8 functions)
3. streq(a, b) -> strview_eq(@a, @b) (when args are StrView)

Usage:
    python migrate_cstr.py path/to/file.ritz        # Preview changes
    python migrate_cstr.py path/to/file.ritz --apply # Apply changes
    python migrate_cstr.py path/to/dir/ --apply      # Migrate directory
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Functions that take *u8 and need .as_ptr()
PTR_FUNCTIONS = {
    'sha256', 'sha256_update', 'sha512', 'sha512_update',
    'hmac_sha256', 'hmac_sha256_init', 'hmac_sha512',
    'aes_encrypt', 'aes_decrypt', 'aes_init',
    'chacha20_encrypt', 'chacha20_init',
    'hkdf_extract', 'hkdf_expand',
    'memcpy', 'memset', 'memmove', 'memcmp', 'mem_eq',
    'strlen', 'strcpy', 'strcat', 'strcmp', 'streq',
    'hash_eq_hex',  # Helper in crypto tests
    'write', 'read', 'open', 'print',  # syscalls
    'puts', 'printf', 'sprintf',  # FFI
}

# Functions that take StrView - no transformation needed
STRVIEW_FUNCTIONS = {
    'strview_eq', 'strview_cmp', 'strview_contains',
    'strview_starts_with', 'strview_ends_with',
    'strview_find', 'strview_slice',
}


def find_cstring_literals(content: str) -> List[Tuple[int, int, str]]:
    """Find all c"..." literals and return (start, end, value) tuples."""
    # Match c"..." but NOT across newlines (single-line strings only)
    # Handle escape sequences properly: \" within the string
    pattern = re.compile(r'c"(?:[^"\\\n]|\\.)*"')
    matches = []
    for m in pattern.finditer(content):
        matches.append((m.start(), m.end(), m.group()))
    return matches


def get_function_context(content: str, pos: int) -> str:
    """Get the function name that this literal is being passed to."""
    # Look backwards for function call pattern: name(
    before = content[:pos]
    # Find the most recent '(' before our position
    paren_pos = before.rfind('(')
    if paren_pos == -1:
        return None

    # Extract potential function name (alphanumeric before the paren)
    name_end = paren_pos
    name_start = name_end - 1
    while name_start >= 0 and (before[name_start].isalnum() or before[name_start] == '_'):
        name_start -= 1
    name_start += 1

    if name_start < name_end:
        return before[name_start:name_end]
    return None


def needs_as_ptr(content: str, pos: int) -> bool:
    """Check if the c"..." at pos needs .as_ptr() transformation."""
    func = get_function_context(content, pos)
    if func and func in PTR_FUNCTIONS:
        return True

    # Check for assignment to *u8 variable
    # Pattern: let x: *u8 = c"..."
    line_start = content.rfind('\n', 0, pos) + 1
    line = content[line_start:pos]
    if '*u8' in line and '=' in line:
        return True

    return False


def migrate_file(filepath: Path, apply: bool = False) -> Tuple[str, List[str]]:
    """Migrate a single file. Returns (new_content, changes)."""
    content = filepath.read_text()
    changes = []

    # Find all c"..." literals
    literals = find_cstring_literals(content)

    if not literals:
        return content, []

    # Process in reverse order to preserve positions
    new_content = content
    for start, end, literal in reversed(literals):
        # Extract the string value without c prefix
        string_value = literal[1:]  # Remove 'c' prefix

        if needs_as_ptr(content, start):
            # Transform to "string".as_ptr()
            replacement = f'{string_value}.as_ptr()'
            change = f'  {literal} -> {replacement}'
        else:
            # Just remove the c prefix
            replacement = string_value
            change = f'  {literal} -> {replacement}'

        changes.append(change)
        new_content = new_content[:start] + replacement + new_content[end:]

    if apply and changes:
        filepath.write_text(new_content)

    return new_content, changes


def migrate_directory(dirpath: Path, apply: bool = False) -> dict:
    """Migrate all .ritz files in a directory."""
    results = {}
    for filepath in sorted(dirpath.rglob('*.ritz')):
        _, changes = migrate_file(filepath, apply)
        if changes:
            results[filepath] = changes
    return results


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = Path(sys.argv[1])
    apply = '--apply' in sys.argv

    if target.is_file():
        new_content, changes = migrate_file(target, apply)
        if changes:
            print(f"{'Applied' if apply else 'Would apply'} changes to {target}:")
            for c in changes:
                print(c)
            if not apply:
                print(f"\nRun with --apply to apply changes")
        else:
            print(f"No c\"...\" literals found in {target}")

    elif target.is_dir():
        results = migrate_directory(target, apply)
        if results:
            total = sum(len(c) for c in results.values())
            print(f"{'Applied' if apply else 'Would apply'} {total} changes across {len(results)} files:")
            for filepath, changes in results.items():
                print(f"\n{filepath}:")
                for c in changes:
                    print(c)
            if not apply:
                print(f"\nRun with --apply to apply changes")
        else:
            print(f"No c\"...\" literals found in {target}")

    else:
        print(f"Error: {target} not found")
        sys.exit(1)


if __name__ == '__main__':
    main()
