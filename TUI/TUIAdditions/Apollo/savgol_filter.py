import numpy as np
from scipy.linalg import lstsq
from scipy.ndimage import convolve1d

def savgol_filter(arr, window, polyorder, mode = "wrap"):
    # line only for now
    if window % 2 != 1:
        print("window size must be odd number")
        return arr
    length = len(arr)
    pad = window / 2
    #arr = np.concatenate([arr[-pad:],arr,arr[:pad]])
    
    x = np.arange(-pad, window - pad,  dtype = float)
    order = np.arange(polyorder + 1).reshape(-1, 1)
    A = x ** order
    y = np.zeros(polyorder + 1)
    y[0] = 1 / (1.0 ** 0)
    
    coeffs, _, _, _ = lstsq(A,y)
    
    arr = np.asarray(arr)
    arr = arr.astype(np.float64)
    
    newarr = convolve1d(arr, coeffs, mode = mode)

    return newarr
