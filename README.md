# README

## Project Overview

This Python API facilitates downloading videos, detecting scenes, and identifying hands within the videos (create folder "**vedio_download**" to save vedio and in this folder create another folder **frame** to save multiple frames). It's built using FastAPI, PyTube, OpenCV, scenedetect, and cvzone.

## Key Features

Downloads videos from YouTube URLs or directly from uploaded video files.
Detects scenes within the videos.
Extracts frames at the start of each detected scene.
Detects hands in the extracted frames and provides their coordinates.
Encodes the modified frames (with hand annotations) to base64 for visualization.
## Endpoints

/download_youtube (POST):
Accepts either a url parameter for a YouTube video or a video_file parameter for an uploaded video file.
Downloads the video (if needed) and processes its frames asynchronously.
Returns a JSON response containing the detected hand coordinates and base64-encoded modified images for each scene's starting frame.
## Usage

Install required libraries: pip install -r requirements.txt
Run the API: uvicorn app:app --reload
Send a POST request to /download_youtube with either a url or video_file parameter.
## Example Request

Bash
curl -X POST http://127.0.0.1:8000/download_youtube -F url=https://www.youtube.com/watch?v=exampleVideo

## Output

The API returns a JSON response like:

JSON
```
{
    "result": [
        {
            "hand_coordinates": [
                {
                    "x": 100,
                    "y": 50,
                    "width": 300,
                    "height": 200
                }
            ],
            "encoded_image": "base64-encoded-image-data"
        },
        
    ]
}
```

## Additional Notes

The API attempts to delete processed video files after 5 minutes to conserve storage space.
