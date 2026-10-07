import os
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from yt_dlp import YoutubeDL
from moviepy.editor import VideoFileClip, concatenate_videoclips

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RenderRequest(BaseModel):
    url: str
    scenes: list

@app.get("/")
def home():
    return {"status": "online", "message": "YouTube Recap Engine is Running 24/7!"}

@app.post("/render")
def render_video(req: RenderRequest):
    video_url = req.url
    scenes = req.scenes
    
    if not video_url or not scenes:
        raise HTTPException(status_code=400, detail="URL and scenes are required")

    timestamp = int(time.time())
    source_file = f"source_{timestamp}.mp4"
    output_file = f"recap_{timestamp}.mp4"

    try:
        ydl_opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            'outtmpl': source_file,
            'merge_output_format': 'mp4'
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        main_video = VideoFileClip(source_file)
        clips = []
        for s in scenes:
            start_t = float(s['start'])
            end_t = float(s['end'])
            if end_t > main_video.duration:
                end_t = main_video.duration
            if start_t < end_t:
                clips.append(main_video.subclip(start_t, end_t))

        if not clips:
            raise Exception("No valid clips could be extracted")

        final_video = concatenate_videoclips(clips)
        final_video.write_videofile(output_file, codec="libx264", audio_codec="aac")

        main_video.close()
        final_video.close()

        if os.path.exists(source_file):
            os.remove(source_file)

        return FileResponse(
            output_file, 
            media_type="video/mp4", 
            filename="youtube_recap.mp4"
        )

    except Exception as e:
        if os.path.exists(source_file): os.remove(source_file)
        if os.path.exists(output_file): os.remove(output_file)
        raise HTTPException(status_code=500, detail=str(e))
