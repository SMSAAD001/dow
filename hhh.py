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
        try:
            os.makedirs(DOWNLOAD_PATH, exist_ok=True)
            logger.debug(f"Download directory ensured: {DOWNLOAD_PATH}")
        except OSError as e:
            logger.error(f"Failed to create download directory: {e}")
            st.error("Failed to initialize download directory")

    def _clean_url(self, url: str) -> str:
        """Remove query parameters from URL"""
        match = re.match(r'(https?://(?:www\.)?(?:youtube|youtu)\.(?:com|be)/(?:watch\?v=)?[A-Za-z0-9_-]{11})', url)
        clean_url = match.group(1) if match else url
        logger.debug(f"Cleaned URL: {clean_url}")
        return clean_url

    def _validate_url(self, url: str) -> bool:
        youtube_regex = (
            r'(https?://)?(www\.)?'
            '(youtube|youtu)\.(com|be)/'
            '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
        valid = bool(re.match(youtube_regex, url))
        logger.debug(f"URL validation result for {url}: {valid}")
        return valid

    def _get_video_info(self, url: str) -> dict:
        try:
            clean_url = self._clean_url(url)
            yt = YouTube(clean_url)
            yt.check_availability()
            info = {
                "title": yt.title or "Unknown Title",
                "author": yt.author or "Unknown Author",
                "length": f"{yt.length // 60}:{yt.length % 60:02d}" if yt.length else "Unknown",
                "views": f"{yt.views:,}" if yt.views else "Unknown",
                "publish_date": yt.publish_date.strftime("%Y-%m-%d") if yt.publish_date else "Unknown"
            }
            logger.info(f"Successfully retrieved info for: {info['title']}")
            return info
        except Exception as e:
            logger.debug(f"Metadata retrieval failed: {str(e)}", exc_info=True)
            st.session_state.debug_info = f"Metadata retrieval error: {str(e)}"
            return {
                "title": "Error retrieving info",
                "author": "N/A",
                "length": "N/A",
                "views": "N/A",
                "publish_date": "N/A"
            }

    def _download_video(self, url: str) -> tuple[bool, str]:
        try:
            clean_url = self._clean_url(url)
            yt = YouTube(clean_url)
            yt.check_availability()
            
            # Get highest available progressive stream
            stream = yt.streams.filter(
                file_extension='mp4',
                progressive=True
            ).order_by('resolution').desc().first()

            if stream:
                title = yt.title if yt.title else f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                actual_resolution = stream.resolution if stream.resolution else "unknown"
                filename = f"{title[:50]}_{actual_resolution}.mp4".replace('/', '_').replace('\\', '_')
                filepath = os.path.join(DOWNLOAD_PATH, filename)
                stream.download(output_path=DOWNLOAD_PATH, filename=filename)
                logger.info(f"Download successful: {filepath} (Resolution: {actual_resolution})")
                return True, filepath
            return False, "No suitable stream found"

        except VideoUnavailable:
            logger.error("Video is unavailable or restricted")
            return False, "Video is unavailable or restricted"
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP Error {e.code}: {e.reason}")
            return False, f"HTTP Error {e.code}: {e.reason}"
        except PytubeError as e:
            logger.error(f"Pytube error: {str(e)}")
            return False, f"Pytube error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected download error: {str(e)}", exc_info=True)
            return False, f"Unexpected error: {str(e)}"

    def run(self) -> None:
        st.title("YouTube Downloader 🎥")
        
        with st.sidebar:
            st.header("Options")
            clear_downloads = st.button("Clear Downloads")
            show_debug = st.checkbox("Show Debug Info")

        col1, col2 = st.columns([2, 1])
        
        with col1:
            url = st.text_input("Enter YouTube URL", "")
            
        with col2:
            st.write("")  # Spacer
            analyze_button = st.button("Analyze Video", use_container_width=True)

        if clear_downloads:
            try:
                shutil.rmtree(DOWNLOAD_PATH)
                self._setup_download_directory()
                st.success("Download folder cleared!")
                logger.info("Download folder cleared by user")
            except Exception as e:
                st.error(f"Failed to clear downloads: {e}")
                logger.error(f"Failed to clear downloads: {e}")

        if url and analyze_button:
            if self._validate_url(url):
                with st.spinner("Analyzing video..."):
                    video_info = self._get_video_info(url)
                    
                    st.subheader("Video Information")
                    info_container = st.container()
                    with info_container:
                        st.write(f"**Title:** {video_info['title']}")
                        st.write(f"**Author:** {video_info['author']}")
                        st.write(f"**Length:** {video_info['length']}")
                        st.write(f"**Views:** {video_info['views']}")
                        st.write(f"**Published:** {video_info['publish_date']}")

                    if show_debug and "debug_info" in st.session_state:
                        st.warning(f"Debug: {st.session_state.debug_info}")

                    force_download = st.checkbox("Force download (if metadata unavailable)")
                    if st.button("Download Now", key="download_now"):
                        with st.spinner("Downloading highest available quality..."):
                            success, message = self._download_video(url)
                            if success:
                                st.success(f"Downloaded successfully to: {message}")
                                logger.info(f"Video downloaded: {video_info['title']}")
                            else:
                                st.error(message)
                                logger.error(f"Download failed: {message}")
            else:
                st.error("Please enter a valid YouTube URL")
                logger.warning(f"Invalid URL entered: {url}")

        st.markdown("---")
        st.markdown("""
        *Note: Please ensure you have permission to download videos and respect copyright laws.*
        *Downloads the highest available quality automatically. If metadata fails, try force download.*
        """)

if __name__ == "__main__":
    downloader = YouTubeDownloader()
    downloader.run()
