import os
import cv2
import gc
import numpy as np
from mtcnn import MTCNN
from tqdm import tqdm
from moviepy.editor import VideoFileClip
from concurrent.futures import ProcessPoolExecutor
from moviepy.editor import AudioClip

# Constants
INPUT_DIR = 'Clips'
OUTPUT_DIR = 'output'
FACE_DETECTION_FREQUENCY = 7  # Change this to reduce the frequency of face detection
RESIZE_RATIO = 0.25  # Change this to adjust the resize ratio for face detection
N_WORKERS = 4  # Change this to adjust the number of worker processes
MOVEMENT_SPEED = 0.06  # Change this to adjust the movement speed (lower value means slower movement)
SMOOTHING_FACTOR = 0.3  # Change this to adjust the smoothing factor for camera movement
PREDICTION_WEIGHT = 0.5  # Change this to adjust the weight for face position prediction
QUICK_MOVE_THRESHOLD = 10  # Adjust this threshold based on your preference
FACE_DISTANCE_THRESHOLD = 10  # Adjust this threshold based on your preference
# Make sure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def process_video(file):
    # Initialize variables
    video = None
    output_video = None
    audio_subclip = None
    final_audio = None
    out = None
    temp_output_file_path = None
    
    try:
        # Initialize the face detector
        detector = MTCNN()

        # Open the video file
        video = VideoFileClip(os.path.join(INPUT_DIR, file))

        # Get the video properties
        fps = video.fps
        height = video.size[1]
        total_frames = video.reader.nframes
        video_duration = total_frames / fps

        # Initialize variables
        box = None
        next_box = None
        frames_since_detection = 0
        last_detected_box = None
        smoothed_move_x = 0
        smoothed_move_y = 0
        quick_move_frames = 0

        # Create a VideoWriter for the output video
        temp_output_file_path = os.path.join(OUTPUT_DIR, f'temp_best_{file}')
        out = cv2.VideoWriter(temp_output_file_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (int(height * 9 / 16), int(height)))

        # Process each frame
        for i, frame in enumerate(video.iter_frames()):
            # Detect the face in the frame every N frames
            if i % FACE_DETECTION_FREQUENCY == 0 or next_box is None:
                small_frame = cv2.resize(frame, (0, 0), fx=RESIZE_RATIO, fy=RESIZE_RATIO)
                result = detector.detect_faces(small_frame)

                # If a face was detected, store the bounding box
                if result:
                    next_box = [coord / RESIZE_RATIO for coord in result[0]['box']]
                    frames_since_detection = 0
                    last_detected_box = next_box
                    quick_move_frames = 0
                else:
                    next_box = None
                    quick_move_frames += 1

            # If a face was detected in a previous frame, crop the frame around the face
            if next_box is not None:
                if box is None or quick_move_frames > QUICK_MOVE_THRESHOLD:
                    box = next_box
                    quick_move_frames = 0

                # Interpolate the bounding box coordinates
                ratio = frames_since_detection / FACE_DETECTION_FREQUENCY
                interpolated_box = np.array(box) * (1 - ratio) + np.array(next_box) * ratio

                # Predict the next face position based on the motion trend
                if last_detected_box is not None:
                    predicted_box = np.array(last_detected_box) + PREDICTION_WEIGHT * (np.array(next_box) - np.array(last_detected_box))
                    x, y, w, h = predicted_box.astype(int)
                else:
                    x, y, w, h = interpolated_box.astype(int)

                # Calculate the crop coordinates
                center_x = x + w // 2
                center_y = y + h // 2

                # Slow down the movement
                move_x = int((center_x - int(height * 9 / 32)) * MOVEMENT_SPEED)
                move_y = int((center_y - int(height / 2)) * MOVEMENT_SPEED)

                # Smooth the movement using a weighted average
                smoothed_move_x = SMOOTHING_FACTOR * smoothed_move_x + (1 - SMOOTHING_FACTOR) * move_x
                smoothed_move_y = SMOOTHING_FACTOR * smoothed_move_y + (1 - SMOOTHING_FACTOR) * move_y

                # Calculate the crop coordinates with smoother movement
                crop_x = max(0, center_x - int(height * 9 / 32) - int(smoothed_move_x))
                crop_y = max(0, center_y - int(height / 2) - int(smoothed_move_y))

                # Ensure crop dimensions don't exceed frame boundaries
                crop_x = min(crop_x, frame.shape[1] - int(height * 9 / 16))
                crop_y = min(crop_y, frame.shape[0] - int(height))
                
                # Crop the frame
                cropped = frame[crop_y:crop_y + int(height), crop_x:crop_x + int(height * 9 / 16)]

                # Resize the cropped frame to the desired resolution
                if cropped.size > 0:  # Ensure cropped frame is not empty
                    resized = cv2.resize(cropped, (int(height * 9 / 16), int(height)))
                    # Write the frame to the output video
                    out.write(cv2.cvtColor(resized, cv2.COLOR_RGB2BGR))

                frames_since_detection += 1
                box = next_box

        # Release the video writer
        if out is not None:
            out.release()
            out = None

        # Load the processed video
        output_video = VideoFileClip(temp_output_file_path)

        # Limit the output video to 58 seconds
        output_video = output_video.subclip(0, min(58, output_video.duration))

        # Handle audio properly with resource management
        try:
            # Use a subclip of the original audio if available
            if video.audio is not None:
                audio_subclip = video.audio.subclip(0, min(58, video.audio.duration))
                # Create a new audio clip with duration set explicitly
                final_audio = AudioClip(lambda t: audio_subclip.get_frame(t), duration=output_video.duration)
                # Set the audio of the output video
                output_video.audio = final_audio
            else:
                # If no audio is available, create an empty audio clip
                final_audio = AudioClip(lambda t: 0, duration=output_video.duration)
                output_video.audio = final_audio

            # Write the final video with the original audio
            output_video.write_videofile(os.path.join(OUTPUT_DIR, f'best_{file}'), codec='libx264', audio_codec='aac')
            
        except Exception as audio_error:
            print(f"Error processing audio for {file}: {audio_error}")
            # Save video without audio as fallback
            output_video.write_videofile(os.path.join(OUTPUT_DIR, f'best_{file}'), codec='libx264')

    except Exception as e:
        print(f"Error processing video {file}: {e}")
        
    finally:
        # Ensure all resources are properly cleaned up
        try:
            if out is not None:
                out.release()
        except:
            pass
            
        try:
            if final_audio is not None:
                final_audio.close()
        except:
            pass
            
        try:
            if audio_subclip is not None:
                audio_subclip.close()
        except:
            pass
            
        try:
            if output_video is not None:
                output_video.close()
        except:
            pass
            
        try:
            if video is not None:
                video.close()
        except:
            pass
            
        # Clean up temporary files
        try:
            if temp_output_file_path and os.path.exists(temp_output_file_path):
                os.remove(temp_output_file_path)
        except OSError:
            pass

        # Force garbage collection
        gc.collect()

def subtitle(file):
    pass

def main():
    # Get the video files
    files = [file for file in os.listdir(INPUT_DIR) if file.endswith(('.mp4', '.avi', '.mov'))]

    if not files:
        print(f"No video files found in {INPUT_DIR}")
        return

    # Create a progress bar
    pbar = tqdm(total=len(files), desc='Processing videos', unit='video')

    try:
        # Process the videos concurrently
        with ProcessPoolExecutor(max_workers=N_WORKERS) as executor:
            for _ in executor.map(process_video, files):
                # Update the progress bar
                pbar.update()
    finally:
        # Close the progress bar
        pbar.close()

if __name__ == '__main__':
    main()
