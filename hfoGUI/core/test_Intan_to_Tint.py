from .load_intan_rhd_format.load_intan_rhd_format import read_rhd_data

from .Intan_to_Tint import (
    create_eeg_and_egf_files
    ,intan_to_lfp_dicts
    ,intan_ephys_to_lfp_dict
    ,intan_to_lfp_header_dict
    ,down_sample_timeseries
    ,intan_scalar
)

import os
import numpy as np
import pytest

base_dir = os.getcwd().replace('\\','/')
intan_data = read_rhd_data(base_dir + '/hfoGUI/core/load_intan_rhd_format/sampledata.rhd')
#intan_data = read_rhd_data("K:/ke/sta/data/cumc/intan_sample/b6_august_18_1_1100_plgt_190422_112734.rhd")

def test_good_base_directory():
    """
    Test that the directory is valid.
    """
    base_dir = os.getcwd().replace('\\','/')
    assert base_dir == "K:/ke/ops/cumc/repos/hfoGUI"

def test_create_eeg_and_egf_files():
    #create_eeg_and_egf_files(intan_data, 'test_session', base_dir + '/test_outputs/')
    create_eeg_and_egf_files(intan_data, 'test_session', base_dir + '/test_outputs/')


def test_read_rhd_data():
    """
    Test that the data is read correctly.
    """
    #base_dir = os.getcwd().replace('\\','/')

    #data = read_rhd_data(base_dir + '/hfoGUI/core/load_intan_rhd_format/sampledata.rhd')

    #data_path = "K:/ke/sta/data/cumc/INTAN_TEST/RADHA_MOUSE_AJ_950um_AQ_950um_220411_142605.rhd"

    #intan_data = read_rhd_data(data_path)

    #for i in range(len(intan_data["amplifier_data"])):
        #print(intan_data["amplifier_channels"][i]["custom_channel_name"])
        #print(intan_data["amplifier_channels"][i])


    #for header in intan_data:
    #    print(header)
    #    print(intan_data[header], "\n\n")

    #Check the types of the data we will use.
    assert type(intan_data) == dict
    assert type(intan_data['t_amplifier']) == np.ndarray
    assert type(intan_data['amplifier_data']) == np.ndarray
    assert type(intan_data['spike_triggers']) == list
    for channel in intan_data['spike_triggers']:
        assert type(channel) == dict

def test_intan_to_lfp_dicts():
    """
    Test that the intan data is converted to lfp.
    """
    base_dir = os.getcwd().replace('\\','/')
    intan_data = read_rhd_data(base_dir + '/hfoGUI/core/load_intan_rhd_format/sampledata.rhd')
    #lfp_ephys_data, lfp_header = intan_to_lfp_dicts(intan_data)
    # Test for egf

    # Test for eeg

    pass

def test_intan_to_lfp_header_dict():
    base_dir = os.getcwd().replace('\\','/')
    intan_data = read_rhd_data(base_dir + '/hfoGUI/core/load_intan_rhd_format/sampledata.rhd')

    # Test for egf

    # Test for eeg

    pass

def test_intan_ephys_to_lfp_dict():

    # Test for egf
    _test_intan_ephys_to_lfp_dict(egf=True)

    # Test for eeg
    _test_intan_ephys_to_lfp_dict(egf=False)


def _test_intan_ephys_to_lfp_dict(egf:bool):
    #base_dir = os.getcwd().replace('\\','/')
    #intan_data = read_rhd_data(base_dir + '/hfoGUI/core/load_intan_rhd_format/sampledata.rhd')
    sample_rate = intan_data['frequency_parameters']['amplifier_sample_rate']
    if egf:
        lfp_ephys_data = intan_ephys_to_lfp_dict(intan_data, egf=True)
        new_sample_rate = 4.8e3
    else:
        lfp_ephys_data = intan_ephys_to_lfp_dict(intan_data, egf=False)
        new_sample_rate = 250.0

    del lfp_ephys_data["time"]

    assert len(lfp_ephys_data) == len(intan_data['amplifier_data'])

    for i, channel in enumerate(lfp_ephys_data.keys()):
        new_len = len(lfp_ephys_data[channel])
        old_len = len(intan_data['amplifier_data'][i])

        assert new_len <= old_len / (sample_rate / new_sample_rate) + 1 and new_len >= old_len / (sample_rate / new_sample_rate) - 1


def test_down_sample_timeseries():

    data = np.arange(0,np.random.randint(0,5000))

    sample_rate = np.random.uniform(1,5000)

    new_sample_rate = np.random.uniform(1,sample_rate)

    downsampled_data = down_sample_timeseries(data, sample_rate, new_sample_rate)

    # assert that the length of downsampled_data is within + or - 1 of the formula.
    assert len(downsampled_data) == round(len(data) / (sample_rate / new_sample_rate) - 1)