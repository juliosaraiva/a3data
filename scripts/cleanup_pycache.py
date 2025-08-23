#!/usr/bin/env python3
"""
Python Cache Cleanup Script

This script recursively finds and removes all __pycache__ directories and .pyc files
from the project directory tree. It's useful for cleaning up Python bytecode files
that can accumulate during development and testing.

Usage:
    python scripts/cleanup_pycache.py

    # Or with uv
    uv run python scripts/cleanup_pycache.py

    # Or make it executable and run directly
    chmod +x scripts/cleanup_pycache.py
    ./scripts/cleanup_pycache.py
"""

import argparse
import os
import shutil
import sys
from pathlib import Path


def find_cache_files_and_dirs(root_dir: Path) -> tuple[list[Path], list[Path]]:
    """
    Find all __pycache__ directories and .pyc files recursively.

    Args:
        root_dir: Root directory to search from

    Returns:
        Tuple of (pycache_dirs, pyc_files)
    """
    pycache_dirs: list[Path] = []
    pyc_files: list[Path] = []

    for root, dirs, files in os.walk(root_dir):
        root_path = Path(root)

        # Find __pycache__ directories
        if "__pycache__" in dirs:
            pycache_path = root_path / "__pycache__"
            pycache_dirs.append(pycache_path)
            # Remove from dirs to avoid walking into it
            dirs.remove("__pycache__")

        # Find .pyc files (in case they're outside __pycache__ dirs)
        for file in files:
            if file.endswith((".pyc", ".pyo")):
                pyc_files.append(root_path / file)

    return pycache_dirs, pyc_files


def cleanup_cache_files(pycache_dirs: list[Path], pyc_files: list[Path], dry_run: bool = False) -> tuple[int, int]:
    """
    Remove __pycache__ directories and .pyc files.

    Args:
        pycache_dirs: List of __pycache__ directories to remove
        pyc_files: List of .pyc files to remove
        dry_run: If True, only print what would be removed without actually removing

    Returns:
        Tuple of (removed_dirs_count, removed_files_count)
    """
    removed_dirs = 0
    removed_files = 0

    # Remove __pycache__ directories
    for pycache_dir in pycache_dirs:
        try:
            if dry_run:
                print(f"[DRY RUN] Would remove directory: {pycache_dir}")
            else:
                shutil.rmtree(pycache_dir)
                print(f"Removed directory: {pycache_dir}")
            removed_dirs += 1
        except Exception as e:
            print(f"Error removing directory {pycache_dir}: {e}", file=sys.stderr)

    # Remove individual .pyc files
    for pyc_file in pyc_files:
        try:
            if dry_run:
                print(f"[DRY RUN] Would remove file: {pyc_file}")
            else:
                pyc_file.unlink()
                print(f"Removed file: {pyc_file}")
            removed_files += 1
        except Exception as e:
            print(f"Error removing file {pyc_file}: {e}", file=sys.stderr)

    return removed_dirs, removed_files


def get_directory_size(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                file_path = Path(dirpath) / filename
                try:
                    total_size += file_path.stat().st_size
                except (OSError, FileNotFoundError):
                    # Handle broken symlinks or permission issues
                    pass
    except (OSError, PermissionError):
        pass
    return total_size


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Clean up Python __pycache__ directories and .pyc files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/cleanup_pycache.py                  # Clean current directory
    python scripts/cleanup_pycache.py --dry-run        # Preview what would be removed
    python scripts/cleanup_pycache.py --path /some/dir # Clean specific directory
    python scripts/cleanup_pycache.py --quiet          # Minimal output
        """,
    )

    parser.add_argument("--path", type=Path, default=Path.cwd(), help="Root directory to clean (default: current directory)")

    parser.add_argument("--dry-run", action="store_true", help="Preview what would be removed without actually removing")

    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output, only show summary")

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output with detailed information")

    return parser


def validate_directory(path: Path) -> Path:
    """Validate that the given path exists and is a directory."""
    if not path.exists():
        print(f"Error: Directory '{path}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not path.is_dir():
        print(f"Error: '{path}' is not a directory", file=sys.stderr)
        sys.exit(1)

    return path.resolve()


def print_scan_results(pycache_dirs: list[Path], pyc_files: list[Path], total_size: int, verbose: bool, quiet: bool) -> None:
    """Print scan results with appropriate verbosity level."""
    if verbose or not quiet:
        print(f"Found {len(pycache_dirs)} __pycache__ directories")
        print(f"Found {len(pyc_files)} .pyc files")
        print(f"Total space to be freed: {format_size(total_size)}")

        if verbose:
            print("\n__pycache__ directories:")
            for pycache_dir in pycache_dirs:
                size = get_directory_size(pycache_dir)
                print(f"  {pycache_dir} ({format_size(size)})")

            if pyc_files:
                print("\n.pyc files:")
                for pyc_file in pyc_files:
                    try:
                        size = pyc_file.stat().st_size
                        print(f"  {pyc_file} ({format_size(size)})")
                    except (OSError, FileNotFoundError):
                        print(f"  {pyc_file} (size unknown)")

        print("─" * 60)


def main() -> int:
    """Main function to clean up Python cache files."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    root_dir = validate_directory(args.path)

    if not args.quiet:
        action = "Scanning" if not args.dry_run else "Dry run scanning"
        print(f"{action} for Python cache files in: {root_dir}")
        print("─" * 60)

    # Find cache files and directories
    pycache_dirs, pyc_files = find_cache_files_and_dirs(root_dir)

    if not pycache_dirs and not pyc_files:
        if not args.quiet:
            print("✅ No Python cache files found. Directory is already clean!")
        return 0

    # Calculate total size that would be freed
    total_size = 0
    for pycache_dir in pycache_dirs:
        total_size += get_directory_size(pycache_dir)
    for pyc_file in pyc_files:
        try:
            total_size += pyc_file.stat().st_size
        except (OSError, FileNotFoundError):
            pass

    # Print scan results
    print_scan_results(pycache_dirs, pyc_files, total_size, args.verbose, args.quiet)

    # Clean up cache files
    if args.dry_run and not args.quiet:
        print("DRY RUN MODE - No files will actually be removed")
        print("─" * 60)

    removed_dirs, removed_files = cleanup_cache_files(pycache_dirs, pyc_files, dry_run=args.dry_run)

    # Summary
    if not args.quiet:
        print("─" * 60)
        action = "Would remove" if args.dry_run else "Removed"
        print(f"✅ {action} {removed_dirs} __pycache__ directories")
        print(f"✅ {action} {removed_files} .pyc files")
        print(f"✅ {action.replace('remove', 'free')} {format_size(total_size)} of disk space")

        if args.dry_run:
            print("\nTo actually remove these files, run without --dry-run flag")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
