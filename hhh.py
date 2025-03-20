import streamlit as st
from pytube import YouTube
from pytube.exceptions import VideoUnavailable, PytubeError
import os
import logging
from datetime import datetime
import shutil
import re
import urllib.error

# Configure logging
logging.basicConfig(
    filename='youtube_downloader.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DOWNLOAD_PATH = "downloads"

class YouTubeDownloader:
    def __init__(self):
        self._setup_download_directory()
        self._configure_streamlit()

    def _configure_streamlit(self) -> None:
        st.set_page_config(
            page_title="YouTube Downloader",
            page_icon="🎥",
            layout="wide",
            initial_sidebar_state="expanded"
        )

    def _setup_download_directory(self) -> None:
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)

    def _validate_url(self, url: str) -> bool:
        youtube_regex = r'^(https?://)?(www\.)?(youtube|youtu)\.(com|be)/.+$'
        return bool(re.match(youtube_regex, url))

    def _get_video_info(self, url: str) -> dict:
        try:
            yt = YouTube(url)
            yt.check_availability()
            return {
                "title": yt.title or "Unknown Title",
                "author": yt.author or "Unknown Author",
                "length": f"{yt.length // 60}:{yt.length % 60:02d}",
                "views": f"{yt.views:,}" if yt.views else "Unknown",
                "publish_date": yt.publish_date.strftime("%Y-%m-%d") if yt.publish_date else "Unknown"
            }
        except Exception as e:
            logger.error(f"Error fetching video info: {e}")
            return {}

    def _download_video(self, url: str) -> tuple[bool, str]:
        try:
            yt = YouTube(url)
            yt.check_availability()
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            if stream:
                filename = f"{yt.title[:50]}_{stream.resolution}.mp4".replace('/', '_')
                filepath = os.path.join(DOWNLOAD_PATH, filename)
                stream.download(output_path=DOWNLOAD_PATH, filename=filename)
                return True, filepath
            return False, "No suitable stream found"
        except (VideoUnavailable, PytubeError, urllib.error.HTTPError) as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def run(self) -> None:
        st.title("YouTube Downloader 🎥")
        url = st.text_input("Enter YouTube URL", "")
        if st.button("Analyze Video"):
            if self._validate_url(url):
                with st.spinner("Fetching video info..."):
                    video_info = self._get_video_info(url)
                    if video_info:
                        st.subheader("Video Information")
                        st.write(f"**Title:** {video_info['title']}")
                        st.write(f"**Author:** {video_info['author']}")
                        st.write(f"**Length:** {video_info['length']}")
                        st.write(f"**Views:** {video_info['views']}")
                        st.write(f"**Published:** {video_info['publish_date']}")
                        if st.button("Download Video"):
                            with st.spinner("Downloading..."):
                                success, message = self._download_video(url)
                                if success:
                                    st.success(f"Downloaded successfully: {message}")
                                else:
                                    st.error(message)
            else:
                st.error("Invalid YouTube URL")

if __name__ == "__main__":
    downloader = YouTubeDownloader()
    downloader.run()
