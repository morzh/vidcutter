import pickle
import os

import numpy as np
import matplotlib.pyplot as plt
from moviepy.editor import * # import everythings (variables, classes, methods...) inside moviepy.editor
from PyQt5.QtCore import (QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize, Qt, QTextStream, QTime)
from PyQt5.QtGui import QImage
from PyQt5.QtGui import QPixmap

from vidcutter.VideoItem import VideoItem


videos_list_path = '/home/morzh/work/enhancersUtils/vidcutter_test_videos'
image_size = 256

video_files = [f for f in os.listdir(videos_list_path) if os.path.isfile(os.path.join(videos_list_path, f))]
videos_list = []

for video_file in video_files:
    print(video_file)
    video_clip = VideoFileClip(os.path.join(videos_list_path, video_file))
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

    bytesPerLine = 3 * width
    qt_image = QImage(thumb.data, width, height, bytesPerLine, QImage.Format_RGB888)
    qt_image.scaledToWidth(image_size)
    qt_pixmap = QPixmap.fromImage(qt_image)

    videoItem = VideoItem()
    videoItem.filename = video_file
    videoItem.duration = video_duration
    videoItem.thumbnail = qt_pixmap

    videos_list.append(videoItem)

pickle.dump(videos_list)