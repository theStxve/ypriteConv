"""
CLI Mode - Command-Line Interface for ypriteConvert

Provides full batch processing capabilities with pipeline support.

Usage examples:
    # Simple conversion
    python cli.py --input file.mp4 --to mp3 --quality high

    # Batch conversion
    python cli.py --batch *.jpg --to webp --output ./converted/

    # Apply pipeline preset
    python cli.py --preset "Podcast Publisher" --input video.mov

    # Dry-run mode
    python cli.py --dry-run --preset "YouTube Ready" --input video.avi
"""
import argparse
import sys
import os
from pathlib import Path
from typing import List, Tuple
import glob

# Windows consoles default to cp1252 -> printing ✓/✗ would crash
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Import with fallback for tqdm
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("Note: Install 'tqdm' for progress bars (pip install tqdm)")

from modules.pipeline_engine import Pipeline
from modules.pipeline_serializer import PresetLibrary
from pipeline_steps import ConversionStep, StepRegistry


class CLI:
    """Command-line interface handler"""

    def __init__(self):
        self.preset_library = PresetLibrary()
        self.dry_run = False
        self.json_output = False

    def parse_args(self):
        """Parse command-line arguments"""
        parser = argparse.ArgumentParser(
            prog='ypriteConvert',
            description='Professional file converter with pipeline support',
            epilog='For more information, visit: https://github.com/yourrepo'
        )

        # Input options
        input_group = parser.add_mutually_exclusive_group(required=False)
        input_group.add_argument('--input', '-i',
                                help='Input file path')
        input_group.add_argument('--batch', '-b',
                                help='Batch process files (supports wildcards like *.mp4)')

        # Output options
        parser.add_argument('--output', '-o',
                           help='Output directory or file path (default: same as input)')

        # Conversion options
        parser.add_argument('--to', '-t',
                           help='Target format (e.g. mp3, jpg, pdf)')
        parser.add_argument('--quality', '-q',
                           choices=['high', 'medium', 'low'],
                           default='medium',
                           help='Quality preset (default: medium)')

        # Pipeline options
        parser.add_argument('--preset', '-p',
                           help='Apply a pipeline preset by name')
        parser.add_argument('--list-presets',
                           action='store_true',
                           help='List all available presets')

        # Execution options
        parser.add_argument('--dry-run',
                           action='store_true',
                           help='Show what would be done without executing')
        parser.add_argument('--json',
                           action='store_true',
                           help='Output results as JSON (for scripting)')
        parser.add_argument('--verbose', '-v',
                           action='store_true',
                           help='Verbose output')

        args = parser.parse_args()

        # Validation
        if args.list_presets:
            return args

        if not args.input and not args.batch:
            parser.error("Either --input or --batch is required (or use --list-presets)")

        if not args.preset and not args.to:
            parser.error("Either --preset or --to is required")

        return args

    def list_presets(self):
        """List all available presets"""
        presets = self.preset_library.list_presets()

        if not presets:
            print("No presets found.")
            return

        print(f"\nAvailable Presets ({len(presets)}):\n")
        print("-" * 70)

        for preset in presets:
            print(f"  {preset['name']}")
            print(f"    Description: {preset['description']}")
            print(f"    File: {preset['filename']}")
            print()

    def collect_files(self, input_pattern: str) -> List[str]:
        """Collect files from input pattern or wildcard"""
        if os.path.isdir(input_pattern):
            # Whole folder (recursive)
            return [os.path.join(r, f) for r, _, fs in os.walk(input_pattern) for f in fs]
        if any(c in input_pattern for c in '*?['):
            files = glob.glob(input_pattern, recursive=True)
            return sorted(f for f in files if os.path.isfile(f))
        return [input_pattern] if os.path.isfile(input_pattern) else []

    def create_pipeline(self, args) -> Pipeline:
        """Create pipeline from arguments"""
        if args.preset:
            # Load preset pipeline
            preset_name = args.preset.replace('.json', '')
            pipeline = self.preset_library.get_preset(preset_name)
            if pipeline is None:
                # Allow display names like "Podcast Publisher" too
                for p in self.preset_library.list_presets():
                    if p['name'].lower() == preset_name.lower() or \
                            p['filename'][:-5] == preset_name.lower().replace(' ', '_'):
                        pipeline = self.preset_library.get_preset(p['filename'][:-5])
                        break

            if pipeline is None:
                raise ValueError(f"Preset not found: {args.preset}")

            return pipeline
        else:
            # Simple conversion pipeline
            pipeline = Pipeline(name="CLI Conversion")

            step = ConversionStep()
            step.configure(
                target_format=args.to,
                quality=args.quality
            )
            pipeline.add_step(step)

            return pipeline

    def process_file(self, input_file: str, output_file: str, pipeline: Pipeline) -> Tuple[bool, str]:
        """Process a single file through the pipeline"""
        if self.dry_run:
            return True, f"[DRY-RUN] Would convert: {input_file} -> {output_file}"

        try:
            success, message = pipeline.execute(input_file, output_file)
            if success and getattr(pipeline, 'last_output_file', None):
                message = pipeline.last_output_file
            return success, message
        except Exception as e:
            return False, f"Error: {str(e)}"

    def run(self):
        """Main CLI execution"""
        args = self.parse_args()

        # List presets mode
        if args.list_presets:
            self.list_presets()
            return 0

        # Set flags
        self.dry_run = args.dry_run
        self.json_output = args.json

        # Create pipeline
        try:
            pipeline = self.create_pipeline(args)
        except Exception as e:
            print(f"Error creating pipeline: {e}")
            return 1

        # Collect input files (--input also accepts wildcards / folders)
        files = self.collect_files(args.input or args.batch)

        if not files:
            print("No input files found.")
            return 1

        if args.verbose or self.dry_run:
            print(f"\nPipeline: {pipeline.name}")
            print(f"Files to process: {len(files)}")
            print(f"Output: {args.output or 'same directory as input'}\n")

        # Determine output paths. The pipeline fixes the extension to the real
        # final format, so we only need the right folder + base name here.
        out = args.output
        out_is_dir = bool(out) and (
            os.path.isdir(out) or len(files) > 1 or out.endswith(('/', '\\')) or not Path(out).suffix)
        if out_is_dir and not self.dry_run:
            os.makedirs(out, exist_ok=True)

        tasks = []
        for input_file in files:
            src = Path(input_file)
            ext = args.to or src.suffix.lstrip('.')
            name = f"{src.stem}.{ext}" if args.to else f"{src.stem}_converted.{ext}"
            if out and not out_is_dir:
                output_file = out
            else:
                folder = Path(out) if out else src.parent
                output_file = str(folder / name)
                if os.path.abspath(output_file) == os.path.abspath(input_file):
                    output_file = str(folder / f"{src.stem}_converted.{ext}")
            tasks.append((input_file, output_file))

        # Process files
        results = []

        if HAS_TQDM and not self.json_output:
            # Progress bar
            iterator = tqdm(tasks, desc="Converting", unit="file")
        else:
            iterator = tasks

        for input_file, output_file in iterator:
            success, message = self.process_file(input_file, output_file, pipeline)
            results.append({
                'input': input_file,
                'output': message if success and not self.dry_run else output_file,
                'success': success,
                'message': message
            })

            if not HAS_TQDM and not self.json_output:
                status = "✓" if success else "✗"
                print(f"{status} {Path(input_file).name} -> {Path(output_file).name}")

        # Output results
        if self.json_output:
            import json
            print(json.dumps(results, indent=2))
        else:
            # Summary
            successful = sum(1 for r in results if r['success'])
            failed = len(results) - successful

            print(f"\n{'=' * 50}")
            print(f"Completed: {successful}/{len(results)} successful")
            if failed > 0:
                print(f"Failed: {failed}")
                print("\nFailed files:")
                for r in results:
                    if not r['success']:
                        print(f"  ✗ {r['input']}: {r['message']}")
            print(f"{'=' * 50}")

        # Return exit code
        return 0 if all(r['success'] for r in results) else 1


def main():
    """Entry point for CLI"""
    cli = CLI()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
