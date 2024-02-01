import os.path
import cv2


video_input_path = '/home/anton/work/fitMate/datasets/squats_2022'
video_output_path = '/home/anton/work/fitMate/datasets/squats_2022_ten_frames'
number_skip_frames = 100
number_video_frames = 10
video_files_extensions = ('mkv', 'mp4', 'webm')


video_filenames = [f for f in os.listdir(video_input_path)
                   if os.path.isfile(os.path.join(video_input_path, f)) and f.endswith(video_files_extensions)]
os.makedirs(video_output_path, exist_ok=True)

for video_filename in video_filenames:
    print(video_filename)
    video_input_filepath = os.path.join(video_input_path, video_filename)
    video_output_filepath = os.path.join(video_output_path, video_filename)
    video_capture = cv2.VideoCapture(video_input_filepath)

    video_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    video_writer = cv2.VideoWriter(video_output_filepath,
                                   cv2.VideoWriter_fourcc('m', 'p', '4', 'v'),
                                   10,
                                   (video_width, video_height))

    if not video_capture.isOpened():
        print("Error opening video stream or file")

    counter_frame = 0
    while video_capture.isOpened():
        if counter_frame < number_skip_frames:
            counter_frame += 1
            continue
        elif counter_frame > number_skip_frames + number_video_frames:
            break

        frame_flag, frame = video_capture.read()
        if frame_flag:
            video_writer.write(frame)
            counter_frame += 1
        else:
            break

    video_capture.release()
    video_writer.release()
