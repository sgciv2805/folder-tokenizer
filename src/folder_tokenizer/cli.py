"""Command-line interface for Folder Tokenizer."""

import argparse
import json
import sys
from pathlib import Path

from .tokenizer import DEFAULT_MODEL, POPULAR_MODELS, FolderTokenizer


def format_number(n: int) -> str:
    """Format large numbers with commas."""
    return f"{n:,}"


def print_summary(result, verbose: bool = False):
    """Print analysis summary to console."""
    print("\n" + "=" * 60)
    print("📊 FOLDER TOKENIZER RESULTS")
    print("=" * 60)

    print(f"\n📁 Folder: {result.folder_path}")
    print(f"🤖 Model: {result.model_name}")

    print("\n📈 Summary:")
    print(f"   Total Tokens:     {format_number(result.total_tokens)}")
    print(f"   Total Characters: {format_number(result.total_chars)}")
    print(f"   Files Processed:  {format_number(result.successful_files)}")
    print(f"   Failed Files:     {format_number(result.failed_files)}")

    if result.by_type:
        print("\n📊 Breakdown by File Type:")
        print("-" * 50)
        print(f"{'Type':<12} {'Files':>8} {'Tokens':>12} {'Avg/File':>10}")
        print("-" * 50)

        sorted_types = sorted(
            result.by_type.items(),
            key=lambda x: x[1]["tokens"],
            reverse=True,
        )

        for file_type, stats in sorted_types:
            avg = stats["tokens"] // stats["files"] if stats["files"] > 0 else 0
            print(
                f"{file_type:<12} {stats['files']:>8} "
                f"{format_number(stats['tokens']):>12} {format_number(avg):>10}"
            )

    if verbose and result.file_results:
        print("\n📋 Top 10 Files by Token Count:")
        print("-" * 70)

        successful = [f for f in result.file_results if f.success]
        top_files = sorted(successful, key=lambda x: x.tokens, reverse=True)[:10]

        for fr in top_files:
            name = Path(fr.path).name
            if len(name) > 40:
                name = name[:37] + "..."
            print(f"   {name:<42} {format_number(fr.tokens):>12} tokens")

    if result.failed_files > 0:
        print(f"\n⚠️  {result.failed_files} file(s) failed to process.")
        if verbose:
            failed = [f for f in result.file_results if not f.success][:5]
            for fr in failed:
                print(f"   - {Path(fr.path).name}: {fr.error}")

    print("\n" + "=" * 60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze token counts for all documents in a folder.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  folder-tokenizer /path/to/folder
  folder-tokenizer /path/to/folder --model bert-base-uncased
  folder-tokenizer /path/to/folder --output results.json
  folder-tokenizer /path/to/folder -v --csv results.csv

Popular models:
"""
        + "\n".join(f"  {name:<35} {label}" for name, label in POPULAR_MODELS),
    )

    parser.add_argument(
        "folder",
        type=str,
        help="Path to the folder to analyze",
    )

    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"HuggingFace tokenizer model name (default: {DEFAULT_MODEL})",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output results to JSON file",
    )

    parser.add_argument(
        "--csv",
        type=str,
        help="Output detailed results to CSV file",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed output",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )

    args = parser.parse_args()

    # Validate folder
    folder_path = Path(args.folder)
    if not folder_path.exists():
        print(f"Error: Folder not found: {args.folder}", file=sys.stderr)
        sys.exit(1)

    if not folder_path.is_dir():
        print(f"Error: Not a directory: {args.folder}", file=sys.stderr)
        sys.exit(1)

    # Initialize tokenizer
    if not args.quiet:
        print(f"Loading tokenizer: {args.model}...")

    try:
        tokenizer = FolderTokenizer(model_name=args.model)
        # Pre-load the tokenizer
        _ = tokenizer.tokenizer
    except Exception as e:
        print(f"Error loading tokenizer: {e}", file=sys.stderr)
        sys.exit(1)

    # Process folder
    if not args.quiet:
        print(f"Analyzing folder: {args.folder}")

    try:
        result = tokenizer.process_folder(args.folder)
    except Exception as e:
        print(f"Error processing folder: {e}", file=sys.stderr)
        sys.exit(1)

    # Print summary
    if not args.quiet:
        print_summary(result, verbose=args.verbose)

    # Export to JSON if requested
    if args.output:
        json_data = {
            "summary": {
                "folder_path": result.folder_path,
                "model_name": result.model_name,
                "total_tokens": result.total_tokens,
                "total_chars": result.total_chars,
                "total_files": result.total_files,
                "successful_files": result.successful_files,
                "failed_files": result.failed_files,
            },
            "by_type": result.by_type,
            "files": [
                {
                    "path": fr.path,
                    "tokens": fr.tokens,
                    "chars": fr.chars,
                    "file_type": fr.file_type,
                    "success": fr.success,
                    "error": fr.error,
                    "source_archive": fr.source_archive,
                }
                for fr in result.file_results
            ],
        }

        with open(args.output, "w") as f:
            json.dump(json_data, f, indent=2)

        print(f"\n✅ Results saved to: {args.output}")

    # Export to CSV if requested
    if args.csv:
        import csv

        with open(args.csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["Path", "Type", "Tokens", "Characters", "Success", "Error", "Source Archive"]
            )

            for fr in result.file_results:
                writer.writerow(
                    [
                        fr.path,
                        fr.file_type,
                        fr.tokens,
                        fr.chars,
                        fr.success,
                        fr.error or "",
                        fr.source_archive or "",
                    ]
                )

        print(f"✅ CSV saved to: {args.csv}")

    # Return total tokens for scripting
    if args.quiet:
        print(result.total_tokens)

    sys.exit(0)


if __name__ == "__main__":
    main()
