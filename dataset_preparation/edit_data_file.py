import pickle

# import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication
from moviepy.editor import *

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

videos_list_new_path = '/home/anton/work/fitMate/datasets/squats_2022'

action_classes = ['Squat with V grip',
                  'Leg Press',
                  'Seated Cable Row',
                  'Barbell Bench Press',
                  'Barbell Squat',
                  'Barbel Row',
                  'Rope Tricep Pushdown',
                  'Squats',
                  'Romanian Deadlifts',  # румынская тяга
                  'Overhead Press',
                  'Back Squat',
                  'Conventional Deadlifts'  # становая тяга
                  ]

action_classes = sorted(action_classes)

output_path = '/home/anton/work/fitMate/datasets/squats_2022'
filename = 'data.pickle'

app = QApplication(sys.argv)

with open(os.path.join(videos_list_new_path, filename), 'rb') as file:
    data_new_format = pickle.load(file)

# with open(os.path.join(output_path, 'data.pickle'), 'wb') as f:
#     pickle.dump(data_new_format, f)

indices_to_delete = [47, 50, 69, 71, 75, 76, 78, 79, 80, 81]
indices_to_delete = [idx - 1 for idx in indices_to_delete]

for index in sorted(indices_to_delete, reverse=True):
    del data_new_format.videos[index]


old_action_classes = data_new_format.actionClassesLabels
data_new_format.actionClassesLabels = action_classes

for video in data_new_format.videos:
    for clip in video.clips:
        old_action_class_name = old_action_classes[clip.actionClassIndex]
        new_index = action_classes.index(old_action_class_name)
        clip.actionClassIndex = new_index

with open(os.path.join(output_path, 'data.pickle'), 'wb') as f:
    pickle.dump(data_new_format, f)
