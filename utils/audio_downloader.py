import os
import yt_dlp


class AudioDownloader:

    def __init__(self, output_dir: str = "data/audio"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def download_youtube_audio(self, url: str, alarm_id: str) -> str:
        out_path = os.path.join(self.output_dir, f"{alarm_id}.mp3")

        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": os.path.join(self.output_dir, f"{alarm_id}.%(ext)s"),
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return out_path