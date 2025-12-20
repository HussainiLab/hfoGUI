import argparse
import json
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from .core.Score import hilbert_detect_events
from .core.Tint_Matlab import ReadEEG, bits2uV, TintException


def _default_freqs(data_path: Path, max_freq: Optional[float]) -> Tuple[float, float]:
    """Choose sensible defaults based on file extension."""
    # Defaults mirror the GUI: 80 Hz min, 125 Hz max for EEG, 500 Hz max for EGF
    min_freq = 80.0
    if max_freq is not None:
        return min_freq, max_freq

    if data_path.suffix.lower().startswith('.egf'):
        return min_freq, 500.0

    return min_freq, 125.0


def _build_output_paths(data_path: Path, set_path: Optional[Path], output: Optional[Path]):
    method_tag = 'HIL'
    session_base = set_path.stem if set_path else data_path.stem

    if output:
        output_dir = output.parent
        scores_path = output_dir / "{}.txt".format(session_base)
        settings_path = output_dir / "{}_settings.json".format(session_base)
    else:
        base_dir = set_path.parent if set_path else data_path.parent
        scores_dir = base_dir / 'HFOScores' / session_base
        scores_path = scores_dir / ("{}_{}.txt".format(session_base, method_tag))
        settings_path = scores_dir / ("{}_{}_settings.json".format(session_base, method_tag))

    scores_path.parent.mkdir(parents=True, exist_ok=True)
    return scores_path, settings_path


def _find_data_files(directory: Path):
    """Find all .eeg and .egf files recursively in a directory.
    
    If both .eeg and .egf exist for the same basename, only return .egf
    since .eeg files typically don't contain HFOs.
    """
    eeg_files = list(directory.rglob('*.eeg'))
    egf_files = list(directory.rglob('*.egf'))
    
    # Create a set of (parent, stem) tuples for .egf files to handle same basenames in same folder
    egf_keys = {(f.parent, f.stem) for f in egf_files}
    
    # Filter out .eeg files that have a corresponding .egf file in the same folder
    filtered_eeg = [f for f in eeg_files if (f.parent, f.stem) not in egf_keys]
    
    return sorted(filtered_eeg + egf_files)


def _find_set_file(data_path: Path):
    """Find corresponding .set file for a data file."""
    set_path = data_path.with_suffix('.set')
    if set_path.exists():
        return set_path
    # Try in parent directory with same stem
    parent_set = data_path.parent / '{}.set'.format(data_path.stem)
    if parent_set.exists():
        return parent_set
    return None


def _process_single_file(data_path: Path, set_path: Optional[Path], args: argparse.Namespace):
    """Process a single data file with Hilbert detection.
    
    Returns:
        int: Number of events detected (for summary reporting).
    """
    if args.verbose:
        print('\nProcessing: {}'.format(data_path))

    raw_data, Fs = ReadEEG(str(data_path))

    if set_path and set_path.exists() and not args.skip_bits2uv:
        try:
            raw_data, _ = bits2uV(raw_data, str(data_path), str(set_path))
        except TintException as exc:
            if not args.skip_bits2uv:
                raise
            if args.verbose:
                print('  Warning: Proceeding without bits->uV conversion: {}'.format(exc))

    min_freq_default, max_freq_default = _default_freqs(data_path, args.max_freq)
    min_freq = args.min_freq if args.min_freq is not None else min_freq_default
    max_freq = args.max_freq if args.max_freq is not None else max_freq_default

    peak_sd = None if args.no_required_peak_threshold else float(args.required_peak_threshold_sd)

    params = {
        'epoch': float(args.epoch_sec),
        'sd_num': float(args.threshold_sd),
        'min_duration': float(args.min_duration_ms),
        'min_freq': float(min_freq),
        'max_freq': float(max_freq),
        'required_peak_number': int(args.required_peaks),
        'required_peak_sd': peak_sd,
        'boundary_fraction': float(args.boundary_percent) / 100.0,
        'verbose': args.verbose,
    }

    events = hilbert_detect_events(np.asarray(raw_data, dtype=float), Fs, **params)

    out_path = Path(args.output).expanduser() if args.output else None
    scores_path, settings_path = _build_output_paths(
        data_path,
        set_path if set_path and set_path.exists() else None,
        out_path,
    )

    with open(str(settings_path), 'w', encoding='utf-8') as f:
        json.dump(params, f, indent=2)

    df = pd.DataFrame({
        'ID#:': ['HIL{}'.format(idx + 1) for idx in range(len(events))],
        'Start Time(ms):': events[:, 0] if len(events) else [],
        'Stop Time(ms):': events[:, 1] if len(events) else [],
        'Settings File:': settings_path.as_posix(),
    })

    df.to_csv(str(scores_path), sep='\t', index=False)

    if args.verbose:
        print('  Saved settings -> {}'.format(settings_path))

    print('  Detected {} events; saved scores -> {}'.format(len(events), scores_path))
    
    return len(events)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='hfoGUI command-line utilities')
    sub = parser.add_subparsers(dest='command')

    hilbert = sub.add_parser('hilbert-batch', help='Run Hilbert-based automatic detection headlessly')
    hilbert.add_argument('-f', '--file', required=True, help='Path to .eeg/.egf file or directory to process recursively')
    hilbert.add_argument('-s', '--set-file', help='Optional .set file or directory; defaults to sibling of the data file')
    hilbert.add_argument('-o', '--output', help='Output directory; scores saved as <session>.txt, defaults to HFOScores/<session>/<session>_HIL.txt')
    hilbert.add_argument('--epoch-sec', type=float, default=5 * 60, help='Epoch length in seconds (default: 300)')
    hilbert.add_argument('--threshold-sd', type=float, default=3.0,
                         help='Envelope threshold in SD above mean (default: 3)')
    hilbert.add_argument('--min-duration-ms', type=float, default=10.0, help='Minimum event duration in ms (default: 10)')
    hilbert.add_argument('--min-freq', type=float, help='Minimum bandpass frequency (Hz). Default 80 Hz')
    hilbert.add_argument('--max-freq', type=float, help='Maximum bandpass frequency (Hz). Default 125 Hz for EEG, 500 Hz for EGF')
    hilbert.add_argument('--required-peaks', type=int, default=6,
                         help='Minimum peak count inside rectified signal (default: 6)')
    hilbert.add_argument('--required-peak-threshold-sd', type=float, default=2.0,
                         help='Peak threshold in SD above mean (default: 2). Use --no-required-peak-threshold to disable')
    hilbert.add_argument('--no-required-peak-threshold', action='store_true',
                         help='Disable the peak-threshold SD check')
    hilbert.add_argument('--boundary-percent', type=float, default=30.0,
                         help='Percent of threshold to find boundaries (default: 30)')
    hilbert.add_argument('--skip-bits2uv', action='store_true',
                         help='Skip bits-to-uV conversion if the .set file is missing')
    hilbert.add_argument('-v', '--verbose', action='store_true', help='Verbose progress logging')

    return parser


def run_hilbert_batch(args: argparse.Namespace):
    input_path = Path(args.file).expanduser()
    
    # Check if input is a directory
    if input_path.is_dir():
        print('Scanning directory: {}'.format(input_path))
        data_files = _find_data_files(input_path)
        
        if not data_files:
            print('No .eeg or .egf files found in directory')
            return
        
        print('Found {} data file(s)'.format(len(data_files)))
        
        # Track summary statistics
        successful = 0
        failed = 0
        total_events = 0
        file_results = []
        
        # Process each data file
        for data_path in data_files:
            set_path = _find_set_file(data_path)
            if not set_path and not args.skip_bits2uv:
                if args.verbose:
                    print('  Skipping {} (no .set file found, use --skip-bits2uv to process anyway)'.format(data_path))
                continue
            
            try:
                event_count = _process_single_file(data_path, set_path, args)
                successful += 1
                total_events += event_count
                file_results.append((data_path.name, event_count))
            except Exception as e:
                print('  Error processing {}: {}'.format(data_path, e))
                failed += 1
                if args.verbose:
                    import traceback
                    traceback.print_exc()
                continue
        
        # Print summary
        print('\n' + '='*60)
        print('BATCH PROCESSING SUMMARY')
        print('='*60)
        print('Total files found:     {}'.format(len(data_files)))
        print('Successfully processed: {}'.format(successful))
        print('Failed:                 {}'.format(failed))
        print('Total HFOs detected:    {}'.format(total_events))
        if successful > 0:
            print('Average per file:       {:.1f}'.format(total_events / float(successful)))
        print('='*60)
        
        if args.verbose and file_results:
            print('\nPer-file event counts:')
            for fname, count in file_results:
                print('  {}: {} events'.format(fname, count))
    
    else:
        # Single file mode
        if not input_path.exists():
            raise FileNotFoundError('Data file not found: {}'.format(input_path))
        
        set_input = Path(args.set_file).expanduser() if args.set_file else None
        
        # If set_file is a directory, try to find the matching set file
        if set_input and set_input.is_dir():
            set_path = _find_set_file(input_path)
        else:
            set_path = set_input if set_input else input_path.with_suffix('.set')
        
        if set_path and not set_path.exists() and not args.skip_bits2uv:
            raise FileNotFoundError('Set file not found: {} (pass --skip-bits2uv to continue without scaling)'.format(set_path))
        
        _process_single_file(input_path, set_path, args)


__all__ = ['build_parser', 'run_hilbert_batch']
