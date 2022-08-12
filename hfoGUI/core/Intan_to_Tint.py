from .load_intan_rhd_format.load_intan_rhd_format import read_rhd_data

import numpy as np


def write_axona_lfp(filepath, lfp_ephys_data, lfp_header):
    session_path, session_filename = os.path.split(filepath)
    num_samples = int(len(lfp_ephys_data))
    trial_date, trial_time = session_datetime(session_filename)
    if '.egf' in session_filename:
        egf = True
    else:
        egf = False

    with open(filepath, 'w') as f:
        date = 'trial_date %s' % (trial_date)
        time_head = '\ntrial_time %s' % (trial_time)
        experimenter = '\nexperimenter %s' % (lfp_header['experimenter'])
        comments = '\ncomments %s' % (lfp_header['comments'])
        duration = '\nduration %d' % (lfp_header['duration'])
        sw_version = '\nsw_version %s' % (lfp_header['version'])
        num_chans = '\nnum_chans 1'

        if egf:
            sample_rate = '\nsample_rate %d Hz' % (lfp_header['Fs_EGF'])
            data = struct.pack('<%dh' % (num_samples), *[int(sample) for sample in lfp_ephys_data.tolist()])
            b_p_sample = '\nbytes_per_sample 2'
            num_EEG_samples = '\nnum_EGF_samples %d' % (num_samples)

        else:
            sample_rate = '\nsample_rate %d.0 hz' % (lfp_header['Fs_EEG'])
            data = struct.pack('>%db' % (num_samples), *[int(sample) for sample in lfp_ephys_data.tolist()])
            b_p_sample = '\nbytes_per_sample 1'
            num_EEG_samples = '\nnum_EEG_samples %d' % (num_samples)

        eeg_p_position = '\nEEG_samples_per_position %d' % (5)

        start = '\ndata_start'

        if egf:
            write_order = [date, time_head, experimenter, comments, duration, sw_version, num_chans,
                           sample_rate, b_p_sample, num_EEG_samples, start]
        else:
            write_order = [date, time_head, experimenter, comments, duration, sw_version, num_chans,
                           sample_rate, eeg_p_position, b_p_sample, num_EEG_samples, start]

        f.writelines(write_order)

    with open(filepath, 'rb+') as f:
        f.seek(0, 2)
        f.writelines([data, bytes('\r\ndata_end\r\n', 'utf-8')])


def intan_to_lfp_dicts(intan_data: dict) -> dict:
    """
    Collects all the data needed for an egf file
    from the intan data and returns a dictionary
    ready for writing to an egf file for every channel.

    IMPORTANT NOTE: This function only collects
    electrophysiology data from the
    'amplifier_data' key. It does not collect
    signals from auxiliary inputs.
    """

    lfp_ephys_data = intan_ephys_to_lfp_dict(intan_data)

    lfp_header = intan_to_lfp_header_dict(intan_data)

    return lfp_ephys_data, lfp_header


def intan_ephys_to_lfp_dict(intan_data: dict, egf=True) -> dict:

    amplifier_sample_rate = float(intan_data['frequency_parameters']['amplifier_sample_rate'])

    if egf:
        sample_rate = 4.8e3
    else:
        sample_rate = 250.0

    try:
        assert len(intan_data['amplifier_data']) == len(intan_data['amplifier_channels'])
    except AssertionError:
        raise ValueError('The number of amplifier channels does not match the number of custom channel names. This file may be corrupted.')

    lfp_ephys_data = dict()
    lfp_ephys_data['time'] = down_sample_timeseries(intan_data['t_amplifier'].flatten(), amplifier_sample_rate, sample_rate)
    for i in range(len(intan_data['amplifier_data'])):
        if intan_data['amplifier_data'][i].size > 1:
            lfp_ephys_data[intan_data["amplifier_channels"][i]["custom_channel_name"]] = down_sample_timeseries(intan_data['amplifier_data'][i], amplifier_sample_rate, sample_rate)

    return lfp_ephys_data



def down_sample_timeseries(data: np.ndarray, sample_rate: float, new_sample_rate: float):
    """
    Downsample a timeseries.
    """
    try:
        assert type(data) == np.ndarray
    except:
        raise TypeError('data must be a numpy array')
    try:
        assert data.ndim == 1
    except:
        raise ValueError('data must be a 1D array')
    try:
        assert type(float(sample_rate)) == float
    except:
        raise TypeError('sample_rate must be a number')
    try:
        assert type(float(new_sample_rate)) == float
    except:
        raise TypeError('new_sample_rate must be a float')
    try:
        assert sample_rate > new_sample_rate
    except:
        raise ValueError('sample_rate must be greater than new_sample_rate')

    #Generate a
    skip_size = sample_rate / new_sample_rate

    #is this necessary?
    data = data.flatten()

    #Generate a list of floating points where the new
    # data would ideally be sampled from.
    subsample = np.arange(0, data.size, skip_size)
    #Find the nearest index value to the subsample.
    new_index = [int(round(i)) for i in subsample]

    if len(data) == new_index[-1]:
        new_index.pop()

    #Downsample the data.
    downsampled_data = data[new_index]

    return downsampled_data



def intan_to_lfp_header_dict(intan_data: dict, egf=True) -> dict:
    """
    """
    lfp_header = dict()
    lfp_header['date'] = 'UNKNOWN'
    lfp_header['time'] = 'UNKNOWN'
    lfp_header['experimenter'] = 'UNKNOWN'
    lfp_header['comments'] = 'UNKNOWN'
    lfp_header['duration'] = 'UNKNOWN'
    lfp_header['version'] = 'UNKNOWN'
    if egf:
        lfp_header['sample_rate'] = 4.8e3
    else: #(if eeg)
        lfp_header['sample_rate'] = 250 #TODO: Check this
    return lfp_header