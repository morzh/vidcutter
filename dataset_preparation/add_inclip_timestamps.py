import pickle

# import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTime
from moviepy.editor import *
from vidcutter.data_structures.video_clip_timestamps import VideoClipTimestamps

import pathlib as path

from vidcutter.data_structures.video_list import VideoList as video_list
from vidcutter.data_structures.video_item import VideoItem as video_item
from vidcutter.data_structures.video_item_clip import VideoItemClip as video_item_clip
from vidcutter.data_structures.video_item_clip import BoundingBox as bounding_box
from vidcutter.data_structures.qpixmap_pickle import QPixmapPickle as qpixmap_pickle
from sortedcontainers import SortedList

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


videos_list_path = '/home/anton/work/fitMate/datasets/squats_2022/'
videos_list_path_timestamps = '/home/anton/work/fitMate/datasets/squats_2022/new_pickle/'
data_filename = 'data.pickle'

app = QApplication(sys.argv)

with open(os.path.join(videos_list_path, data_filename), 'rb') as f:
    video_list = pickle.load(f)

for video in video_list:
    for clip in video.clips:
        clip.clip_timestamps.clear()
        current_in_clip_timestamp = 0.5 * (clip.timeEnd.msecsSinceStartOfDay() - clip.timeStart.msecsSinceStartOfDay())
        current_video_clip_timestamp = VideoClipTimestamps(QTime.fromMSecsSinceStartOfDay(int(current_in_clip_timestamp)))
        clip.clip_timestamps.append(current_video_clip_timestamp)


with open(os.path.join(videos_list_path_timestamps, data_filename), 'wb') as f:
    pickle.dump(video_list, f)