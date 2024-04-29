import pickle

# import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication
from moviepy.editor import *

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

image_size = 128
data_filename = 'data.pickle'

app = QApplication(sys.argv)

with open(os.path.join(videos_list_path, data_filename), 'rb') as f:
    videoList = pickle.load(f)

# print(videoList)

video_list_ = video_list()
video_list_.description = videoList.description
video_list_.currentVideoIndex = videoList.currentVideoIndex
video_list_._videoIssuesClasses = videoList.video_issues_classes
video_list_.actionClassesLabels = videoList.actionClassesLabels
video_list_.actionClassUnknownLabel = videoList.actionClassUnknownLabel

for video in videoList:
    video_item_ = video_item()

    # video_item_.thumbnail = qpixmap_pickle()
    video_item_.thumbnail = qpixmap_pickle(video.thumbnail.copy())
    # video_item_.thumbnail = video.thumbnail
    video_item_.duration = video.duration
    video_item_.currentCLipIndex = video._currentCLipIndex

    video_item_.filename = video.filename
    video_item_.description = video.description
    video_item_.youtubeId = video.youtubeId
    video_item_.issues = video.issues

    video_item_clips = []
    for clip in video.clips:
        video_item_clip_ = video_item_clip()

        video_item_clip_.timeStart = clip.timeStart
        video_item_clip_.timeEnd = clip.timeEnd
        video_item_clip_.thumbnail = qpixmap_pickle(clip.thumbnail.copy())
        # video_item_clip_.thumbnail.fromImage(clip.thumbnail.toImage())
        video_item_clip_.visibility = clip.visibility

        video_item_clip_.description = clip.description
        video_item_clip_.actionClassIndex = clip.actionClassIndex
        video_item_clip_.boundingBox = bounding_box()

        video_item_clips.append(video_item_clip_)

    video_item_.clips = SortedList(video_item_clips)
    video_list_.videos.append(video_item_)


with open(os.path.join(videos_list_path_timestamps, data_filename), 'wb') as f:
    pickle.dump(video_list_, f)

