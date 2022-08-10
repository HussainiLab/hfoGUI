from .load_intan_rhd_format.load_intan_rhd_format import read_rhd_data

import numpy as np

def intan_to_egf(intan_data: dict):
    """
    Convert intan data to set.
    """
    amplifier_data = intan_data['amplifier_data']

    amplifier_sample_rate = float(intan_data['frequency_parameters']['amplifier_sample_rate'])

    egf_sample_rate = 4.8e3

    return None


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
    # data would ideally be sample from.
    subsample = np.arange(0, data.size, skip_size)
    #Find the nearest index value to the subsample.
    new_index = [int(round(i)) for i in subsample]

    if len(data) == new_index[-1]:
        new_index.pop()

    #Downsample the data.
    downsampled_data = data[new_index]

    return downsampled_data