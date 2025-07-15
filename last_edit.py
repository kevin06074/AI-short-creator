# Import the os and cv2 modules
import os
import cv2

# Define the file path using relative paths
caption_root_file = os.path.join("caption", "src", "Root.tsx")
video_file = os.path.join("output", "best_video_2.mp4")

# Check if files exist before processing
if not os.path.exists(caption_root_file):
    print(f"Error: Caption file not found at {caption_root_file}")
    exit(1)

if not os.path.exists(video_file):
    print(f"Error: Video file not found at {video_file}")
    exit(1)

try:
    # Open the file in the output directory with the given file name and extension in read mode
    with open(caption_root_file, "r") as f:
        # Read the text from the file
        text = f.read()

    # Create a video object using cv2.VideoCapture and the video file name
    video = cv2.VideoCapture(video_file)

    if not video.isOpened():
        print(f"Error: Could not open video file {video_file}")
        exit(1)

    # Get the frame rate or frames per second of the video
    frame_rate = video.get(cv2.CAP_PROP_FPS)

    # Get the total number of frames in the video
    total_num_frames = video.get(cv2.CAP_PROP_FRAME_COUNT)

    # Release the video object
    video.release()

    if frame_rate <= 0 or total_num_frames <= 0:
        print("Error: Could not get valid video properties")
        exit(1)

    # Calculate the duration of the video in seconds by dividing the total number of frames by the frame rate
    duration = total_num_frames / frame_rate

    # Round the duration to the nearest integer
    duration = round(duration)

    # Replace the durationInSeconds value in the text with the calculated duration
    # Use a more flexible replacement pattern
    import re
    pattern = r'durationInSeconds:\s*\d+'
    replacement = f'durationInSeconds: {duration}'
    text = re.sub(pattern, replacement, text)

    # Open the file in write mode and update it
    with open(caption_root_file, "w") as f:
        # Write the updated text to the file
        f.write(text)

    # Print a message to indicate the file has been updated
    print(f"File {caption_root_file} has been updated with the duration of {duration} seconds.")

except Exception as e:
    print(f"Error processing files: {e}")
