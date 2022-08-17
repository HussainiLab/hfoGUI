from .load_intan_rhd_format.load_intan_rhd_format import read_rhd_data
from .filtering import notch_filt, iirfilt, get_a_b

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
    duration = time[-1] - time[0]

    efg_header = intan_to_lfp_header_dict(intan_data, True)

    eeg_header = intan_to_lfp_header_dict(intan_data, False)

    write_faux_set_file(eeg_header, session_name, output_dir, duration)

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


            write_eeg_or_egf_file(egf_ephys_data, duration, efg_header, channel, session_name, output_dir, is_egf=True)


            # EEG
            eeg_ephys_data, N = fir_hann(egf_ephys_data, 4.8e3, 125, n_taps=101, showresponse=0)

            # converting data from int16 to int8
            #value = np.divide(eeg_ephys_data, 256).astype(int)
            #eeg_ephys_data[np.where(eeg_ephys_data > 127)] = 127
            #eeg_ephys_data[np.where(eeg_ephys_data < -128)] = -128

            # downsample the data
            eeg_ephys_data = down_sample_timeseries(filtered_data, 4.8e3, 250)

            eeg_ephys_data = eeg_ephys_data.astype(np.int8)


            write_eeg_or_egf_file(eeg_ephys_data, duration, eeg_header, channel, session_name, output_dir, is_egf=False)



def write_eeg_or_egf_file(lfp_single_unit_data, duration,lfp_header_dict, channel_name, session_name, output_dir, is_egf=False):
    """Writes a single channel of eeg data to a .eeg file.

    Parameters
        lfp_single_unit_data : numpy.array
            The data to be written to the .eeg file.
        duration : float
            The duration of the data in seconds.
        eeg_header_dict : dict
            The header dictionary for the .eeg file.
        channel_name : str
            The name of the channel to be written to the .eeg file.
        session_name : str
            The name of the session to be written to the .eeg file.
        output_dir : str
            The output directory for the .eeg file.

    Returns
        None
            (Writes a .eeg file to the output directory without returning an output.)
    """

    if is_egf:
        filepath = os.path.join(output_dir, session_name + '.egf{}'.format(channel_name[-3:]))
    else:
        filepath = os.path.join(output_dir, session_name + '.eeg{}'.format(channel_name[-3:]))


    with open(filepath, 'w') as f:
        header = "\nThis data set was created by the hfoGUI software."

        num_chans = '\nnum_chans 1'

        num_samples = len(lfp_single_unit_data)

        if is_egf:
            sample_rate = '\nsample_rate 4.8e3'
            b_p_sample = '\nbytes_per_sample 2'
        else:
            sample_rate = '\nsample_rate 250 Hz'
            b_p_sample = '\nbytes_per_sample 1'

        num_samples_line = '\nnum_samples %d' % (num_samples)

        p_position = '\nsamples_per_position %d' % (5)

        duration = '\nduration %.3f' % (duration)

        start = '\ndata_start'

        write_order = [header, num_chans,sample_rate, p_position, b_p_sample, num_samples_line, start]

        # write the header to the file
        f.writelines(write_order)

    # write the data to the file
    if is_egf:
        data = struct.pack('<%dh' % (num_samples), *[np.int16(data_value) for data_value in lfp_single_unit_data.tolist()])
    else:
        data = struct.pack('<%dh' % (num_samples), *[np.int8(data_value) for data_value in lfp_single_unit_data.tolist()])


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
            lfp_ephys_data[intan_data["amplifier_channels"][i]["native_channel_name"]] = down_sample_timeseries(intan_data['amplifier_data'][i], amplifier_sample_rate, sample_rate)

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

"""
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
"""

def get_set_header(set_filename):
    with open(set_filename, 'r+') as f:
        header = ''
        for line in f:
            header += line
            if 'sw_version' in line:
                break
    return header


def write_faux_set_file(intan_header_dict, session_name, output_dir, duration):
    set_filepath = os.path.join(output_dir, session_name + '.set')

    timestamp = 'created ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    duration = '\nduration {}'.format(str(duration))

    ADC_fullscale_mv = '\nADC_fullscale_mv {}'.format(1500) # TODO - 1500 may not be the correct number; replace with real one once you can ask Abid what it should be

    gains = ['\ngain_ch_{} {}'.format(channel[-3:], 6277) for channel in intan_header_dict['channels']] # TODO - 6277 is a fake number; replace with real one once you can ask Abid what it should be; Are these gain values inside the intan header??? Maybe in the channel data dictionary?
    EEG_ch = ['\nEEG_ch_{} {}'.format(channel[-3:], int(channel[-3:]) + 1) for channel in intan_header_dict['channels']]

    additional = '\nThis is a fake set file created by the hfoGUI software.\n' \

    write_order = [timestamp, duration, ADC_fullscale_mv] + gains + EEG_ch + [additional]

    with open(set_filepath, 'w+') as f:
        f.writelines(write_order)

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
        lfp_header['sample_rate'] = 250.0 #TODO: Check this

    for key in intan_data['frequency_parameters'].keys():
        lfp_header[key] = intan_data['frequency_parameters'][key]
    lfp_header['channels'] = [intan_data['amplifier_channels'][i]['native_channel_name'] for i in range(len(intan_data['amplifier_channels']))]

    return lfp_header


def get_set_header(set_filename):
    with open(set_filename, 'r+') as f:
        header = ''
        for line in f:
            header += line
            if 'sw_version' in line:
                break
    return header

def intan_scalar():
    """returns the scalar value that can be element-wise multiplied to the data
    to convert from bits to micro-volts"""
    Vswing = 2.45
    bit_range = 2 ** 16  # it's 16 bit system
    gain = 192  # V/V, listed in the intan chip's datasheet
    return (1e6) * (Vswing) / (bit_range * gain)