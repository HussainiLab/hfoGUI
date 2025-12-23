"""
Standalone animal tracking utilities: position loading and speed computation.

Copy this file into another project to reuse tracking from Axona `.pos` files.

Public functions:
- grab_position_data(pos_path: str, ppm: int) -> (pos_x, pos_y, pos_t, (width_x, width_y))
- speed2D(x, y, t) -> np.ndarray

Dependencies: numpy, scipy (ndimage), struct, os
"""

from __future__ import division, print_function
import os
import struct
import numpy as np
from scipy.ndimage import convolve


def grab_position_data(pos_path: str, ppm: int) -> tuple:
    """
    Extracts position data and corrects bad tracking from an Axona `.pos` file.

    Params:
        pos_path (str): Absolute path to the `.pos` file
        ppm (int): Pixels per meter (overridden by file header if present)

    Returns:
        Tuple: (pos_x, pos_y, pos_t, (pos_x_width, pos_y_width))
        - pos_x, pos_y, pos_t: column arrays of x, y coordinates and time
        - pos_x_width: max(pos_x) - min(pos_x)
        - pos_y_width: max(pos_y) - min(pos_y)
    """

    print("    → Reading .pos file...")
    x, y, t, Fs_pos = getpos(pos_path, ppm)
    print("    → .pos file loaded, correcting timestamps...")

    # Correcting pos_t length mismatches
    new_pos_t = np.copy(t).flatten()
    if len(new_pos_t) < len(x):
        while len(new_pos_t) < len(x):
            new_pos_t = np.append(new_pos_t, float(new_pos_t[-1] + 0.02))
    elif len(new_pos_t) > len(x):
        new_pos_t = new_pos_t[:len(x)]

    print("    → Extracting and centering coordinates...")
    pos_x = x
    pos_y = y
    pos_t = new_pos_t.reshape((len(new_pos_t), 1))

    center = centerBox(pos_x, pos_y)
    pos_x = pos_x - center[0]
    pos_y = pos_y - center[1]

    print("    → Removing bad tracking...")
    pos_x, pos_y, pos_t = remBadTrack(pos_x, pos_y, pos_t, 2)

    non_nan = np.where(~np.isnan(pos_x))[0]
    pos_t = pos_t[non_nan]
    pos_x = pos_x[non_nan]
    pos_y = pos_y[non_nan]

    print("    → Smoothing position data...")
    # Boxcar smoothing via convolution (window ~0.4 seconds)
    win = int(np.ceil(0.4 * Fs_pos))
    if win < 1:
        win = 1
    B = np.ones((win, 1)) / float(win)
    pos_x = convolve(pos_x, B, mode="nearest")
    pos_y = convolve(pos_y, B, mode="nearest")

    print("    → Position data processing complete")
    pos_x_width = float(np.nanmax(pos_x) - np.nanmin(pos_x))
    pos_y_width = float(np.nanmax(pos_y) - np.nanmin(pos_y))

    return pos_x, pos_y, pos_t, (pos_x_width, pos_y_width)


def getpos(pos_fpath, ppm, method="", flip_y=True):
    """
    Read Axona `.pos` file and return position and time arrays.

    Returns:
        x, y, t (column arrays), sample_rate (float)
    """
    with open(pos_fpath, "rb+") as f:
        headers = ""
        for line in f:
            if "data_start" in str(line):
                headers += "data_start"
                break
            elif "duration" in str(line):
                headers += line.decode(encoding="UTF-8")
            elif "num_pos_samples" in str(line):
                num_pos_samples = int(line.decode(encoding="UTF-8")[len("num_pos_samples "):])
                headers += line.decode(encoding="UTF-8")
            elif "bytes_per_timestamp" in str(line):
                bytes_per_timestamp = int(line.decode(encoding="UTF-8")[len("bytes_per_timestamp "):])
                headers += line.decode(encoding="UTF-8")
            elif "bytes_per_coord" in str(line):
                bytes_per_coord = int(line.decode(encoding="UTF-8")[len("bytes_per_coord "):])
                headers += line.decode(encoding="UTF-8")
            elif "timebase" in str(line):
                timebase = (line.decode(encoding="UTF-8")[len("timebase "):]).split(" ")[0]
                headers += line.decode(encoding="UTF-8")
            elif "pixels_per_metre" in str(line):
                ppm = float(line.decode(encoding="UTF-8")[len("pixels_per_metre "):])
                headers += line.decode(encoding="UTF-8")
            elif "min_x" in str(line) and "window" not in str(line):
                min_x = int(line.decode(encoding="UTF-8")[len("min_x "):])
                headers += line.decode(encoding="UTF-8")
            elif "max_x" in str(line) and "window" not in str(line):
                max_x = int(line.decode(encoding="UTF-8")[len("max_x "):])
                headers += line.decode(encoding="UTF-8")
            elif "min_y" in str(line) and "window" not in str(line):
                min_y = int(line.decode(encoding="UTF-8")[len("min_y "):])
                headers += line.decode(encoding="UTF-8")
            elif "max_y" in str(line) and "window" not in str(line):
                max_y = int(line.decode(encoding="UTF-8")[len("max_y "):])
                headers += line.decode(encoding="UTF-8")
            elif "pos_format" in str(line):
                headers += line.decode(encoding="UTF-8")
                if "t,x1,y1,x2,y2,numpix1,numpix2" in str(line):
                    two_spot = True
                else:
                    two_spot = False
                    print("The position format is unrecognized!")
            elif "sample_rate" in str(line):
                sample_rate = float(line.decode(encoding="UTF-8").split(" ")[1])
                headers += line.decode(encoding="UTF-8")
            else:
                headers += line.decode(encoding="UTF-8")

    if two_spot:
        with open(pos_fpath, "rb+") as f:
            pos_data = f.read()
            pos_data = pos_data[len(headers):-12]
            byte_string = "i8h"
            pos_data = np.asarray(struct.unpack(">%s" % (num_pos_samples * byte_string), pos_data))
            pos_data = pos_data.astype(float).reshape((num_pos_samples, 9))

        x = pos_data[:, 1]
        y = pos_data[:, 2]
        t = pos_data[:, 0]

        x = x.reshape((len(x), 1))
        y = y.reshape((len(y), 1))
        t = t.reshape((len(t), 1))

        if method == "raw":
            return x, y, t, sample_rate

        t = np.divide(t, float(timebase))

        x[np.where(x == 1023)] = np.nan
        y[np.where(y == 1023)] = np.nan

        didFix, fixedPost = fixTimestamps(t)
        if didFix:
            t = fixedPost
        t = t - t[0]

        x, y = arena_config(x, y, ppm, center=centerBox(x, y), flip_y=flip_y)
        x, y, t = removeNan(x, y, t)
    else:
        print("Haven't made any code for this part yet.")

    return x.reshape((len(x), 1)), y.reshape((len(y), 1)), t.reshape((len(t), 1)), sample_rate


def arena_config(posx, posy, ppm, center, flip_y=True):
    center = center
    conversion = ppm
    posx = 100 * (posx - center[0]) / conversion
    if flip_y:
        posy = 100 * (-posy + center[1]) / conversion
    else:
        posy = 100 * (posy + center[1]) / conversion
    return posx, posy


def removeNan(posx, posy, post):
    removeNanFlag = True
    while removeNanFlag:
        if np.isnan(posx[-1]):
            posx = posx[:-1]
            posy = posy[:-1]
            post = post[:-1]
        else:
            removeNanFlag = False
    return posx, posy, post


def centerBox(posx, posy):
    posx = posx[~np.isnan(posx)]
    posy = posy[~np.isnan(posy)]
    NE = np.array([np.amax(posx), np.amax(posy)])
    NW = np.array([np.amin(posx), np.amax(posy)])
    SW = np.array([np.amin(posx), np.amin(posy)])
    SE = np.array([np.amax(posx), np.amin(posy)])
    return findCenter(NE, NW, SW, SE)


def findCenter(NE, NW, SW, SE):
    x = np.mean([np.amax([NE[0], SE[0]]), np.amin([NW[0], SW[0]])])
    y = np.mean([np.amax([NW[1], NE[1]]), np.amin([SW[1], SE[1]])])
    return np.array([x, y])


def fixTimestamps(post):
    post = np.asarray(post, dtype=float).flatten()
    first = float(post[0])
    N = len(post)
    uniquePost = np.unique(post)
    if len(uniquePost) != N:
        didFix = True
        numZeros = 0
        while True:
            if post[-1 - numZeros] == 0:
                numZeros += 1
            else:
                break
        last = first + (N - 1 - numZeros) * 0.02
        fixedPost = np.arange(first, last + 0.02, 0.02)
        fixedPost = fixedPost.reshape((len(fixedPost), 1))
    else:
        didFix = False
        fixedPost = []
    return didFix, fixedPost


def remBadTrack(x, y, t, threshold):
    remInd = []
    diffx = np.diff(x, axis=0)
    diffy = np.diff(y, axis=0)
    diffR = np.sqrt(diffx ** 2 + diffy ** 2)
    diffR[np.isnan(diffR)] = threshold
    ind = np.where((diffR > threshold))[0]
    if len(ind) == 0:
        return x, y, t
    if ind[-1] == len(x):
        offset = 2
    else:
        offset = 1
    for index in range(len(ind) - offset):
        if ind[index + 1] == ind[index] + 1:
            remInd.append(ind[index] + 1)
        else:
            idx = np.where(x[ind[index] + 1 : ind[index + 1] + 1 + 1] == x[ind[index] + 1])[0]
            if len(idx) == len(x[ind[index] + 1 : ind[index + 1] + 1 + 1]):
                remInd.extend(list(range(ind[index] + 1, ind[index + 1] + 1 + 1)))
    keep_ind = np.setdiff1d(np.arange(len(x)), remInd)
    x = x[keep_ind]
    y = y[keep_ind]
    t = t[keep_ind]
    return x.reshape((len(x), 1)), y.reshape((len(y), 1)), t.reshape((len(t), 1))


def speed2D(x, y, t):
    """Calculates an averaged/smoothed 2D speed from position.

    Inputs are column arrays (N×1). Output is 1D array length N.
    """
    N = len(x)
    v = np.zeros((N, 1))
    for index in range(1, N - 1):
        v[index] = np.sqrt((x[index + 1] - x[index - 1]) ** 2 + (y[index + 1] - y[index - 1]) ** 2) / (
            t[index + 1] - t[index - 1]
        )
    v[0] = v[1]
    v[-1] = v[-2]
    v = v.flatten()
    kernel_size = 12
    kernel = np.ones(kernel_size) / kernel_size
    v_convolved = np.convolve(v, kernel, mode="same")
    return v_convolved


__all__ = ["grab_position_data", "speed2D"]
