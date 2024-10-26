import json
import pickle

import numpy as np
from PyQt5.QtCore import QTime
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication
from moviepy.editor import *

from vidcutter.data_structures.video_item import VideoItem
from vidcutter.data_structures.video_list import VideoList

from vidcutter.data_structures.qpixmap_pickle import QPixmapPickle


# videos_list_path = '/home/anton/work/fitMate/datasets/ALEX_test_set_squats_001/'
videos_list_path = '/media/anton/1e894684-3165-4ae7-9ef9-92b66b4e94ca/home/anton/work/fitMate/datasets/squats_non_compound/regular squat_steady_camera'
video_source_list_json = '/home/anton/Downloads/Telegram Desktop/video_list_one_person.json'
image_size = 64
target_data_filename = 'regular_squat_steady_single_whole_video.pickle'

issues_list = ['video of a bad quality',
               'video is too dark',
               'exercise is not performed',
               'exercise start is outside video',
               'exercise end is outside video',
               'strong occlusions',
               'camera shake or movement',
               ]


action_classes = ['Front Squat',
                  'Goblet Squat',
                  'Lateral Squat',
                  'Regular Squat',
                  'Split Squats',
                  'Suitcase Squats',
                  'Sumo Squats',
                  'Other Squats',
                  ]

# action_classes = sorted(action_classes)

video_extension = 'mp4'

with open(video_source_list_json, 'r') as f:
    videos_selected = json.load(f)

video_files = [f for f in os.listdir(videos_list_path) if os.path.isfile(os.path.join(videos_list_path, f))]
videos = []
preview_postfix = '.preview.mp4'

video_list = VideoList(issues_list, action_classes)
app = QApplication(sys.argv)

for index, video_file in enumerate(video_files):
    if not video_extension in video_file or video_file not in videos_selected:
        continue

    print(str(index).zfill(3), video_file)
    video_filepath = os.path.join(videos_list_path, video_file)
    try:
        video_file_clip = VideoFileClip(video_filepath)
    except:
        continue

    video_youtube_id = video_file[:11]
    video_file_clip.filename = video_file
    video_duration = video_file_clip.duration
    video_fps = video_file_clip.fps
    video_frames = video_duration * video_fps
    thumb = video_file_clip.get_frame(0.5 * video_duration)

    video_item_duration = QTime(0, 0)
    video_item_duration = video_item_duration.addSecs(int(video_duration))
    video_item_duration = video_item_duration.addMSecs(int(1000*(video_duration - video_duration)))

    height, width, channel = thumb.shape
    center = np.array([int(0.5 * height), int(0.5 * width)])
    minimum_side = min(height, width) - 1
    thumb_cropped = thumb[int(center[0] - 0.5 * minimum_side):int(center[0] + 0.5 * minimum_side), int(center[1] - 0.5 * minimum_side):int(center[1] + 0.5 * minimum_side)]

    height, width, _ = thumb_cropped.shape
    bytesPerLine = 3 * width
    qt_image = QImage(thumb_cropped.data.tobytes(), width, height, bytesPerLine, QImage.Format_RGB888)
    qt_image.scaledToWidth(image_size)
    qt_pixmap = QPixmap.fromImage(qt_image)

    videoItem = VideoItem()
    videoItem.filename = video_file
    videoItem.duration = video_item_duration
    videoItem.thumbnail = QPixmapPickle(qt_pixmap)
    videoItem.youtubeId = video_youtube_id

    videos.append(videoItem)

print('')
print('writing data ....')

video_list.videos = videos
data_filepath = os.path.join(videos_list_path, target_data_filename)
with open(data_filepath, 'wb') as file:
    pickle.dump(video_list, file)
