from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from pytube import YouTube
import os
import cv2 as cv
from scenedetect import open_video, SceneManager, ContentDetector
from cvzone import HandTrackingModule
import base64
import asyncio
import asyncio
import time
from fastapi import BackgroundTasks
app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_dynamic_path(*path_parts):
    return os.path.join(BASE_DIR, *path_parts)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

def download_youtube_video(url, download_path):
    try:
        full_download_path = get_dynamic_path(download_path)
        if not os.path.exists(full_download_path):
            os.makedirs(full_download_path)

        yt = YouTube(url)
        stream = yt.streams.get_highest_resolution()
        downloaded_file = os.path.join(full_download_path, stream.default_filename)
        stream.download(output_path=full_download_path)
        return downloaded_file
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading video: {e}")

async def detect_hands_async(detector, image_path, count):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: detect_hands(detector, image_path, count))

def detect_hands(detector, image_path, count):
    img = cv.imread(image_path)
    os.remove(image_path)
    hands_data = []

    if img is not None:
        hands, img = detector.findHands(img)
        if hands:
            for hand in hands:
                bbox = hand['bbox']
                x, y, w, h = bbox
                cv.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                landmarks = hand['lmList']
                
                hand_data = {
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                }

                hands_data.append(hand_data)

            # output_path = get_dynamic_path('download_vedio_youtube', 'vedio_download', 'frame', f'example_new_{count}.jpg')
            output_path = get_dynamic_path( 'vedio_download', 'frame', f'example_new_{count}.jpg')
            cv.imwrite(output_path, img)
            
            # Encode the image to base64
            encoded_image = encode_image(output_path)

            print(f"Modified image saved to {output_path}")

            # Return the response as JSON
            response_data = {
                'hand_coordinates': hands_data,
                'encoded_image': encoded_image
            }
            return response_data

    else:
        return {'error': 'Failed to process the image'}

async def process_frames_async(video_path, frame_info_list, output_directory, hand_detector):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: process_frames(video_path, frame_info_list, output_directory, hand_detector))

def process_frames(video_path, frame_info_list, output_directory, hand_detector):
    cap = cv.VideoCapture(video_path)

    if not cap.isOpened():
        raise HTTPException(status_code=500, detail="Error opening video file")

    full_output_directory = get_dynamic_path(output_directory)
    os.makedirs(full_output_directory, exist_ok=True)

    frame_results = []

    try:
        for count, frame_info in enumerate(frame_info_list):
            start_frame = frame_info['start_frame']

            cap.set(cv.CAP_PROP_POS_FRAMES, start_frame)

            ret, frame = cap.read()

            if not ret:
                print(f"Error reading frame {start_frame}. Trying to re-open the video file.")
                raise HTTPException(status_code=500, detail=f"Error reading frame {start_frame}")

            thumbnail_name = os.path.join(full_output_directory, f"thumb_nail_{count}.jpg")
            print(f"Saving image to: {thumbnail_name}")
            print(frame.shape)
            p = cv.imwrite(thumbnail_name, frame)
            print(f"Saved: {p}")

            if not p:
                print(f"Error writing image to {thumbnail_name}")

            # Detect hands and save modified image
            result = detect_hands(hand_detector, thumbnail_name, count)
            if result:
                frame_results.append(result)

    finally:
        # Release the video file before attempting to remove it
        cap.release()
        time.sleep(1)
        # os.remove(video_path) 
    return frame_results

@app.post('/download_youtube')
async def download_youtube( background_tasks: BackgroundTasks,url: str = Form(None), video_file: UploadFile = File(None)):
    try:
        if url is not None and video_file is not None:
            raise HTTPException(status_code=400, detail="Provide only one of 'url' or 'video_file'")
        elif url is None and video_file is None:
            raise HTTPException(status_code=400, detail="Provide either 'url' or 'video_file'")

        if url is not None:
            download_path = get_dynamic_path( 'vedio_download')
            video_path = download_youtube_video(url, download_path)
            print('vedio saved1')

        elif video_file is not None:
            # Save the uploaded video file
            video_path = get_dynamic_path('vedio_download', video_file.filename)
            with open(video_path, 'wb') as video_file_dest:
                video_file_dest.write(video_file.file.read())
                print('vedio saved')
        video = open_video(video_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector())
        scene_manager.detect_scenes(video)
        scenes = scene_manager.get_scene_list()
        
        frame_info_list = []
        for start_time_code, end_time_code in scenes:
            start_frame = int(start_time_code.get_frames())
            end_frame = int(end_time_code.get_frames())

            frame_info = {
                "start_frame": start_frame,
                "end_frame": end_frame
            }

            frame_info_list.append(frame_info)
        hand_detector = HandTrackingModule.HandDetector()
        output_directory = get_dynamic_path( 'vedio_download', 'frame')
        ''' Use async function to process frames concurrently'''
        results = await process_frames_async(video_path, frame_info_list, output_directory, hand_detector)
      
        ''' Attempt to remove the video file after processing frames'''
        
        async def delete_video(video_path):
            try:
                await asyncio.sleep(300)  # 5 minutes (300 seconds) delay
                if os.path.exists(video_path):
                    os.remove(video_path)
                    print(f"Video file removed: {video_path}")
                else:
                    print(f"Video file not found: {video_path}")
            except Exception as e:
                print(f"Error removing video file: {e}")
        # Schedule the background task to delete the video file
        background_tasks.add_task(delete_video, video_path)
        return {'result':results}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing video frames: {e}")