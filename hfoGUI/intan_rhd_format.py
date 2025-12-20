import os
import sys
import glob
import re
import numpy as np
from core.load_intan_rhd_format.load_intan_rhd_format import read_rhd_data
from core.Intan_to_Tint import (
    intan_ephys_to_lfp_dict, intan_to_lfp_header_dict,
    write_faux_set_file, write_eeg_or_egf_file,
    down_sample_timeseries, fir_hann
)
from core.filtering import notch_filt, iirfilt


def find_related_rhd_files(rhd_file: str) -> list:
    """Find all RHD files belonging to the same recording session in the folder.

    Strategy:
    - Detect session prefix ending with date and time: ..._YYMMDD_HHMMSS
    - Group all files that match the same prefix including date, regardless of time.
      Example: ..._220516_093123.rhd, ..._220516_095124.rhd, ..._220516_101124.rhd
    - Also support explicit chunk suffixes (e.g., _001) if present.
    """
    directory = os.path.dirname(rhd_file)
    basename_no_ext = os.path.splitext(os.path.basename(rhd_file))[0]

    # Try to parse "prefix_date_time" components
    m = re.match(r"(.+?)_(\d{6})_(\d{6})(?:[-_]\d{1,3})?$", basename_no_ext)

    if m:
        prefix = m.group(1)
        date = m.group(2)
        time = m.group(3)
        session_core_date = f"{prefix}_{date}"
        print(f"Detected session core (date-level): '{session_core_date}' (file time {time})")
    else:
        # Fallback to chunk-only detection
        m2 = re.match(r"(.+)[-_](\d{1,3})$", basename_no_ext)
        if m2:
            session_core_date = m2.group(1)
            print(f"Detected chunked recording. Base: '{session_core_date}', Chunk: '{m2.group(2)}'")
        else:
            print("Single file recording (no session core detected)")
            return [rhd_file]

    # Find all .rhd/.RHD files in the directory
    all_rhd = glob.glob(os.path.join(directory, '*.[rR][hH][dD]'))
    print(f"Discovered {len(all_rhd)} RHD files in folder:")
    for f in sorted(all_rhd):
        print(f"  - {os.path.basename(f)}")

    # Match files that have the same prefix+date and any HHMMSS time
    related_files = []
    pattern = re.compile(rf"^{re.escape(session_core_date)}_\d{{6}}(?:[-_]\d{{1,3}})?$")
    for f in all_rhd:
        name_no_ext = os.path.splitext(os.path.basename(f))[0]
        if pattern.match(name_no_ext):
            related_files.append(f)

    related_files.sort()

    if not related_files:
        return [rhd_file]

    print(f"Found {len(related_files)} files for session date core:")
    for f in related_files:
        print(f"  + {os.path.basename(f)}")
    return related_files


def read_and_concatenate_rhd_files(file_list: list) -> dict:
    """Read multiple RHD files and concatenate their data."""
    if len(file_list) == 1:
        print(f"Reading single RHD file...")
        try:
            return read_rhd_data(file_list[0])
        except Exception as e:
            print(f"Error reading file: {e}")
            print("This file may be corrupted or incomplete.")
            raise
    
    print(f"Found {len(file_list)} related RHD files. Reading and concatenating...")
    
    # Read first file to get structure
    try:
        first_data = read_rhd_data(file_list[0])
        print(f"  File 1/{len(file_list)}: {os.path.basename(file_list[0])} - OK")
    except Exception as e:
        print(f"  File 1/{len(file_list)}: {os.path.basename(file_list[0])} - ERROR: {e}")
        raise
    
    # For remaining files, concatenate data arrays
    for idx, rhd_file in enumerate(file_list[1:], start=2):
        try:
            print(f"  File {idx}/{len(file_list)}: {os.path.basename(rhd_file)} - Reading...")
            current_data = read_rhd_data(rhd_file)
            
            # Concatenate amplifier data
            first_data['amplifier_data'] = np.concatenate(
                [first_data['amplifier_data'], current_data['amplifier_data']], axis=1
            )
            
            # Update time arrays
            time_offset = first_data['t_amplifier'][-1] + (1.0 / first_data['frequency_parameters']['amplifier_sample_rate'])
            first_data['t_amplifier'] = np.concatenate([
                first_data['t_amplifier'],
                current_data['t_amplifier'] + time_offset
            ])
            
            # Concatenate other data arrays if they exist
            for key in ['aux_input_data', 'supply_voltage_data', 'board_adc_data', 
                        'board_dig_in_data', 'board_dig_out_data', 'temp_sensor_data']:
                if key in first_data and key in current_data:
                    first_data[key] = np.concatenate([first_data[key], current_data[key]], axis=1)
            
            print(f"  File {idx}/{len(file_list)}: {os.path.basename(rhd_file)} - OK")
        except Exception as e:
            print(f"  File {idx}/{len(file_list)}: {os.path.basename(rhd_file)} - ERROR: {e}")
            print(f"  Skipping this file and continuing with already concatenated data...")
            continue
    
    print(f"Concatenation complete. Total duration: {first_data['t_amplifier'][-1]:.2f} seconds")
    return first_data


def select_rhd_file(default_path: str) -> str:
    """Prompt user to choose an RHD file; return None if cancelled."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return default_path

    root = tk.Tk()
    root.withdraw()
    root.update()

    file_path = filedialog.askopenfilename(
        title='Select Intan RHD file',
        filetypes=[('Intan RHD', '*.rhd'), ('All files', '*.*')],
        initialdir=os.path.dirname(default_path)
    )
    root.destroy()

    if file_path:
        return file_path
    return None


def main():
    # Directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Default to bundled sample data
    default_rhd = os.path.join(script_dir, 'core', 'load_intan_rhd_format', 'sampledata.rhd')

    # If a path was provided as an argument, use it; otherwise prompt user
    rhd_file = sys.argv[1] if len(sys.argv) > 1 else select_rhd_file(default_rhd)

    # User cancelled the dialog: exit gracefully with no conversion
    if not rhd_file:
        print("Conversion cancelled: no RHD file selected.")
        return

    if not os.path.isfile(rhd_file):
        print(f"Error: RHD file not found: {rhd_file}")
        sys.exit(1)

    print(f"Using RHD file: {rhd_file}")

    # Find and read all related RHD files (handles chunked recordings)
    related_files = find_related_rhd_files(rhd_file)
    intan_data = read_and_concatenate_rhd_files(related_files)

    # Use session core for folder/name when available
    session_name_base = os.path.splitext(os.path.basename(rhd_file))[0]
    m = re.match(r"(.+?_\d{6}_\d{6})(?:[-_]\d{1,3})?$", session_name_base)
    session_name = m.group(1) if m else session_name_base

    # Get sampling rate to determine if we can create EGF or only EEG
    intan_sample_rate = intan_data['frequency_parameters']['amplifier_sample_rate']
    print(f"Intan sampling rate: {intan_sample_rate} Hz")

    # Determine file type based on sampling rate
    create_egf = intan_sample_rate >= 4800
    file_type = "EGF" if create_egf else "EEG"
    print(f"Creating {file_type} files (sampling rate {'sufficient' if create_egf else 'insufficient'} for EGF)")

    # Create output directory with session name next to the chosen RHD file
    parent_dir = os.path.dirname(rhd_file)
    output_dir = os.path.join(parent_dir, session_name)
    os.makedirs(output_dir, exist_ok=True)

    # Select only one channel: A-000
    target_channel_name = 'A-000'
    target_idx = None
    for i, ch in enumerate(intan_data.get('amplifier_channels', [])):
        names = [ch.get('native_channel_name', ''), ch.get('custom_channel_name', '')]
        if any(n == target_channel_name for n in names):
            target_idx = i
            break

    if target_idx is None:
        # Fallback: try startswith match
        for i, ch in enumerate(intan_data.get('amplifier_channels', [])):
            names = [ch.get('native_channel_name', ''), ch.get('custom_channel_name', '')]
            if any(n.startswith(target_channel_name) for n in names):
                target_idx = i
                target_channel_name = names[0] or names[1]
                break

    if target_idx is None:
        print("Error: Could not find channel 'A-000' in amplifier_channels.")
        sys.exit(1)

    print(f"Converting single channel: {target_channel_name} (index {target_idx})")

    # Downsample time for duration
    amplifier_sample_rate = float(intan_data['frequency_parameters']['amplifier_sample_rate'])
    target_rate = 4.8e3 if create_egf else 250.0
    time_down = down_sample_timeseries(intan_data['t_amplifier'].flatten(), amplifier_sample_rate, target_rate)
    duration = float(time_down[-1] - time_down[0]) if len(time_down) > 1 else 0.0

    # Create header limited to single channel
    header = intan_to_lfp_header_dict(intan_data, egf=create_egf)
    header['channels'] = [target_channel_name]
    write_faux_set_file(header, session_name, output_dir, duration)

    # Extract, filter, and convert only the target channel
    chan_data = intan_data['amplifier_data'][target_idx]
    irfiltered_data = iirfilt(
        bandtype='low', data=chan_data, Fs=intan_sample_rate,
        Wp=500, order=6, automatic=0, Rp=0.1, As=60, filttype='cheby1', showresponse=0
    )
    filtered_data = notch_filt(
        irfiltered_data, Fs=intan_sample_rate, freq=60, band=10, order=2, showresponse=0
    )

    if create_egf:
        # Create EGF file (4.8 kHz)
        egf_ephys_data = down_sample_timeseries(filtered_data, intan_sample_rate, 4.8e3)
        egf_ephys_data = egf_ephys_data.astype('int16')
        write_eeg_or_egf_file(egf_ephys_data, duration, header, target_channel_name, session_name, output_dir, is_egf=True)
    else:
        # Create EEG file (250 Hz)
        eeg_ephys_data = down_sample_timeseries(filtered_data, intan_sample_rate, 250)
        eeg_ephys_data = eeg_ephys_data.astype('int8')
        write_eeg_or_egf_file(eeg_ephys_data, duration, header, target_channel_name, session_name, output_dir, is_egf=False)

    print(f"\nConversion complete!")
    print(f"Session name: {session_name}")
    print(f"Files saved to: {output_dir}")
    print(f"Files created: {session_name}.set, {session_name}.{file_type.lower()}1, {session_name}.{file_type.lower()}2, etc.")


if __name__ == "__main__":
    main()