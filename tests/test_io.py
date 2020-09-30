"""
Tests for the Suite2p IO module
"""
from pathlib import Path
import os

import numpy as np
import pytest
from pynwb import NWBHDF5IO

from suite2p import io
from suite2p.io.nwb import save_nwb

@pytest.fixture()
def binfile1500(test_ops):
    test_ops['tiff_list'] = ['input_1500.tif']
    op = io.tiff_to_binary(test_ops)
    bin_filename = str(Path(op['save_path0']).joinpath('suite2p/plane0/data.bin'))
    with io.BinaryFile(Ly=op['Ly'], Lx=op['Lx'], read_filename=bin_filename) as bin_file:
        yield bin_file



def test_h5_to_binary_produces_nonnegative_output_data(test_ops):
    test_ops['h5py'] = Path(test_ops['data_path'][0]).joinpath('input.h5')
    test_ops['data_path'] = []
    op = io.h5py_to_binary(test_ops)
    output_data = io.BinaryFile(read_filename=Path(op['save_path0'], 'suite2p/plane0/data.bin'), Ly=op['Ly'], Lx=op['Lx']).data
    assert np.all(output_data >= 0)


def test_that_bin_movie_without_badframes_results_in_a_same_size_array(binfile1500):
    mov = binfile1500.bin_movie(bin_size=1)
    assert mov.shape == (1500, binfile1500.Ly, binfile1500.Lx)


def test_that_bin_movie_with_badframes_results_in_a_smaller_array(binfile1500):

    np.random.seed(42)
    bad_frames = np.random.randint(2, size=binfile1500.n_frames, dtype=bool)
    mov = binfile1500.bin_movie(bin_size=1, bad_frames=bad_frames, reject_threshold=0)

    assert len(mov) < binfile1500.n_frames, "bin_movie didn't produce a smaller array."
    assert len(mov) == len(bad_frames) - sum(bad_frames), "bin_movie didn't produce the right size array."



def test_that_binaryfile_data_is_repeatable(binfile1500):
    data1 = binfile1500.data
    assert data1.shape == (1500, binfile1500.Ly, binfile1500.Lx)

    data2 = binfile1500.data
    assert data2.shape == (1500, binfile1500.Ly, binfile1500.Lx)

    assert np.allclose(data1, data2)

@pytest.mark.parametrize("data_folder", [
    ("1plane1chan"), ("1plane1chan1500"), ("2plane2chan"), ("2plane2chan1500")])
def test_save_nwb(data_folder):
    save_folder = Path("data").joinpath("test_data", data_folder, "suite2p")

    # Change temporarily the save_folder variable saved in the NumPy file
    save_path = {}
    for plane in os.listdir(save_folder):
        if save_folder.joinpath(plane).is_dir():
            ops1 = np.load(save_folder.joinpath(plane, "ops.npy"), allow_pickle=True)
            save_path[plane] = ops1.item(0)["save_path"]
            ops1.item(0)["save_path"] = str(save_folder.joinpath(plane).absolute())
            np.save(save_folder.joinpath(plane, "ops.npy"), ops1)

    save_nwb(save_folder)
    with NWBHDF5IO(str(save_folder.joinpath("ophys.nwb")), "r") as io:
        read_nwbfile = io.read()
        assert read_nwbfile.processing
        assert read_nwbfile.processing["ophys"].data_interfaces["Deconvolved"]
        assert read_nwbfile.processing["ophys"].data_interfaces["Fluorescence"]
        assert read_nwbfile.processing["ophys"].data_interfaces["Neuropil"]

    # Undo the variable change
    for plane in os.listdir(save_folder):
        if save_folder.joinpath(plane).is_dir():
            ops1 = np.load(save_folder.joinpath(plane, "ops.npy"), allow_pickle=True)
            ops1.item(0)["save_path"] = save_path[plane]
            np.save(save_folder.joinpath(plane, "ops.npy"), ops1)

    # Remove NWB file
    save_folder.joinpath("ophys.nwb").unlink()
