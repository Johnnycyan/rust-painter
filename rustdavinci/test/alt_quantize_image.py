#!/usr/bin/env python3

# pip install scikit-image
# pip install scipy

import numpy as np
from PIL import Image
from skimage import color

def CIE76DeltaE2(Lab1,Lab2):
    """Returns the square of the CIE76 Delta-E colour distance between 2 lab colours"""
    return (Lab2[0]-Lab1[0])*(Lab2[0]-Lab1[0]) + (Lab2[1]-Lab1[1])*(Lab2[1]-Lab1[1]) + (Lab2[2]-Lab1[2])*(Lab2[2]-Lab1[2])

def NearestPaletteIndex(Lab,palLab):
    """Return index of entry in palette that is nearest the given colour"""
    NearestIndex = 0
    NearestDist   = CIE76DeltaE2(Lab,palLab[0,0])
    for e in range(1,palLab.shape[0]):
        dist = CIE76DeltaE2(Lab,palLab[e,0])
        if dist < NearestDist:
            NearestDist = dist
            NearestIndex = e
    return NearestIndex

# Updated palette with the new 4x16 color grid
palette = (
    # Row 1 - Black to white
    0, 0, 0,       115, 115, 115,    191, 191, 191,   255, 255, 255,
    # Row 2 - Browns and oranges
    51, 33, 19,    101, 65, 41,      255, 133, 50,    255, 177, 128,
    # Row 3 - Yellow tones
    51, 45, 19,    102, 90, 40,      255, 214, 52,    254, 229, 128,
    # Row 4 - Yellow-green
    46, 51, 21,    90, 101, 41,      213, 255, 51,    230, 255, 127,
    # Row 5 - Light green
    34, 50, 21,    64, 102, 41,      133, 254, 51,    179, 255, 128,
    # Row 6 - Green
    20, 51, 20,    41, 102, 42,      52, 255, 51,     128, 255, 126,
    # Row 7 - Green-cyan
    20, 51, 33,    42, 102, 66,      51, 255, 132,    127, 255, 178,
    # Row 8 - Cyan
    20, 51, 45,    40, 102, 89,      50, 255, 214,    127, 255, 230,
    # Row 9 - Cyan-blue
    20, 45, 50,    42, 90, 102,      51, 214, 255,    127, 229, 254,
    # Row 10 - Light blue
    20, 33, 50,    41, 65, 103,      50, 133, 255,    127, 179, 255,
    # Row 11 - Blue
    20, 21, 52,    41, 41, 103,      50, 51, 255,     128, 127, 255,
    # Row 12 - Purple
    33, 20, 50,    65, 41, 101,      133, 52, 255,    179, 127, 254,
    # Row 13 - Magenta
    45, 20, 50,    91, 41, 102,      214, 51, 254,    229, 127, 255,
    # Row 14 - Pink-magenta
    50, 20, 44,    103, 41, 90,      255, 51, 214,    255, 127, 228,
    # Row 15 - Pink-red
    51, 21, 33,    103, 41, 66,      254, 51, 133,    255, 127, 178,
    # Row 16 - Red
    51, 19, 20,    102, 40, 41,      255, 51, 52,     255, 127, 126
) + (2, 2, 2) * 64  # Add padding to complete 256 colors

# Load the source image as numpy array and convert to Lab colorspace
imnp = np.array(Image.open('C:\\Users\\Alexander\\Downloads\\aaa.png').convert('RGB'))
imLab = color.rgb2lab(imnp)
h,w = imLab.shape[:2]

# Load palette as numpy array, truncate unused palette entries, and convert to Lab colourspace
palnp = np.array(palette,dtype=np.uint8).reshape(256,1,3)[:64,:]  # Use only the 64 colors from our grid
palLab = color.rgb2lab(palnp)

# Make numpy array for output image
resnp = np.empty((h,w), dtype=np.uint8)

# Iterate over pixels, replacing each with the nearest palette entry
for y in range(0, h):
    for x in range(0, w):
        resnp[y, x] = NearestPaletteIndex(imLab[y,x], palLab)

# Create output image from indices, whack a palette in and save
resim = Image.fromarray(resnp, mode='P')
resim.putpalette(palette)
#resim.save('result.png')
resim.show()
