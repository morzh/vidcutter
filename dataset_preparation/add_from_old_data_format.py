import json
import os
import pickle
import shutil
import sys

# import matplotlib.pyplot as plt
import moviepy
import numpy as np
from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import QApplication
from moviepy.editor import *

from vidcutter.QPixmapPickle import QPixmapPickle
from vidcutter.VideoItem import VideoItem, VideoItemClip

ci_build_and_not_headless = False
try:
    from cv2.version import ci_build, headless
    ci_and_not_headless = ci_build and not headless
except:
    pass

if sys.platform.startswith("linux") and ci_and_not_headless:
    os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH")
if sys.platform.startswith("linux") and ci_and_not_headless:
    os.environ.pop("QT_QPA_FONTDIR")


videos_list_new_path = '/home/anton/work/fitMate/datasets/ALEX_test_set_squats_001'
videos_list_old_path = [
    '/media/anton/Windows-SSD/Documents and Settings/morzh/YandexDisk/1_Антон/OXY/squats_set_001',
    '/media/anton/Windows-SSD/Documents and Settings/morzh/YandexDisk/1_Антон/OXY/squats_set_002',
    '/media/anton/Windows-SSD/Documents and Settings/morzh/YandexDisk/1_Антон/OXY/squats_set_003',
                        ]
output_path = '/home/anton/work/fitMate/datasets/squats_2022'
filename = 'data.pickle'

app = QApplication(sys.argv)

with open(os.path.join(videos_list_new_path, filename), 'rb') as file:
    data_new_format = pickle.load(file)

# with open(os.path.join(output_path, 'data.pickle'), 'wb') as f:
#     pickle.dump(data_new_format, f)

'''
for video in data_new_format.videos:
    file_name_path_source = os.path.join(videos_list_new_path, video.filename)
    file_name_path_destination = os.path.join(output_path, video.filename)
    shutil.copyfile(file_name_path_source, file_name_path_destination)
'''

for old_path in videos_list_old_path:
    with open(os.path.join(old_path, filename), 'rb') as file:
        data_old_format = pickle.load(file)

    # print(data_new_format)
    print('number videos:', len(data_old_format.videos))
    for video_old in data_old_format.videos:
        '''
        file_name_path_source = os.path.join(old_path, video_old.filename)
        file_name_path_destination = os.path.join(output_path, video_old.filename)
        shutil.copyfile(file_name_path_source, file_name_path_destination)
        '''

        video_new = VideoItem()
        video_new.issues = video_old.issues
        video_new.filename = video_old.filename
        video_new.thumbnail = video_old.thumbnail
        for idx in range(len(video_old.clips)):
            clip = VideoItemClip()
            clip.timeStart = video_old.clips[idx].timeStart
            clip.timeEnd = video_old.clips[idx].timeEnd
            clip.visibility = 2
            clip.name = ''
            clip.thumbnail = QPixmapPickle(video_old.clips[idx].thumbnail)
            clip.actionClassIndex = 2
            video_new.clips.add(clip)

        data_new_format.videos.append(video_new)

with open(os.path.join(output_path, 'data.pickle'), 'wb') as f:
    pickle.dump(data_new_format, f)
