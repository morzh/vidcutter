import pickle

# import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication
from moviepy.editor import *

from vidcutter.data_structures.video_item import VideoItemClip

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


videos_list_new_path = '/home/anton/work/fitMate/datasets/ALEX_test_set_squats_001/'
videos_list_old_path = '/home/anton/work/fitMate/datasets/ANT_test_set_squats_001/'
filename = 'data.pickle'

app = QApplication(sys.argv)

with open(os.path.join(videos_list_new_path, filename), 'rb') as file:
    data_new_format = pickle.load(file)

with open(os.path.join(videos_list_old_path, filename), 'rb') as file:
    data_old_format = pickle.load(file)

# print(data_new_format)

for video_new in data_new_format.videos:
    video_filename_new = video_new.filename
    for video_old in data_old_format:
        if video_filename_new == video_old.filename:
            video_new.clips.clear()
            for idx in range(len(video_old.clips)):
                clip = VideoItemClip()
                clip.timeStart = video_old.clips[idx].timeStart
                clip.timeEnd = video_old.clips[idx].timeEnd
                clip.visibility = 2
                clip.thumbnail = video_old.clips[idx].thumbnail
                clip.actionClassIndex = 2
                video_new.clips.add(clip)


with open(os.path.join(videos_list_new_path, 'data.pickle'), 'wb') as f:
    pickle.dump(data_new_format, f)