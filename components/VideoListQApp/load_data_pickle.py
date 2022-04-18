#!/usr/bin/python

import os
import pickle
import sys

from PyQt5.QtWidgets import QApplication
sys.path.append('/home/morzh/work/vidcutter')

from vidcutter.QPixmapPickle import QPixmapPickle
from vidcutter.VideoItem import VideoItem
from vidcutter.VideoList import VideoList

# path = '/media/morzh/Storage/video_labeling_to_check/squats_set_002'
path = '/home/morzh/work/vidcutter_test_videos'
filename = 'data.pickle'
# filename = 'data(1).pickle'
app = QApplication(sys.argv)

filepath = os.path.join(path, filename)
print(filepath)
with open(filepath, 'rb') as f:
    data = pickle.load(f)

data.print()
