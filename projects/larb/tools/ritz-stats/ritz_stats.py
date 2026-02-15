#!/usr/bin/env python3
"""
ritz-stats: Source code analytics for Ritz

Provides metrics similar to cloc/sloccount but tailored for Ritz:
- Lines of code (total, source, comments, blank)
- Function-level metrics (line count, cyclomatic complexity)
- Struct/enum counts
- Per-file and aggregate statistics

This is a Python bootstrap - the real tool will be in Ritz.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FunctionInfo:
    name: str
    file: str
    start_line: int
    end_line: int = 0
    line_count: int = 0
    code_lines: int = 0
    cyclomatic_complexity: int = 1
    max_indent: int = 0


@dataclass
class FileStats:
    path: str
    total_lines: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    code_lines: int = 0
    functions: list = field(default_factory=list)
    structs: list = field(default_factory=list)
    enums: list = field(default_factory=list)
    imports: list = field(default_factory=list)


@dataclass
class ProjectStats:
    files: list = field(default_factory=list)
    total_lines: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    code_lines: int = 0
    function_count: int = 0
    struct_count: int = 0
    enum_count: int = 0
    avg_function_length: float = 0.0
    avg_cyclomatic_complexity: float = 0.0
    max_cyclomatic_complexity: int = 0
    deepest_nesting: int = 0
    hottest_function: Optional[FunctionInfo] = None


def count_indent(line: str) -> int:
    """Count indentation level (4 spaces = 1 level)."""
    spaces = len(line) - len(line.lstrip(' '))
    return spaces // 4


def calculate_complexity(lines: list[str]) -> int:
    """Calculate cyclomatic complexity for a function body."""
    complexity = 1  # Base complexity

    for line in lines:
        trimmed = line.strip()

        # Control flow keywords
        if trimmed.startswith(('if ', 'if(')):
            complexity += 1
        if trimmed.startswith(('elif ', 'elif(')):
            complexity += 1
        if trimmed.startswith(('while ', 'while(')):
            complexity += 1
        if trimmed.startswith('for '):
            complexity += 1
        if trimmed.startswith('loop'):
            complexity += 1

        # Match arms
        if ' => ' in trimmed or trimmed.endswith(' =>'):
            complexity += 1

        # Logical operators
        if ' and ' in trimmed:
            complexity += 1
        if ' or ' in trimmed:
            complexity += 1

        # Error propagation
        if '?' in trimmed:
            complexity += 1

    return complexity


def analyze_file(path: Path) -> FileStats:
    """Analyze a single Ritz file."""
    stats = FileStats(path=str(path))

    try:
        content = path.read_text()
    except Exception as e:
        return stats

    lines = content.split('\n')
    stats.total_lines = len(lines)

    current_fn: Optional[tuple] = None  # (name, start_line, base_indent)
    fn_lines: list[str] = []

    for i, line in enumerate(lines):
        line_num = i + 1
        trimmed = line.strip()
        indent = count_indent(line)

        # Classify line
        if not trimmed:
            stats.blank_lines += 1
        elif trimmed.startswith('#'):
            stats.comment_lines += 1
        else:
            stats.code_lines += 1

        # Track imports
        if trimmed.startswith('import '):
            stats.imports.append(trimmed[7:])

        # Track struct/enum definitions
        if trimmed.startswith('struct '):
            name = trimmed[7:].split()[0] if trimmed[7:] else ''
            stats.structs.append({'name': name, 'line': line_num})
        elif trimmed.startswith('enum '):
            name = trimmed[5:].split()[0] if trimmed[5:] else ''
            stats.enums.append({'name': name, 'line': line_num})

        # Track function definitions
        if trimmed.startswith('fn '):
            # Close previous function if any
            if current_fn:
                fn_name, fn_start, _ = current_fn
                fn_info = FunctionInfo(
                    name=fn_name,
                    file=str(path),
                    start_line=fn_start,
                    end_line=line_num - 1,
                    line_count=line_num - 1 - fn_start,
                    code_lines=len([l for l in fn_lines if l.strip() and not l.strip().startswith('#')]),
                    cyclomatic_complexity=calculate_complexity(fn_lines),
                    max_indent=max((count_indent(l) for l in fn_lines), default=0)
                )
                stats.functions.append(fn_info)

            # Extract function name
            after_fn = trimmed[3:]
            paren_idx = after_fn.find('(')
            name = after_fn[:paren_idx].strip() if paren_idx > 0 else after_fn.split()[0] if after_fn else ''

            current_fn = (name, line_num, indent)
            fn_lines = []
        elif current_fn:
            _, _, base_indent = current_fn
            if indent > base_indent or not trimmed:
                fn_lines.append(line)
            elif trimmed and not trimmed.startswith('#'):
                # Dedented out of function
                fn_name, fn_start, _ = current_fn
                fn_info = FunctionInfo(
                    name=fn_name,
                    file=str(path),
                    start_line=fn_start,
                    end_line=line_num - 1,
                    line_count=line_num - 1 - fn_start,
                    code_lines=len([l for l in fn_lines if l.strip() and not l.strip().startswith('#')]),
                    cyclomatic_complexity=calculate_complexity(fn_lines),
                    max_indent=max((count_indent(l) for l in fn_lines), default=0)
                )
                stats.functions.append(fn_info)
                current_fn = None
                fn_lines = []

    # Close final function
    if current_fn:
        fn_name, fn_start, _ = current_fn
        fn_info = FunctionInfo(
            name=fn_name,
            file=str(path),
            start_line=fn_start,
            end_line=stats.total_lines,
            line_count=stats.total_lines - fn_start,
            code_lines=len([l for l in fn_lines if l.strip() and not l.strip().startswith('#')]),
            cyclomatic_complexity=calculate_complexity(fn_lines),
            max_indent=max((count_indent(l) for l in fn_lines), default=0)
        )
        stats.functions.append(fn_info)

    return stats


def collect_ritz_files(root: Path) -> list[Path]:
    """Collect all .ritz files, ignoring git submodules."""
    files = []

    # Read .gitmodules to find submodule paths
    submodule_paths = set()
    gitmodules = root / '.gitmodules'
    if gitmodules.exists():
        try:
            content = gitmodules.read_text()
            for line in content.split('\n'):
                if line.strip().startswith('path = '):
                    submodule_paths.add(line.strip()[7:])
        except:
            pass

    for path in root.rglob('*.ritz'):
        # Skip build directories
        path_str = str(path.relative_to(root))
        if '/build/' in path_str or path_str.startswith('build/'):
            continue
        if '/target/' in path_str or path_str.startswith('target/'):
            continue

        # Skip submodules
        skip = False
        for submod in submodule_paths:
            if path_str.startswith(submod + '/') or path_str.startswith(submod + os.sep):
                skip = True
                break
        if skip:
            continue

        files.append(path)

    return sorted(files)


def analyze_project(root: Path) -> ProjectStats:
    """Analyze entire project."""
    project = ProjectStats()

    files = collect_ritz_files(root)

    total_fn_lines = 0
    total_complexity = 0

    for path in files:
        stats = analyze_file(path)

        project.total_lines += stats.total_lines
        project.blank_lines += stats.blank_lines
        project.comment_lines += stats.comment_lines
        project.code_lines += stats.code_lines
        project.struct_count += len(stats.structs)
        project.enum_count += len(stats.enums)

        for fn in stats.functions:
            project.function_count += 1
            total_fn_lines += fn.code_lines
            total_complexity += fn.cyclomatic_complexity

            if fn.cyclomatic_complexity > project.max_cyclomatic_complexity:
                project.max_cyclomatic_complexity = fn.cyclomatic_complexity
                project.hottest_function = fn

            if fn.max_indent > project.deepest_nesting:
                project.deepest_nesting = fn.max_indent

        project.files.append(stats)

    if project.function_count > 0:
        project.avg_function_length = total_fn_lines / project.function_count
        project.avg_cyclomatic_complexity = total_complexity / project.function_count

    return project


def print_summary(stats: ProjectStats):
    """Print formatted summary."""
    print("=" * 60)
    print("                    RITZ SOURCE STATISTICS")
    print("=" * 60)
    print()

    # Overall metrics
    print("LINES OF CODE")
    print("-" * 40)
    if stats.total_lines > 0:
        print(f"  Total lines:      {stats.total_lines:,}")
        print(f"  Code lines:       {stats.code_lines:,} ({100*stats.code_lines/stats.total_lines:.1f}%)")
        print(f"  Comment lines:    {stats.comment_lines:,} ({100*stats.comment_lines/stats.total_lines:.1f}%)")
        print(f"  Blank lines:      {stats.blank_lines:,} ({100*stats.blank_lines/stats.total_lines:.1f}%)")
    else:
        print("  No lines found")
    print()

    # Structure counts
    print("DEFINITIONS")
    print("-" * 40)
    print(f"  Functions:        {stats.function_count:,}")
    print(f"  Structs:          {stats.struct_count:,}")
    print(f"  Enums:            {stats.enum_count:,}")
    print(f"  Files:            {len(stats.files):,}")
    print()

    # Complexity metrics
    print("COMPLEXITY")
    print("-" * 40)
    print(f"  Avg function length:       {stats.avg_function_length:.1f} lines")
    print(f"  Avg cyclomatic complexity: {stats.avg_cyclomatic_complexity:.2f}")
    print(f"  Max cyclomatic complexity: {stats.max_cyclomatic_complexity}")
    print(f"  Deepest nesting:           {stats.deepest_nesting} levels")
    print()


def print_hotspots(stats: ProjectStats):
    """Print high-complexity functions."""
    print("HOTSPOTS (Cyclomatic Complexity >= 10)")
    print("-" * 60)

    # Collect all functions
    all_fns = []
    for file_stats in stats.files:
        for fn in file_stats.functions:
            all_fns.append(fn)

    # Sort by complexity
    all_fns.sort(key=lambda f: f.cyclomatic_complexity, reverse=True)

    found = False
    for fn in all_fns[:15]:  # Top 15
        if fn.cyclomatic_complexity >= 10:
            found = True
            print(f"  CC {fn.cyclomatic_complexity:2d} | {fn.code_lines:3d} lines | {fn.file}:{fn.start_line} {fn.name}")

    if not found:
        print("  No functions with cyclomatic complexity >= 10")
    print()


def print_file_breakdown(stats: ProjectStats):
    """Print per-file stats."""
    print("FILE BREAKDOWN (by code lines)")
    print("-" * 60)

    # Sort files by code lines
    sorted_files = sorted(stats.files, key=lambda f: f.code_lines, reverse=True)

    for file_stats in sorted_files[:20]:  # Top 20
        rel_path = file_stats.path
        if len(rel_path) > 45:
            rel_path = "..." + rel_path[-42:]
        print(f"  {file_stats.code_lines:5d} | {len(file_stats.functions):3d} fn | {rel_path}")

    if len(sorted_files) > 20:
        print(f"  ... and {len(sorted_files) - 20} more files")
    print()


def print_json(stats: ProjectStats):
    """Print JSON output."""
    data = {
        "total_lines": stats.total_lines,
        "code_lines": stats.code_lines,
        "comment_lines": stats.comment_lines,
        "blank_lines": stats.blank_lines,
        "function_count": stats.function_count,
        "struct_count": stats.struct_count,
        "enum_count": stats.enum_count,
        "file_count": len(stats.files),
        "avg_function_length": round(stats.avg_function_length, 2),
        "avg_cyclomatic_complexity": round(stats.avg_cyclomatic_complexity, 2),
        "max_cyclomatic_complexity": stats.max_cyclomatic_complexity,
        "deepest_nesting": stats.deepest_nesting,
    }
    print(json.dumps(data, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Source code analytics for Ritz projects"
    )
    parser.add_argument("path", type=Path, nargs="?", default=Path("."),
                        help="File or directory to analyze")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show per-file breakdown")
    parser.add_argument("-j", "--json", action="store_true",
                        help="Output as JSON")

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    stats = analyze_project(args.path)

    if args.json:
        print_json(stats)
    else:
        print_summary(stats)
        print_hotspots(stats)
        if args.verbose:
            print_file_breakdown(stats)


if __name__ == "__main__":
    main()
