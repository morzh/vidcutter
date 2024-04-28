import json
import pickle

# import matplotlib.pyplot as plt
import moviepy
import numpy as np
from PyQt5.QtCore import QTime
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication
from moviepy.editor import *

from vidcutter.data_structures.qpixmap_pickle import QPixmapPickle
from vidcutter.data_structures.video_item import VideoItem
from vidcutter.data_structures.video_list import VideoList

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


videos_list_path = '/home/anton/work/fitMate/datasets/squats_2022_ten_frames'
image_size = 128
data_filename = 'data.pickle'

issues_list = ['video of a bad quality',
               'video is too dark',
               'exercise is not performed',
               'strong occlusions',
               'too many people in video',
               'camera shake',
               'video is too long']

action_classes = ['Squat with V grip', 'Leg Press', 'Seated Cable Row', 'Barbell Bench Press', 'Rope Tricep Pushdown', 'Squats']

video_files = [f for f in os.listdir(videos_list_path) if os.path.isfile(os.path.join(videos_list_path, f))]
videos = []
preview_postfix = '.preview.mp4'

video_list = VideoList(issues_list, actionLabels=action_classes)
app = QApplication(sys.argv)

for video_file in video_files:
    print(video_file)
    if preview_postfix in video_file:
        continue
    video_filepath = os.path.join(videos_list_path, video_file)
    try:
        video_file_clip = VideoFileClip(video_filepath)
    except:
        continue

    try:
        ext = video_file.split('.')[-1]
        json_filepath = os.path.join(videos_list_path, video_file.replace(ext, 'info.json'))
        json_file = open(json_filepath, "r")
        video_data = json.loads(json_file.read())
        youtube_id = video_data['id']
    except:
        youtube_id = ''

    video_file_clip.filename = video_file
    video_duration = video_file_clip.duration
    thumb = video_file_clip.get_frame(0.5 * video_duration)

    video_preview_filepath = video_filepath + preview_postfix
    if not os.path.isfile(video_preview_filepath):
        clip_resized = moviepy.video.fx.all.resize(video_file_clip, height=128)
        clip_resized.write_videofile(video_preview_filepath)

    video_item_duration = QTime(0, 0)
    video_item_duration = video_item_duration.addSecs(int(video_duration))
    video_item_duration = video_item_duration.addMSecs(int(1000*(video_duration - int(video_duration))))

    height, width, channel = thumb.shape
    center = np.array([int(0.5 * height), int(0.5 * width)])
    minimum_side = min(height, width) - 1
    thumb_cropped = thumb[int(center[0] - 0.5 * minimum_side):int(center[0] + 0.5 * minimum_side), int(center[1] - 0.5 * minimum_side):int(center[1] + 0.5 * minimum_side)]
    '''
    plt.imshow(thumb)
    plt.show()

    plt.imshow(thumb_cropped)
    plt.show()
    '''
    height, width, channel = thumb_cropped.shape
    bytesPerLine = 3 * width
    qt_image = QImage(thumb_cropped.data.tobytes(), width, height, bytesPerLine, QImage.Format_RGB888)
    qt_image.scaledToWidth(image_size)
    qt_pixmap = QPixmap.fromImage(qt_image)

    videoItem = VideoItem()
    videoItem.filename = video_file
    videoItem.duration = video_item_duration
    videoItem.thumbnail = QPixmapPickle(qt_pixmap)
    videoItem.youtubeId = youtube_id

    videos.append(videoItem)

video_list.videos = videos
data_filepath = os.path.join(videos_list_path, data_filename)
with open(data_filepath, 'wb') as json_file:
    pickle.dump(video_list, json_file)
