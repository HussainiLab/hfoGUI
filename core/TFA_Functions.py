import scipy
import numpy as np
from pyfftw.interfaces import scipy_fftpack as fftw
# from scipy.io import savemat


def s_transform(timeseries, minfreq, maxfreq, Fs, output_Fs, removeedge=False,
                analytic_signal=False, factor=1):

    """
    ------------------------------------------------------------------------
    Note: This is a conversion from code by Robert Glenn Stockwell written in
    Matlab (the st.m file)
    Reference is "Localization of the Complex Spectrum: The S Transform"
    from IEEE Transactions on Signal Processing, vol. 44., number 4, April
    1996, pages 998-1001.
    ------------------------------------------------------------------------
    inputs:
    timeseries - vector of data to be transformed
    minfreq - minimum frequency in the s_transform result
    maxfreq - maximum frequency in the s_transform result
    Fs - the sampling rate of the timeseries data
    outout_Fs - the sampling rate you desire in the s_transform result

    outputs:
    st - a complex matrix containing the Stockwell transforms (rows are frequencies,
    and the columns are the time values)

    t - the vector containing the sampled times
    f - the vector containing the samples frequencies

    """

    timeseries = timeseries.astype(np.float64)

    #nyquist = Fs / 2

    # if minfreq < 0 | minfreq > nyquist:
    #    # maximum frequency you can obtain is Nyquist frequency ()
    #    minfreq = 0
    #    print('Minfreq < 0 or > Nyquist, setting value to 0')

    if minfreq < 0 | minfreq > len(timeseries) / 2:
        # maximum frequency you can obtain is Nyquist frequency ()
        minfreq = 0
        print('Minfreq < 0 or > Nyquist, setting value to 0')

    # if maxfreq > nyquist:
    #    print('Maxfreq > Nyquist setting value to Nyquist')
    #    maxfreq = nyquist

    if maxfreq > len(timeseries) / 2:
        print('Maxfreq > Nyquist setting value to Nyquist')
        maxfreq = len(timeseries) / 2

    if minfreq > maxfreq:
        print('Minfreq > Maxfreq, swapping values')
        temp_value = minfreq
        minfreq = maxfreq
        maxfreq = temp_value
        temp_value = None

    # t = np.arange(0, len(timeseries))/Fs
    t = np.divide(np.arange(0, len(timeseries)), Fs)
    spe_nelements = np.ceil((maxfreq - minfreq + 1) / output_Fs)
    # f = (np.arange(0, spe_nelements) * output_Fs + minfreq) / (Fs * len(timeseries))
    f = np.divide(np.multiply(np.arange(0, spe_nelements), output_Fs) + minfreq, Fs*len(timeseries))

    st_values = strans(timeseries, minfreq, maxfreq, Fs, output_Fs, removeedge,
                       analytic_signal, factor)

    return st_values, t, f


def strans(timeseries, minfreq, maxfreq, Fs, output_Fs, removeedge,
           analytic_signal, factor):
    n = len(timeseries)
    original = timeseries.copy()

    if removeedge:
        print('Removing trend with polynomial fit')
        indices = np.arange(0, n)  # getting indices

        # second degree polynomial curve fitting

        p = np.polyfit(indices, timeseries, 2)

        # fitting curve
        fit = np.polyval(p, indices)

        timeseries = np.subtract(timeseries, fit)

        print('Removing edges with 5% hanning taper')

        sh_len = np.floor(len(timeseries) / 10)

        if sh_len == 0:
            sh_len = len(timeseries)
            wn = np.ones((sh_len, 1))

        else:
            # in MATLAB, hanning doesn't return the first and last indices as a zero
            # value, thus if we increase the length by 2, we get the same values as
            # in MATLAB if we remove the zero in the beginning and the end
            wn = np.hanning(sh_len + 2)
            wn = wn[1:-1]  # removes first and last indices (the zero weighted values)
            # wn = wn.transpose()

        half_sh_len = int(np.floor(sh_len / 2))
        sh_len = int(sh_len)
        timeseries[:half_sh_len + 1] = np.multiply(timeseries[:half_sh_len + 1],
                                                   wn[:half_sh_len + 1])

        timeseries[n - half_sh_len - 1:] = np.multiply(timeseries[n - half_sh_len - 1:],
                                                       wn[sh_len - half_sh_len - 1:])

    if analytic_signal:
        print('Calculating analytic signal (using Hilbert transform)')
        ts_spe = np.fft.fft(np.real(timeseries))
        # print(ts_spe)
        h = np.vstack((1,
                       2. * np.ones((int(np.fix((n - 1) / 2)), 1)),
                       np.ones((1 - np.mod(n, 2), 1)),
                       np.zeros((int(np.fix((n - 1) / 2)), 1))
                       ))
        # h = np.asarray(h, dtype=np.complex)
        # element-wise multiplication does not work like it does in matlab for
        # complex numbers and real numbers
        ts_spe = np.asarray(ts_spe, dtype=np.complex)
        ts_spe[:] = np.multiply(ts_spe, h.flatten())
        timeseries = np.fft.ifft(ts_spe)

    # compute the FFT's

    vector_fft = np.fft.fft(timeseries)
    vector_fft = vector_fft.reshape((len(vector_fft), 1))
    vector_fft = np.concatenate((vector_fft, vector_fft), axis=1)

    # print(vector_fft)

    st_output = np.zeros((int(np.ceil(maxfreq - minfreq + 1) / output_Fs), n))  # preallocate memory

    # Compute S-transform value for 1 ... ceil(n/2+1)-1 frequency points
    if minfreq == 0:
        st_output[0, :] = np.multiply(np.mean(timeseries), np.ones((1, n)))
    else:
        st_output[0, :] = np.multiply(np.fft.ifft(vector_fft.flatten('F')[minfreq:minfreq + n]),
                                      gauss_window(n, minfreq, factor)
                                      )

    freq_array = np.arange(output_Fs, (maxfreq - minfreq), output_Fs)

    st_output = np.asarray(st_output, dtype=np.complex)
    for freq in freq_array:
        st_output[int(freq / output_Fs), :] = np.fft.ifft(
            np.multiply(vector_fft.flatten('F')[int(minfreq + freq): int(minfreq + freq + n)],
                        gauss_window(n, int(minfreq + freq), factor) + 0j
                        ))

    return st_output


def stransform(h):
    '''
    Compute S-Transform without for loops

    Converted from MATLAB code written by Kalyan S. Dash

    Converted by Geoffrey Barrett, CUMC

    h - an 1xN vector representing timeseries data, units will most likely by uV

    returns the stockwell transform, representing the values of all frequencies from 0-> Fs/2 (nyquist) for each time
    '''

    h = np.asarray(h, dtype=float)

    # scipy.io.savemat('stransform_numpy.mat', {'h': h})

    h = h.reshape((1, len(h)))  # uV

    n = h.shape[1]

    n_half = np.fix(n / 2)

    n_half = int(n_half)

    odd_n = 1

    if n_half * 2 == n:
        odd_n = 0

    f = np.concatenate((np.arange(n_half + 1),
                        np.arange(-n_half + 1 - odd_n, 0)
                        )) / n

    Hft = fftw.fft(h, axis=1)  # uV

    Hft = conj_nonzeros(Hft)
    # compute all frequency domain Guassians as one matrix

    invfk = np.divide(1, f[1:n_half + 1])
    invfk = invfk.reshape((len(invfk), 1))

    W = np.multiply(2 * np.pi * np.tile(f, (n_half, 1)),
                    np.tile(invfk.reshape((len(invfk), 1)), (1, n))
                    )

    G = np.exp((-W ** 2) / 2)  # Gaussian in freq domain
    G = np.asarray(G, dtype=np.complex)

    # Compute Toeplitz matrix with the shifted fft(h)

    HW = scipy.linalg.toeplitz(Hft[0, :n_half + 1].T, np.conj(Hft))
    # HW = scipy.linalg.toeplitz(Hft[0,:n_half+1].T, Hft)

    # exclude the first row, corresponding to zero frequency

    HW = HW[1:n_half + 1, :]

    # compute the stockwell transform

    cwt = np.multiply(HW, G)

    ST = fftw.ifft(cwt, axis=-1)  # compute voices

    # add the zero freq row

    # print(np.mean(h, axis=1))

    st0 = np.multiply(np.mean(h, axis=1),
                      np.ones((1, n)))

    ST = np.vstack((st0, ST))

    return ST


def conj_nonzeros(X):
    ind = np.where(X.imag != 0)
    X[ind] = np.conj(X[ind])

    return X


def gauss_window(length, freq, factor):
    """Function to compute the Gaussion window for
    function Stransform. g_window is used by function
    Stransform. Programmed by Eric Tittley

    -----Inputs Needed--------------------------

    length-the length of the Gaussian window

    freq-the frequency at which to evaluate
    the window.
    factor- the window-width factor

    -----Outputs Returned--------------------------

    gauss-The Gaussian window
    """
    vector1 = np.arange(0, length)
    vector2 = np.arange(-length, 0)

    vector = np.vstack((vector1, vector2))

    vector = np.multiply(vector, vector)

    vector = np.multiply(vector, -factor * 2 * (np.pi ** 2) / (freq ** 2))

    gauss = np.sum(np.exp(vector), axis=0)

    return gauss


def stran_psd_old(h, minfreq, maxfreq, Fs, output_Fs):
    ST = stransform(h)

    # print(ST[:,:3])
    power = np.abs(ST)
    # print(power[:,0])
    _, _, f = s_transform(h, minfreq, maxfreq, Fs, output_Fs)

    # normalize phase estimates to one length
    nST = np.divide(ST, power)
    phase = np.angle(nST)

    return power, phase, f


def stran_psd(h, Fs, minfreq=0, maxfreq=600, output_Fs=1):
    '''The s-transform, ST, returns an NxM, N being number of frequencies, M being number of time points'''

    ST = stransform(h)  # returns all frequencies between 0 and the nyquist frequency

    nyquist = Fs / 2

    if minfreq < 0 | minfreq > nyquist:
        # maximum frequency you can obtain is Nyquist frequency ()
        minfreq = 0
        print('Minfreq < 0 or > Nyquist, setting value to 0')

    if maxfreq > nyquist:
        print('Maxfreq > Nyquist setting value to Nyquist')
        maxfreq = nyquist

    if minfreq > maxfreq:
        print('Minfreq > Maxfreq, swapping values')
        temp_value = minfreq
        minfreq = maxfreq
        maxfreq = temp_value
        temp_value = None

    f = np.arange(0, ST.shape[0]) / (ST.shape[0] - 1) * nyquist
    desired_frequency_indices = np.where((f >= minfreq) & (f <= maxfreq))
    f = f[desired_frequency_indices]
    # maxfreq_index = np.round(nyquist_index * (maxfreq/nyquist_index))
    # minfreq_index = np.round(nyquist_index * (minfreq / nyquist_index))

    ST = ST[desired_frequency_indices[0], :]

    power = np.abs(ST)

    # normalize phase estimates to one length
    nST = np.divide(ST, power)
    phase = np.angle(nST)

    return power, phase, f



