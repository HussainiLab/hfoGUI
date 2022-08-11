from .load_intan_rhd_format.load_intan_rhd_format import read_rhd_data

from .Intan_to_Tint import (
    intan_to_egf_dicts
    ,down_sample_timeseries
)

import os
import numpy as np
import pytest



def test_good_base_directory():
    """
    Test that the directory is valid.
    """
    base_dir = os.getcwd().replace('\\','/')
    assert base_dir == "K:/ke/ops/cumc/repos/hfoGUI"

def test_read_rhd_data():
    """
    Test that the data is read correctly.
    """
    #base_dir = os.getcwd().replace('\\','/')

    #data = read_rhd_data(base_dir + '/hfoGUI/core/load_intan_rhd_format/sampledata.rhd')

    data_path = "K:\ke\sta\data\cumc\INTAN_TEST\RADHA_MOUSE_AJ_950um_AQ_950um_220411_142605.rhd"

    data = read_rhd_data(data_path)

    #for i in range(len(data["amplifier_data"])):
    #    print(data["amplifier_channels"][i]["custom_channel_name"])
    #    print(data["amplifier_data"][i])


    #for header in data:
    #    print(header)
    #    print(data[header], "\n\n")

    #Check the types of the data we will use.
    assert type(data) == dict
    assert type(data['t_amplifier']) == np.ndarray
    assert type(data['amplifier_data']) == np.ndarray
    assert type(data['spike_triggers']) == list
    for channel in data['spike_triggers']:
        assert type(channel) == dict

def test_intan_to_egf_dicts():
    """
    Test that the intan data is converted to egf.
    """
    base_dir = os.getcwd().replace('\\','/')
    intan_data = read_rhd_data(base_dir + '/hfoGUI/core/load_intan_rhd_format/sampledata.rhd')
    egf_ephys_data, egf_header = intan_to_egf_dicts(intan_data)

    raise Exception("Not implemented")


def test_down_sample_timeseries():

    data = np.arange(0,np.random.randint(0,5000))

    sample_rate = np.random.uniform(1,5000)

    new_sample_rate = np.random.uniform(1,sample_rate)

    downsampled_data = down_sample_timeseries(data, sample_rate, new_sample_rate)

    # assert that the length of downsampled_data is within + or - 1 of the formula.
    assert len(downsampled_data) <= len(data) / (sample_rate / new_sample_rate) + 1 and len(downsampled_data) >= len(data) / (sample_rate / new_sample_rate) - 1