from .load_intan_rhd_format.load_intan_rhd_format import read_rhd_data

import os
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal
import struct
import datetime
import json

import numpy as np

def create_eeg_and_egf_files(intan_data: dict, session_name: str, output_dir: str):
    """
    """
    intan_sample_rate = intan_data['frequency_parameters']['amplifier_sample_rate']
    lfp_ephys_data = intan_ephys_to_lfp_dict(intan_data)
    time = lfp_ephys_data['time']
    egf_time = down_sample_timeseries(time, intan_sample_rate, 4.8e3)
    eeg_time = down_sample_timeseries(time, 4.8e3, 250.0)

    for channel in lfp_ephys_data:
        if channel == 'time':
            continue
        else:
            irfiltered_data = iirfilt(bandtype='low', data=lfp_ephys_data[channel], Fs=intan_sample_rate, Wp=500, order=6,automatic=0, Rp=0.1, As=60, filttype='cheby1', showresponse=0)

            filtered_data = notch_filt(irfiltered_data, Fs=intan_sample_rate, freq=60, band=10,order=2, showresponse=0)


            # EGF
            egf_ephys_data = down_sample_timeseries(filtered_data, intan_sample_rate, 4.8e3)

            # converting the data from uV to int16
            #egf_ephys_data = (egf_ephys_data / scalar16)

            # ensuring the appropriate range of the values
            #egf_ephys_data[np.where(egf_ephys_data > 32767)] = 32767
            #egf_ephys_data[np.where(egf_ephys_data < -32768)] = -32768

            egf_ephys_data = egf_ephys_data.astype(np.int16)

            efg_header = intan_to_lfp_header_dict(intan_data, True)

            try:
                assert len(egf_ephys_data) == len(egf_time)
            except:
                raise AssertionError("len(egf_ephys_data) ({}) == len(egf_time) ({}). Values must be equal for write_egf_file.".format(len(egf_ephys_data), len(egf_time)))

            write_egf_file(egf_ephys_data, egf_time, efg_header, channel, session_name, output_dir)


            # EEG
            eeg_ephys_data, N = fir_hann(egf_ephys_data, 4.8e3, 125, n_taps=101, showresponse=0)

            # converting data from int16 to int8
            #value = np.divide(eeg_ephys_data, 256).astype(int)
            #eeg_ephys_data[np.where(eeg_ephys_data > 127)] = 127
            #eeg_ephys_data[np.where(eeg_ephys_data < -128)] = -128

            # downsample the data
            eeg_ephys_data = down_sample_timeseries(filtered_data, 4.8e3, 250)

            eeg_ephys_data = eeg_ephys_data.astype(np.int8)

            eeg_header = intan_to_lfp_header_dict(intan_data, False)

            try:
                assert len(eeg_ephys_data) == len(eeg_time)
                continue
            except:
                raise AssertionError("len(eeg_ephys_data) ({}) == len(eeg_time) ({}). These values must be equal for write_eeg_file function.".format(len(eeg_ephys_data), len(eeg_time)))

            write_eeg_file(eeg_ephys_data, eeg_time, eeg_header, channel, session_name, output_dir)



def write_eeg_file(eeg_single_unit_data, eeg_time,eeg_header_dict, channel_name, session_name, output_dir):

    eeg_filepath = os.path.join(output_dir, session_name + '_' + channel_name + '.eeg')

    duration = None #TODO get duration from header

    pass

def write_eeg(filepath, data, Fs, set_filename=None):
    data = data.flatten()

    session_path, session_filename = os.path.split(filepath)

    tint_basename = os.path.splitext(session_filename)[0]

    if set_filename is None:
        set_filename = os.path.join(session_path, '%s.set' % tint_basename)

    header = get_set_header(set_filename)

    num_samples = int(len(data))

    if '.egf' in session_filename:
        egf = True

    else:
        egf = False

    # if the duration before the set file was overwritten wasn't a round number, it rounded up and thus we need
    # to append values to the EEG (we will add 0's to the end)
    duration = int(get_setfile_parameter('duration', set_filename))  # get the duration from the set file

    EEG_expected_num = int(Fs * duration)

    if num_samples < EEG_expected_num:
        missing_samples = EEG_expected_num - num_samples
        data = np.hstack((data, np.zeros((1, missing_samples)).flatten()))
        num_samples = EEG_expected_num

    with open(filepath, 'w') as f:

        num_chans = 'num_chans 1'

        if egf:
            sample_rate = '\nsample_rate %d Hz' % (int(Fs))
            data = struct.pack('<%dh' % (num_samples), *[np.int(data_value) for data_value in data.tolist()])
            b_p_sample = '\nbytes_per_sample 2'
            num_EEG_samples = '\nnum_EGF_samples %d' % (num_samples)

        else:
            sample_rate = '\nsample_rate %d.0 hz' % (int(Fs))
            data = struct.pack('>%db' % (num_samples), *[np.int(data_value) for data_value in data.tolist()])
            b_p_sample = '\nbytes_per_sample 1'
            num_EEG_samples = '\nnum_EEG_samples %d' % (num_samples)

        eeg_p_position = '\nEEG_samples_per_position %d' % (5)

        start = '\ndata_start'

        if egf:
            write_order = [header, num_chans, sample_rate,
                           b_p_sample, num_EEG_samples, start]
        else:
            write_order = [header, num_chans, sample_rate, eeg_p_position,
                           b_p_sample, num_EEG_samples, start]

        f.writelines(write_order)

    with open(filepath, 'rb+') as f:
        f.seek(0, 2)
        f.writelines([data, bytes('\r\ndata_end\r\n', 'utf-8')])

def write_egf_file(egf_single_unit_data, efg_time, egf_header_dict, channel_name, session_name, output_dir):

    eeg_filepath = os.path.join(output_dir, session_name + '_' + channel_name + '.egf')

    pass


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

    # clip the data to the lower bound of
    # the expected size
    end = int(round(len(data) / (sample_rate / new_sample_rate) - 1))

    if len(downsampled_data) >= end:
        downsampled_data = downsampled_data[:end]
    else:
        raise ValueError('The data is not long enough to downsample.')


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





def create_eeg(filename, data, Fs, set_filename, scalar16, DC_Blocker=True, notch_freq=60, self=None):
    # data is given in int16

    if os.path.exists(filename):
        msg = '[%s %s]: The following EEG filename already exists: %s!' % \
              (str(datetime.datetime.now().date()),
               str(datetime.datetime.now().time())[:8], filename)

        if self is not None:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)
        return

    Fs_EGF = 4.8e3
    Fs_EEG = 250

    '''
    if DC_Blocker:
        data = filt.dcblock(data, 0.1, Fs_tint)
    '''

    msg = '[%s %s]: Filtering to create the EEG data!' % \
        (str(datetime.datetime.now().date()),
         str(datetime.datetime.now().time())[:8])

    if self is not None:
        self.LogAppend.myGUI_signal_str.emit(msg)
    else:
        print(msg)

    # LP at 500
    data = iirfilt(bandtype='low', data=data, Fs=Fs, Wp=500, order=6,automatic=0, Rp=0.1, As=60, filttype='cheby1', showresponse=0)

    # notch filter the data
    if notch_freq != 0:

        msg = '[%s %s]: Notch Filtering the EEG data!' % \
              (str(datetime.datetime.now().date()),
               str(datetime.datetime.now().time())[:8])

        if self is not None:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)

        data = filt.notch_filt(data, Fs, freq=notch_freq, band=10,order=2, showresponse=0)
    else:

        msg = '[%s %s]: Notch Filtering the EEG data at a default of 60 Hz!' % \
              (str(datetime.datetime.now().date()),
               str(datetime.datetime.now().time())[:8])

        if self is not None:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)

        data = filt.notch_filt(data, Fs, freq=60, band=10,
                               order=2, showresponse=0)

    # downsample to 4.8khz signal for EGF signal (EEG is derived from EGF data)

    data = data[:, 0::int(Fs / Fs_EGF)]

    # append zeros to make the duration a round number
    # duration_round = np.ceil(data.shape[1] / Fs_EGF)  # the duration should be rounded up to the nearest integer
    duration_round = int(get_setfile_parameter('duration', set_filename))  # get the duration from the set file
    missing_samples = int(duration_round * Fs_EGF - data.shape[1])

    if missing_samples != 0:
        missing_samples = np.tile(np.array([0]), (1, missing_samples))
        data = np.hstack((data, missing_samples))

    # ------------------------------------- clipping data ---------------------------------------------
    # converting the data from uV to int16
    data = (data / scalar16)

    # ensuring the appropriate range of the values
    data[np.where(data > 32767)] = 32767
    data[np.where(data < -32768)] = -32768

    data = data.astype(np.int16)

    # -----------------------------------------------------------------------------------------------

    msg = '[%s %s]: Downsampling the EEG data to 250 Hz!' % \
        (str(datetime.datetime.now().date()),
         str(datetime.datetime.now().time())[:8])

    if self is not None:
        self.LogAppend.myGUI_signal_str.emit(msg)
    else:
        print(msg)

    # now apply lowpass at 125 hz to prevent aliasing of EEG
    # this uses a 101 tap von hann filter @ 125 Hz
    data, N = fir_hann(data, Fs_EGF, 125, n_taps=101, showresponse=0)

    # --------------------------------------------------------------------------------------------------------------

    data = int16toint8(data)

    data = EEG_downsample(data)

    ##################################################################################################
    # ---------------------------Writing the EEG Data-------------------------------------------
    ##################################################################################################

    write_eeg(filename, data, Fs_EEG, set_filename=set_filename)





def fir_hann(data, Fs, cutoff, n_taps=101, showresponse=0):

    # The Nyquist rate of the signal.
    nyq_rate = Fs / 2

    b = scipy.signal.firwin(n_taps, cutoff / nyq_rate, window='hann')

    a = 1.0
    # Use lfilter to filter x with the FIR filter.
    data = scipy.signal.lfilter(b, a, data)
    # data = scipy.signal.filtfilt(b, a, data)

    if showresponse == 1:
        w, h = scipy.signal.freqz(b, a, worN=8000)  # returns the requency response h, and the angular frequencies
        # w in radians/sec
        # w (radians/sec) * (1 cycle/2pi*radians) = Hz
        # f = w / (2 * np.pi)  # Hz

        plt.figure(figsize=(20, 15))
        plt.subplot(211)
        plt.semilogx((w / np.pi) * nyq_rate, np.abs(h), 'b')
        plt.xscale('log')
        plt.title('%s Filter Frequency Response')
        plt.xlabel('Frequency(Hz)')
        plt.ylabel('Gain [V/V]')
        plt.margins(0, 0.1)
        plt.grid(which='both', axis='both')
        plt.axvline(cutoff, color='green')

    return data, n_taps


def get_set_header(set_filename):
    with open(set_filename, 'r+') as f:
        header = ''
        for line in f:
            header += line
            if 'sw_version' in line:
                break
    return header


def create_egf(filename, data, Fs, set_filename, scalar16, DC_Blocker=True, notch_freq=60, self=None):

    if os.path.exists(filename):
        msg = '[%s %s]: The following EGF filename already exists: %s!' % \
              (str(datetime.datetime.now().date()),
               str(datetime.datetime.now().time())[:8], filename)

        if self is not None:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)
        return

    Fs_EGF = 4.8e3

    '''
    if DC_Blocker:
        data = filt.dcblock(data, 0.1, Fs_tint)
    '''

    msg = '[%s %s]: Filtering to create the EGF data!' % \
        (str(datetime.datetime.now().date()),
         str(datetime.datetime.now().time())[:8])

    if self is not None:
        self.LogAppend.myGUI_signal_str.emit(msg)
    else:
        print(msg)

    # LP at 500
    data = iirfilt(bandtype='low', data=data, Fs=Fs, Wp=500, order=6,
                        automatic=0, Rp=0.1, As=60, filttype='cheby1', showresponse=0)

    # notch filter the data
    if notch_freq != 0:

        msg = '[%s %s]: Notch Filtering the EGF data!' % \
            (str(datetime.datetime.now().date()),
             str(datetime.datetime.now().time())[:8])

        if self is not None:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)

        data = filt.notch_filt(data, Fs, freq=60, band=10,order=2, showresponse=0)
    else:

        msg = '[%s %s]: Notch Filtering the EGF data at a default of 60 Hz!' % \
            (str(datetime.datetime.now().date()),
             str(datetime.datetime.now().time())[:8])

        if self is not None:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)

        data = filt.notch_filt(data, Fs, freq=60, band=10,
                               order=2, showresponse=0)

    # downsample to 4.8khz signal for EGF signal (EEG is derived from EGF data)

    data = data[:, 0::int(Fs / Fs_EGF)]

    # the duration should be rounded up to the nearest integer
    duration_round = int(get_setfile_parameter('duration', set_filename))  # get the duration from the set file
    missing_samples = int(duration_round * Fs_EGF - data.shape[1])
    if missing_samples != 0:
        missing_samples = np.tile(np.array([0]), (1, missing_samples))
        data = np.hstack((data, missing_samples))

    # converting the data from uV to int16
    data = (data / scalar16)

    # ensuring the appropriate range of the values
    data[np.where(data > 32767)] = 32767
    data[np.where(data < -32768)] = -32768

    data = data.astype(np.int16)

    # data is already in int16 which is what the final unit should be in

    ##################################################################################################
    # ---------------------------Writing the EGF Data-------------------------------------------
    ##################################################################################################

    write_eeg(filename, data, Fs_EGF, set_filename=set_filename)


def eeg_channels_to_filenames(channels, directory, output_basename):
    eeg_filenames = []
    egf_filenames = []

    for i in np.arange(len(channels)):
        eeg_number = i + 1

        if eeg_number == 1:
            eeg_filename = os.path.join(directory, output_basename + '.eeg')
            egf_filename = os.path.join(directory, output_basename + '.egf')
        else:
            eeg_filename = os.path.join(directory, output_basename + '.eeg%d' % (eeg_number))
            egf_filename = os.path.join(directory, output_basename + '.egf%d' % (eeg_number))

        eeg_filenames.append(eeg_filename)
        egf_filenames.append(egf_filename)

    return eeg_filenames, egf_filenames


def get_eeg_channels(probe_map, directory, output_basename, channels='all'):
    """

    :param method:
    :return:
    """

    tetrode_channels = probe_map.values()

    if type(channels) == str:
        if channels == 'all':
            # All of the channels will be saved as an EEG / EGF file
            channels = np.asarray(list(tetrode_channels)).flatten()
        elif channels == 'first':
            # only convert the first channel in each tetrode
            channels = np.asarray([channel[0] for channel in tetrode_channels])

    eeg_filenames, egf_filenames = eeg_channels_to_filenames(channels, directory, output_basename)

    return eeg_filenames, egf_filenames, channels


def convert_eeg(session_files, tint_basename, output_basename, Fs, convert_channels='first', self=None):
    """
    This method will create all the eeg and egf files
    """
    directory = os.path.dirname(session_files[0])

    raw_fnames = [os.path.join(directory, file) for file in os.listdir(
        directory) if '_raw.mda' in file if os.path.basename(tint_basename) in file]

    probe = get_probe_name(session_files[0])

    probe_map = tetrode_map[probe]

    # get eeg and egf files + channels to convert
    eeg_filenames, egf_filenames, eeg_channels = get_eeg_channels(probe_map, directory, output_basename, channels=convert_channels)

    total_files_n = len(eeg_filenames) + len(egf_filenames)

    cue_fname = os.path.join(directory, tint_basename + '_cues.json')

    if os.path.exists(cue_fname):
        with open(cue_fname) as f:
            cue_data = json.load(f)
    else:
        msg = '[%s %s]: The following cue filename does not exist: %s!#red' % \
              (str(datetime.datetime.now().date()),
               str(datetime.datetime.now().time())[:8], cue_fname)
        if self is not None:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)

        cue_data = {}

    if 'converted_eeg' in cue_data.keys():
        # then the session has been converted already, check to ensure that we maintain the correct naming

        # get the converted eeg channel numbers
        converted_eegs_dict = cue_data['converted_eeg']

        converted_eegs = np.asarray([converted_eegs_dict[key] for key in sorted(
            converted_eegs_dict)])

        # get the converted eeg/egf filenames
        eeg_converted, egf_converted = eeg_channels_to_filenames(converted_eegs, directory, output_basename)
        for i in np.arange(len(eeg_converted)):
            if i < len(eeg_channels):
                if converted_eegs[i] != eeg_channels[i]:
                    # then the eeg_filename corresponds to the wrong channel, delete it
                    os.remove(eeg_converted[i])
                    os.remove(egf_converted[i])
            else:
                # delete these files, they are no longer necessary in the new conversion
                os.remove(eeg_converted[i])
                os.remove(egf_converted[i])

    else:
        # deleting old files before the implementation of converted_eeg was used
        eeg_converted = [os.path.join(directory, file) for file in os.listdir(directory) if
                         output_basename + '.eeg' in file]
        egf_converted = [os.path.join(directory, file) for file in os.listdir(directory) if
                         output_basename + '.egf' in file]

        for file in eeg_converted + egf_converted:
            os.remove(file)

    # check if the files have already been created
    file_exists = 0
    for create_file in (eeg_filenames + egf_filenames):
        if os.path.exists(create_file):
            file_exists += 1

    if file_exists == total_files_n:

        msg = '[%s %s]: All the EEG/EGF files for the following session is converted: %s!' % \
              (str(datetime.datetime.now().date()),
               str(datetime.datetime.now().time())[:8], tint_basename)
        if self is not None:
            self.LogAppend.myGUI_signal_str.emit(msg)
        else:
            print(msg)

        return False

    # set_filename = '%s.set' % (os.path.join(directory, tint_basename))
    set_filename = '%s.set' % output_basename

    for file in raw_fnames:

        mda_basename = os.path.splitext(file)[0]
        mda_basename = mda_basename[:find_sub(mda_basename, '_')[-1]]

        tint_basename = mda_basename[:find_sub(mda_basename, '_')[-1]]

        tetrode = int(mda_basename[find_sub(mda_basename, '_')[-1] + 2:])

        tetrode_channels = probe_map[tetrode]

        channel_bool = np.where(np.in1d(eeg_channels, tetrode_channels))[0]

        if len(channel_bool) > 0:
            # then this tetrode has a channel to be saved
            current_files = [eeg_filenames[x] for x in channel_bool] + \
                            [egf_filenames[x] for x in channel_bool]

            file_written = 0
            for cfile in current_files:
                if os.path.exists(cfile):
                    file_written += 1

            if file_written == len(current_files):
                for cfile in current_files:
                    if '.eeg' in file:
                        msg = '[%s %s]: The following EEG file has already been created, skipping: %s!' % \
                              (str(datetime.datetime.now().date()),
                               str(datetime.datetime.now().time())[:8], cfile)
                    else:
                        msg = '[%s %s]: The following EGF file has already been created, skipping: %s!' % \
                              (str(datetime.datetime.now().date()),
                               str(datetime.datetime.now().time())[:8], cfile)
                    if self is not None:
                        self.LogAppend.myGUI_signal_str.emit(msg)
                    else:
                        print(msg)
                continue

            data, _ = readMDA(file)  # size: len(tetrode_channels) x number of samples, units: bits

            # convert from bits to uV
            data = data * intan_scalar()  # units: uV

            file_header = read_header(session_files[0])  # read the file header information from a session file
            n_channels = file_header['num_amplifier_channels']

            clip_filename = '%s_clips.json' % (os.path.join(directory, tint_basename))

            if os.path.exists(clip_filename):
                with open(clip_filename, 'r') as f:
                    clip_data = json.load(f)

                channel_scalar16s = np.zeros(n_channels)

                for tetrode in probe_map.keys():
                    tetrode_clips = clip_data[str(tetrode)]
                    for channel in probe_map[tetrode]:
                        channel_scalar16s[channel - 1] = tetrode_clips['scalar16bit']
            else:
                raise FileNotFoundError('Clip Filename not found!')

            # for eeg_filename, egf_filename, channel_number in zip(eeg_filenames, egf_filenames, probe_map[tetrode]):
            for i in channel_bool:
                eeg_filename = eeg_filenames[i]
                egf_filename = egf_filenames[i]
                channel_number = eeg_channels[i]
                channel_i = np.where(np.asarray(tetrode_channels) == channel_number)[0][0]

                if os.path.exists(eeg_filename):

                    EEG = np.array([])
                    msg = '[%s %s]: The following EEG file has already been created, skipping: %s!' % \
                          (str(datetime.datetime.now().date()),
                           str(datetime.datetime.now().time())[:8], eeg_filename)
                    if self is not None:
                        self.LogAppend.myGUI_signal_str.emit(msg)
                    else:
                        print(msg)
                else:
                    msg = '[%s %s]: Creating the following EEG file: %s!' % \
                          (str(datetime.datetime.now().date()),
                           str(datetime.datetime.now().time())[:8], eeg_filename)

                    if self is not None:
                        self.LogAppend.myGUI_signal_str.emit(msg)
                    else:
                        print(msg)

                    # load data
                    EEG = data[channel_i, :].reshape((1, -1))

                    create_eeg(eeg_filename, EEG, Fs, set_filename, channel_scalar16s[channel_number - 1],
                               DC_Blocker=False, self=self)

                    # this will overwrite the eeg settings that is in the .set file
                    eeg_ext = os.path.splitext(eeg_filename)[1]
                    if eeg_ext == '.eeg':
                        eeg_number = '1'
                    else:
                        eeg_number = eeg_ext[4:]

                if os.path.exists(egf_filename):

                    msg = '[%s %s]: The following EGF file has already been created, skipping: %s!' % \
                          (str(datetime.datetime.now().date()),
                           str(datetime.datetime.now().time())[:8], egf_filename)
                    if self is not None:
                        self.LogAppend.myGUI_signal_str.emit(msg)
                    else:
                        print(msg)

                else:

                    msg = '[%s %s]: Creating the following EGF file: %s!' % \
                          (str(datetime.datetime.now().date()),
                           str(datetime.datetime.now().time())[:8], egf_filename)

                    if self is not None:
                        self.LogAppend.myGUI_signal_str.emit(msg)
                    else:
                        print(msg)

                    EEG = data[channel_i, :].reshape((1, -1))

                    create_egf(egf_filename, EEG, Fs, set_filename, channel_scalar16s[channel_number - 1],
                               DC_Blocker=False, self=self)

                EEG = None

    eeg_dict = {}
    for k in np.arange(len(eeg_channels)):
        # using the int because json doesn't like np.int32
        eeg_dict[int(k)] = int(eeg_channels[k])

    cue_data['converted_eeg'] = eeg_dict

    with open(cue_fname, 'w') as f:
        json.dump(cue_data, f)

    return True


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




def notch_filt(data, Fs, band=10, freq=60, ripple=1, order=2, filter_type='butter', analog_filt=False,
               showresponse=0):
    '''# Required input defintions are as follows;
    # time:   Time between samples
    # band:   The bandwidth around the centerline freqency that you wish to filter
    # freq:   The centerline frequency to be filtered
    # ripple: The maximum passband ripple that is allowed in db
    # order:  The filter order.  For FIR notch filters this is best set to 2 or 3,
    #         IIR filters are best suited for high values of order.  This algorithm
    #         is hard coded to FIR filters
    # filter_type: 'butter', 'bessel', 'cheby1', 'cheby2', 'ellip'
    # data:         the data to be filtered'''

    cutoff = freq
    nyq = Fs / 2.0
    low = freq - band / 2.0
    high = freq + band / 2.0
    low = low / nyq
    high = high / nyq
    b, a =scipy.signal.iirfilter(order, [low, high], rp=ripple, btype='bandstop', analog=analog_filt, ftype=filter_type)

    filtered_data = np.array([])

    if len(data) != 0:
        if len(data.shape) > 1:  # lfilter is one dimensional so we need to perform for loop on multi-dimensional array
            # filtered_data = np.zeros((data.shape[0], data.shape[1]))
            filtered_data =scipy.signal.filtfilt(b, a, data, axis=1)
            # for channel_num in range(0, data.shape[0]):
            # filtered_data[channel_num,:] =scipy.signal.lfilter(b, a, data[channel_num,:])
            #   filtered_data[channel_num, :] =scipy.signal.filtfilt(b, a, data[channel_num, :])
        else:
            # filtered_data =scipy.signal.lfilter(b, a, data)
            filtered_data =scipy.signal.filtfilt(b, a, data)

    FType = ''
    if showresponse == 1:
        if filter_type == 'butter':
            FType = 'Butterworth'
        elif filter_type == 'cheby1':
            FType = 'Chebyshev I'
        elif filter_type == 'cheby2':
            FType = 'Chebyshev II'
        elif filter_type == 'ellip':
            FType = 'Cauer/Elliptic'
        elif filter_type == 'bessel':
            FType = 'Bessel/Thomson'

        if analog_filt == 1:
            mode = 'Analog'
        else:
            mode = 'Digital'

        if analog_filt is False:
            w, h =scipy.signal.freqz(b, a, worN=8000)  # returns the requency response h, and the normalized angular
            # frequencies w in radians/sample
            # w (radians/sample) * Fs (samples/sec) * (1 cycle/2pi*radians) = Hz
            f = Fs * w / (2 * np.pi)  # Hz
        else:
            w, h =scipy.signal.freqs(b, a, worN=8000)  # returns the requency response h, and the angular frequencies
            # w in radians/sec
            # w (radians/sec) * (1 cycle/2pi*radians) = Hz
            f = w / (2 * np.pi)  # Hz

        plt.figure(figsize=(20, 15))
        plt.subplot(211)
        plt.semilogx(f, np.abs(h), 'b')
        plt.xscale('log')
        plt.title('%s Filter Frequency Response (%s)' % (FType, mode))
        plt.xlabel('Frequency(Hz)')
        plt.ylabel('Gain [V/V]')
        plt.margins(0, 0.1)
        plt.grid(which='both', axis='both')
        plt.axvline(cutoff, color='green')

    return filtered_data

def iirfilt(bandtype, data, Fs, Wp, Ws=[], order=3, analog_val=False, automatic=0, Rp=3, As=60, filttype='butter',
            showresponse=0):
    '''Designs butterworth filter:
    Data is the data that you want filtered
    Fs is the sampling frequency (in Hz)
    Ws and Wp are stop and pass frequencies respectively (in Hz)

    Passband (Wp) : This is the frequency range which we desire to let the signal through with minimal attenuation.
    Stopband (Ws) : This is the frequency range which the signal should be attenuated.

    Digital: Ws is the normalized stop frequency where 1 is the nyquist freq (pi radians/sample in digital)
             Wp is the normalized pass frequency

    Analog: Ws is the stop frequency in (rads/sec)
            Wp is the pass frequency in (rads/sec)

    Analog is false as default, automatic being one has Python select the order for you. pass_atten is the minimal attenuation
    the pass band, stop_atten is the minimal attenuation in the stop band. Fs is the sample frequency of the signal in Hz.

    Rp = 0.1      # passband maximum loss (gpass)
    As = 60 stoppand min attenuation (gstop)


    filttype : str, optional
        The type of IIR filter to design:
        Butterworth : ‘butter’
        Chebyshev I : ‘cheby1’
        Chebyshev II : ‘cheby2’
        Cauer/elliptic: ‘ellip’
        Bessel/Thomson: ‘bessel’

    bandtype : {‘bandpass’, ‘lowpass’, ‘highpass’, ‘bandstop’}, optional
    '''

    cutoff = Wp

    if Ws != []:
        cutoff2 = Ws

    b, a = get_a_b(bandtype, Fs, Wp, Ws, order=order, Rp=Rp, As=As, analog_val=analog_val, filttype=filttype, automatic=automatic)

    if len(data) != 0:
        if len(data.shape) > 1:

            filtered_data = np.zeros((data.shape[0], data.shape[1]))
            filtered_data = scipy.signal.filtfilt(b, a, data, axis=1)
        else:
            filtered_data = scipy.signal.filtfilt(b, a, data)

    if showresponse == 1:  # set to 1 if you want to visualize the frequency response of the filter
        if filttype == 'butter':
            FType = 'Butterworth'
        elif filttype == 'cheby1':
            FType = 'Chebyshev I'
        elif filttype == 'cheby2':
            FType = 'Chebyshev II'
        elif filttype == 'ellip':
            FType = 'Cauer/Elliptic'
        elif filttype == 'bessel':
            FType = 'Bessel/Thomson'

        if analog_val:
            mode = 'Analog'
        else:
            mode = 'Digital'

        if not analog_val:
            w, h = scipy.signal.freqz(b, a, worN=8000)  # returns the requency response h, and the normalized angular
            # frequencies w in radians/sample
            # w (radians/sample) * Fs (samples/sec) * (1 cycle/2pi*radians) = Hz
            f = Fs * w / (2 * np.pi)  # Hz
        else:
            w, h = scipy.signal.freqs(b, a, worN=8000)  # returns the requency response h,
            # and the angular frequencies w in radians/sec
            # w (radians/sec) * (1 cycle/2pi*radians) = Hz
            f = w / (2 * np.pi)  # Hz

        plt.figure(figsize=(10, 5))
        plt.semilogx(f, np.abs(h), 'b')
        plt.xscale('log')

        if 'cutoff2' in locals():
            plt.title('%s Bandpass Filter Frequency Response (Order = %s, Wp=%s (Hz), Ws =%s (Hz))'
                      % (FType, order, cutoff, cutoff2))
        else:
            plt.title('%s Lowpass Filter Frequency Response (Order = %s, Wp=%s (Hz))'
                      % (FType, order, cutoff))

        plt.xlabel('Frequency(Hz)')
        plt.ylabel('Gain [V/V]')
        plt.margins(0, 0.1)
        plt.grid(which='both', axis='both')
        plt.axvline(cutoff, color='green')
        if 'cutoff2' in locals():
            plt.axvline(cutoff2, color='green')
            # plt.plot(cutoff, 0.5*np.sqrt(2), 'ko') # cutoff frequency
        plt.show()
    if len(data) != 0:
        return filtered_data

def get_a_b(bandtype, Fs, Wp, Ws, order=3, Rp=3, As=60, analog_val=False, filttype='butter', automatic=0):

    stop_amp = 1.5
    stop_amp2 = 1.4

    if not analog_val:  # need to convert the Ws and Wp to have the units of pi radians/sample
        # this is for digital filters
        if bandtype in ['low', 'high']:
            Wp = Wp / (Fs / 2)  # converting to fraction of nyquist frequency

            Ws = Wp * stop_amp

        elif bandtype == 'band':
            Wp = Wp / (Fs / 2)  # converting to fraction of nyquist frequency
            Wp2 = Wp / stop_amp2

            Ws = Ws / (Fs / 2)  # converting to fraction of nyquist frequency
            Ws2 = Ws * stop_amp2

    else:  # need to convert the Ws and Wp to have the units of radians/sec
        # this is for analog filters
        if bandtype in ['low', 'high']:
            Wp = 2 * np.pi * Wp

            Ws = Wp * stop_amp

        elif bandtype == 'band':
            Wp = 2 * np.pi * Wp
            Wp2 = Wp / stop_amp2

            Ws = 2 * np.pi * Ws
            Ws2 = Ws * stop_amp2

    if automatic == 1:
        if bandtype in ['low', 'high']:
            b, a = scipy.signal.iirdesign(wp=Wp, ws=Ws, gpass=Rp, gstop=As, analog=analog_val, ftype=filttype)
        elif bandtype == 'band':
            b, a = scipy.signal.iirdesign(wp=[Wp, Ws], ws=[Wp2, Ws2], gpass=Rp, gstop=As, analog=analog_val, ftype=filttype)
    else:
        if bandtype in ['low', 'high']:
            if filttype == 'cheby1' or 'cheby2' or 'ellip':
                b, a = scipy.signal.iirfilter(order, Wp, rp=Rp, rs=As, btype=bandtype, analog=analog_val, ftype=filttype)
            else:
                b, a = scipy.signal.iirfilter(order, Wp, btype=bandtype, analog=analog_val, ftype=filttype)
        elif bandtype == 'band':
            if filttype == 'cheby1' or 'cheby2' or 'ellip':
                b, a = scipy.signal.iirfilter(order, [Wp, Ws], rp=Rp, rs=As, btype=bandtype, analog=analog_val,
                                        ftype=filttype)
            else:
                b, a = scipy.signal.iirfilter(order, [Wp, Ws], btype=bandtype, analog=analog_val, ftype=filttype)

    return b, a