# -*- coding: utf-8 -*-

"""
Copyright (c) 2019 Galib F. Arrieta
Copyright (c) 2017 Guillaume Chevalier

Permission is hereby granted, free of charge, to any person obtaining a copy of 
this software and associated documentation files (the "Software"), to deal in 
the Software without restriction, including without limitation the rights to 
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies 
of the Software, and to permit persons to whom the Software is furnished to do 
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
SOFTWARE.
"""
#Most of the code copied from:
#https://github.com/guillaume-chevalier/filtering-stft-and-laplace-transform
import scipy.signal as signal

def _butter_lowpass(cutoff, nyq_freq, order=4):
    normal_cutoff = float(cutoff) / nyq_freq
    b, a = signal.butter(order, normal_cutoff, btype='lowpass')
    return b, a

#input_data is a numpy array.
#returns a numpy array with the low pass signal.
def butter_lowpass_filter(input_data, cutoff_freq, nyq_freq, order=4):
    b, a = _butter_lowpass(cutoff_freq, nyq_freq, order=order)
    lowpass_data = signal.filtfilt(b, a, input_data)
    return lowpass_data

__all__ = ['butter_lowpass_filter']
