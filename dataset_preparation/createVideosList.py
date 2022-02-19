import pickle
import os
import sys

import numpy as np
# import matplotlib.pyplot as plt
from moviepy.editor import * # import everythings (variables, classes, methods...) inside moviepy.editor
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QTime
from PyQt5.QtGui import QImage
from PyQt5.QtGui import QPixmap


from vidcutter.VideoItem import VideoItem
from vidcutter.VideoItemClip import VideoItemClip
from vidcutter.QPixmapPickle import QPixmapPickle

videos_list_path = '/home/morzh/work/vidcutter_test_videos'
image_size = 128
data_filename = 'data.pickle'

video_files = [f for f in os.listdir(videos_list_path) if os.path.isfile(os.path.join(videos_list_path, f))]
videos_list = []

app = QApplication(sys.argv)

for video_file in video_files:
    print(video_file)
    try:
        video_clip = VideoItem()
    except:
        continue

    video_clip.filename = video_file
    video_duration = video_clip.duration
    thumb = video_clip.get_frame(0.5 * video_duration)

    video_item_duration = QTime(0, 0)
    video_item_duration = video_item_duration.addSecs(int(video_duration))
    video_item_duration = video_item_duration.addMSecs(1000*(video_duration - int(video_duration)))

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

    videos_list.append(videoItem)

data_filepath = os.path.join(videos_list_path, data_filename)
with open(data_filepath, 'wb') as f:
    pickle.dump(videos_list, f)
