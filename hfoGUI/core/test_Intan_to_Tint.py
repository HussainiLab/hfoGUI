from .load_intan_rhd_format.load_intan_rhd_format import read_rhd_data

import os
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
    base_dir = os.getcwd().replace('\\','/')

    data = read_rhd_data(base_dir + '/hfoGUI/core/load_intan_rhd_format/sampledata.rhd')

    assert dict == type(data)


