# hfoGUI

hfoGUI was initially a Python package designed to visualize High Frequency Oscillations (HFO's), but has grown to be an all encompassing tool to visualize LFP data recorded in the Tint format (from Axona's dacqUSB).

# Python Dependencies:
- PyQt5
- Pillow
- numpy
- PyQtGraph
- scipy
- matplotlib 
- pandas
- pyfftw

# Requirements
Since it utilizes PyQt5 as the GUI framework it should be available to a wide variety of Python versions and Operating Systems. However it was only tested on Python 3.7 with Windows 10. I do recommend using the latest version of Python as it makes it easy to download some of these C++ based dependencies. 

# Project Documentation
- [Installation](https://geba.technology/project/hfogui)
- [User Guide](https://geba.technology/project/hfogui-hfogui-user-guide)
- Windows No-Install file (OLD version). (1) [Download](https://drive.google.com/file/d/1Yz5z3Fn5AA3JPS4_hlFLPap3Omue6Pw7/view?usp=sharing) pre-built hfoGUI zip file, (2) unzip contents to folder and (3) run hfoGUI.exe. Use below method for latest version.

# Usage

## GUI Mode (Default)
Launch the graphical interface:
```bash
python -m hfoGUI
```

### Intan RHD → Tint Conversion (GUI)

Convert Intan `.rhd` recordings into Tint `.set` + `.egf`/`.eeg` files directly from the GUI:

- Click "Intan Convert" next to "Import Set" on the main window
- Choose an `.rhd` file; canceling simply exits without conversion
- The converter auto-detects related chunked files in the same folder and concatenates them
- Output is saved next to the chosen file in a subfolder named after the session (e.g., `prefix_YYMMDD_HHMMSS/`)
- Creates `.egf` when sample rate ≥ 4.8 kHz, otherwise `.eeg`
- Converts a single amplifier channel (default: `A-000`) for quick testing

Example output:
```
Session name: sample_session
Files saved to: E:\DATA\sample_session
Files created: sample_session.set, sample_session.egf1, sample_session.egf2, ...
```

## CLI Mode - Automated Batch Processing

### Hilbert Detection Batch Command

Process HFO detection automatically using the Hilbert envelope method without launching the GUI. Supports both single-file and directory batch processing.

#### Basic Syntax
```bash
python -m hfoGUI hilbert-batch --file <path> [options]
```

#### Single File Processing
```bash
python -m hfoGUI hilbert-batch \
  --file /path/to/data.egf \
  --set-file /path/to/data.set \
  --epoch-sec 300 \
  --threshold-sd 4 \
  --min-duration-ms 12 \
  --min-freq 250 \
  --max-freq 600 \
  --required-peaks 6 \
  --required-peak-threshold-sd 3 \
  --boundary-percent 30
```

#### Directory Batch Processing
Recursively process all `.egf` and `.eeg` files in a directory (prioritizes `.egf` when both exist):
```bash
python -m hfoGUI hilbert-batch \
  --file /path/to/data/directory/ \
  --epoch-sec 180 \
  --threshold-sd 4 \
  --min-duration-ms 10 \
  --min-freq 80 \
  --max-freq 500 \
  --required-peaks 6 \
  --required-peak-threshold-sd 2 \
  --boundary-percent 25 \
  --verbose
```

#### Command-Line Options

**Required:**
- `--file PATH`: Path to `.eeg`/`.egf` file or directory to process recursively

**Optional Detection Parameters:**
- `--set-file PATH`: Path to `.set` calibration file (auto-detected if not specified)
- `--epoch-sec SECONDS`: Epoch window size in seconds (default: 300)
- `--threshold-sd SD`: Detection threshold in standard deviations (default: 3.0)
- `--min-duration-ms MS`: Minimum event duration in milliseconds (default: 10.0)
- `--min-freq HZ`: Minimum frequency for bandpass filter in Hz (default: 80 for EEG, 80 for EGF)
- `--max-freq HZ`: Maximum frequency for bandpass filter in Hz (default: 125 for EEG, 500 for EGF)
- `--required-peaks N`: Minimum number of peaks required in event (default: 6)
- `--required-peak-threshold-sd SD`: Peak detection threshold in SD (default: 2.0)
- `--no-required-peak-threshold`: Disable peak threshold (count all peaks)
- `--boundary-percent PERCENT`: Boundary detection threshold as % of main threshold (default: 30%)
- `--skip-bits2uv`: Skip bits-to-microvolts conversion if `.set` file missing
- `--output PATH`: Custom output directory (default: `HFOScores/<session>/`)
- `--verbose`, `-v`: Enable detailed progress logging

#### Output Files

For each processed session, the following files are created:
- `<session>_HIL.txt`: Tab-separated file with detected HFO events (ID, start time, stop time, settings)
- `<session>_settings.json`: JSON file with all detection parameters used

Default output location: `HFOScores/<session>/`

#### Examples

**Example 1: Process single file with custom parameters**
```bash
python -m hfoGUI hilbert-batch \
  --file E:\DATA\recording.egf \
  --epoch-sec 120 \
  --threshold-sd 5 \
  --min-freq 200 \
  --max-freq 600 \
  --verbose
```

**Example 2: Batch process directory (recursive)**
```bash
python -m hfoGUI hilbert-batch \
  --file E:\DATA\Experiments\ \
  --epoch-sec 300 \
  --threshold-sd 4 \
  --min-duration-ms 12 \
  --required-peaks 8 \
  --verbose
```
This will:
1. Scan all subdirectories for `.egf` and `.eeg` files
2. Auto-detect matching `.set` files
3. Process each file independently
4. Print a summary report showing total files, success/failure counts, and HFO statistics

**Example 3: Process without calibration file**
```bash
python -m hfoGUI hilbert-batch \
  --file recording.egf \
  --skip-bits2uv \
  --epoch-sec 180
```

#### Batch Processing Summary

When processing directories, a summary report is displayed:
```
============================================================
BATCH PROCESSING SUMMARY
============================================================
Total files found:     15
Successfully processed: 14
Failed:                 1
Total HFOs detected:    1247
Average per file:       89.1
============================================================
```

#### Notes
- Directory mode automatically matches `.set` files by basename
- When both `.eeg` and `.egf` exist with same basename, only `.egf` is processed
- Large epoch windows (e.g., 300s) work correctly with empty epochs
- Failed files don't stop batch processing (errors logged, processing continues)
- Use `--verbose` for per-epoch progress and detailed error traces

## Intan Conversion (CLI)

Run the converter without the GUI. If no file argument is provided, a file picker opens; canceling exits.

```bash
# As a module
python -m hfoGUI.intan_rhd_format

# Or direct script path
python hfoGUI/intan_rhd_format.py E:\DATA\recording_250k_240101_120000.rhd
```

Outputs are created in a session-named subfolder next to the input `.rhd`. The converter selects channel `A-000` by default and produces `.egf` or `.eeg` depending on input sample rate. A bundled sample file is available at `hfoGUI/core/load_intan_rhd_format/sampledata.rhd` for quick testing.

# Authors
* **Geoff Barrett** - [Geoff’s GitHub](https://github.com/GeoffBarrett)
* **HussainiLab** - [hfoGUI Repository](https://github.com/HussainiLab/hfoGUI)

**Updated (v3.0):** Added Intan RHD → Tint converter (GUI + CLI) and global UI theme options; batch Hilbert detection retained and improved.

# License

This project is licensed under the GNU  General  Public  License - see the [LICENSE.md](../master/LICENSE) file for details
