#!/usr/bin/env python3
"""
InstaTranscriber - A tool to download and transcribe Instagram and TikTok videos
"""

import os
import sys
import tempfile
import validators
import warnings
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import yt_dlp
import whisper
from moviepy import VideoFileClip
from colorama import init, Fore, Style
from tqdm import tqdm

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning, module="whisper")
warnings.filterwarnings("ignore", category=FutureWarning, module="whisper")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")

# Initialize colorama for cross-platform colored output
init()

class InstaTranscriber:
    def __init__(self, output_dir: str = "transcriptions"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir = tempfile.mkdtemp()
        
        # Load Whisper model (using base model for good balance of speed/accuracy)
        print(f"{Fore.YELLOW}Loading Whisper model...{Style.RESET_ALL}")
        
        # Suppress Whisper loading messages
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.whisper_model = whisper.load_model("base")
        
        print(f"{Fore.GREEN}Whisper model loaded successfully!{Style.RESET_ALL}")
    
    def is_valid_url(self, url: str) -> bool:
        """Check if the URL is valid and from supported platforms"""
        if not validators.url(url):
            return False
        
        supported_domains = [
            'instagram.com', 'www.instagram.com',
            'tiktok.com', 'www.tiktok.com', 'vm.tiktok.com'
        ]
        
        return any(domain in url.lower() for domain in supported_domains)
    
    def download_video(self, url: str) -> Optional[str]:
        """Download video from URL and return the path to the downloaded file"""
        try:
            # Configure yt-dlp options with more flexible format selection
            ydl_opts = {
                'outtmpl': os.path.join(self.temp_dir, '%(title)s.%(ext)s'),
                'format': 'best[height<=720]/best/worst',  # More flexible format selection
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"{Fore.BLUE}Downloading video from: {url}{Style.RESET_ALL}")
                
                try:
                    # Get video info first
                    info = ydl.extract_info(url, download=False)
                    video_title = info.get('title', 'Unknown')
                    
                    # Download the video
                    ydl.download([url])
                    
                    # Find the downloaded file
                    for file in os.listdir(self.temp_dir):
                        if file.endswith(('.mp4', '.webm', '.mkv', '.avi', '.m4a', '.mp3')):
                            video_path = os.path.join(self.temp_dir, file)
                            print(f"{Fore.GREEN}Downloaded: {video_title}{Style.RESET_ALL}")
                            return video_path
                    
                    return None
                    
                except yt_dlp.DownloadError as e:
                    # Try with even more permissive settings
                    print(f"{Fore.YELLOW}Retrying with alternative format...{Style.RESET_ALL}")
                    
                    ydl_opts_fallback = {
                        'outtmpl': os.path.join(self.temp_dir, '%(title)s.%(ext)s'),
                        'format': 'worst',  # Try worst quality as fallback
                        'quiet': True,
                        'no_warnings': True,
                        'extract_flat': False,
                        'ignoreerrors': True,
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl_fallback:
                        ydl_fallback.download([url])
                        
                        # Find the downloaded file
                        for file in os.listdir(self.temp_dir):
                            if file.endswith(('.mp4', '.webm', '.mkv', '.avi', '.m4a', '.mp3')):
                                video_path = os.path.join(self.temp_dir, file)
                                print(f"{Fore.GREEN}Downloaded: {video_title} (fallback quality){Style.RESET_ALL}")
                                return video_path
                    
                    raise e
                
        except Exception as e:
            print(f"{Fore.RED}Error downloading video: {str(e)}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Note: Some Instagram content may be restricted or require login.{Style.RESET_ALL}")
            return None
    
    def extract_audio(self, video_path: str) -> Optional[str]:
        """Extract audio from video file"""
        try:
            print(f"{Fore.BLUE}Extracting audio...{Style.RESET_ALL}")
            
            # Check if the file is already audio-only
            if video_path.endswith(('.m4a', '.mp3', '.wav', '.aac')):
                print(f"{Fore.GREEN}File is already audio format, using directly!{Style.RESET_ALL}")
                return video_path
            
            # Load video and extract audio
            video = VideoFileClip(video_path)
            
            # Check if video has audio
            if video.audio is None:
                print(f"{Fore.RED}Video has no audio track!{Style.RESET_ALL}")
                video.close()
                return None
            
            audio_path = video_path.replace('.mp4', '.wav').replace('.webm', '.wav').replace('.mkv', '.wav').replace('.avi', '.wav')
            
            # Extract audio as WAV file with minimal parameters for maximum compatibility
            try:
                # Try with logger parameter first
                video.audio.write_audiofile(audio_path, logger=None)
            except TypeError:
                # Fallback for older MoviePy versions
                video.audio.write_audiofile(audio_path)
            
            video.close()
            
            print(f"{Fore.GREEN}Audio extracted successfully!{Style.RESET_ALL}")
            return audio_path
            
        except Exception as e:
            print(f"{Fore.RED}Error extracting audio: {str(e)}{Style.RESET_ALL}")
            return None
    
    def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Transcribe audio file to text using Whisper"""
        try:
            print(f"{Fore.BLUE}Transcribing audio...{Style.RESET_ALL}")
            
            # Transcribe using Whisper with warning suppression
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = self.whisper_model.transcribe(audio_path)
            
            transcription = result["text"].strip()
            
            print(f"{Fore.GREEN}Transcription completed!{Style.RESET_ALL}")
            return transcription
            
        except Exception as e:
            print(f"{Fore.RED}Error transcribing audio: {str(e)}{Style.RESET_ALL}")
            return None
    
    def save_transcription(self, transcription: str, url: str) -> str:
        """Save transcription to a text file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a safe filename from URL
        safe_url = url.replace('https://', '').replace('http://', '')
        safe_url = ''.join(c for c in safe_url if c.isalnum() or c in '._-')[:50]
        
        filename = f"transcription_{timestamp}_{safe_url}.txt"
        filepath = self.output_dir / filename
        
        # Write transcription with metadata
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Transcription from: {url}\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 50 + "\n\n")
            f.write(transcription)
        
        return str(filepath)
    
    def troubleshoot_url(self, url: str) -> None:
        """Provide troubleshooting information for a URL"""
        print(f"\n{Fore.CYAN}🔍 Troubleshooting URL: {url}{Style.RESET_ALL}")
        
        try:
            # Try to get basic info without downloading
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info:
                    print(f"{Fore.GREEN}✅ URL is accessible{Style.RESET_ALL}")
                    print(f"Title: {info.get('title', 'Unknown')}")
                    print(f"Duration: {info.get('duration', 'Unknown')} seconds")
                    
                    # Check available formats
                    ydl_opts_formats = {'listformats': True, 'quiet': False}
                    print(f"\n{Fore.YELLOW}Available formats:{Style.RESET_ALL}")
                    with yt_dlp.YoutubeDL(ydl_opts_formats) as ydl_formats:
                        try:
                            ydl_formats.extract_info(url, download=False)
                        except:
                            print("Could not list formats")
                else:
                    print(f"{Fore.RED}❌ Could not access URL{Style.RESET_ALL}")
                    
        except Exception as e:
            print(f"{Fore.RED}❌ Error accessing URL: {str(e)}{Style.RESET_ALL}")
            
            # Provide specific suggestions based on the URL
            if 'instagram.com' in url.lower():
                print(f"\n{Fore.YELLOW}Instagram troubleshooting tips:{Style.RESET_ALL}")
                print("• Make sure the post/reel is public")
                print("• Try copying the URL directly from the browser")
                print("• Some Instagram content may require login")
                print("• Stories are only available for 24 hours")
            elif 'tiktok.com' in url.lower():
                print(f"\n{Fore.YELLOW}TikTok troubleshooting tips:{Style.RESET_ALL}")
                print("• Make sure the video is public")
                print("• Try using the full URL instead of short links")
                print("• Some regions may have restrictions")

    def process_url(self, url: str) -> bool:
        """Process a single URL: download, transcribe, and save"""
        print(f"\n{Fore.CYAN}Processing: {url}{Style.RESET_ALL}")
        
        if not self.is_valid_url(url):
            print(f"{Fore.RED}Invalid URL or unsupported platform: {url}{Style.RESET_ALL}")
            return False
        
        video_path = None
        audio_path = None
        
        try:
            # Download video
            video_path = self.download_video(url)
            if not video_path:
                # Provide troubleshooting information
                self.troubleshoot_url(url)
                return False
            
            # Extract audio
            audio_path = self.extract_audio(video_path)
            if not audio_path:
                return False
            
            # Transcribe audio
            transcription = self.transcribe_audio(audio_path)
            if not transcription:
                return False
            
            # Save transcription
            output_file = self.save_transcription(transcription, url)
            print(f"{Fore.GREEN}Transcription saved to: {output_file}{Style.RESET_ALL}")
            
            # Preview transcription
            print(f"\n{Fore.YELLOW}Preview:{Style.RESET_ALL}")
            preview = transcription[:200] + "..." if len(transcription) > 200 else transcription
            print(f"{Fore.WHITE}{preview}{Style.RESET_ALL}")
            
            return True
            
        finally:
            # Clean up temporary files (video and audio)
            temp_files_to_clean = []
            
            if video_path and os.path.exists(video_path):
                temp_files_to_clean.append(video_path)
            
            if audio_path and os.path.exists(audio_path):
                temp_files_to_clean.append(audio_path)
            
            # Also clean up any other files in temp directory
            if os.path.exists(self.temp_dir):
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    if os.path.isfile(file_path):
                        temp_files_to_clean.append(file_path)
            
            # Remove all temporary files
            for temp_file in temp_files_to_clean:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        print(f"{Fore.BLUE}🗑️ Cleaned up: {os.path.basename(temp_file)}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}⚠️ Could not remove {temp_file}: {e}{Style.RESET_ALL}")

    def process_urls(self, urls: List[str]) -> None:
        """Process multiple URLs"""
        successful = 0
        total = len(urls)
        
        print(f"\n{Fore.CYAN}Starting transcription of {total} video(s)...{Style.RESET_ALL}")
        
        for i, url in enumerate(urls, 1):
            print(f"\n{Fore.MAGENTA}[{i}/{total}]{Style.RESET_ALL}")
            if self.process_url(url):
                successful += 1
        
        print(f"\n{Fore.GREEN}Completed! {successful}/{total} videos transcribed successfully.{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Transcriptions saved in: {self.output_dir}{Style.RESET_ALL}")
    
    def cleanup(self):
        """Clean up temporary directory and all its contents"""
        import shutil
        try:
            if os.path.exists(self.temp_dir):
                # Remove all files in temp directory
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"{Fore.YELLOW}⚠️ Could not remove {file_path}: {e}{Style.RESET_ALL}")
                
                # Remove the temp directory itself
                try:
                    os.rmdir(self.temp_dir)
                    print(f"{Fore.BLUE}🗑️ Cleaned up temporary directory{Style.RESET_ALL}")
                except:
                    # Directory might not be empty, try force removal
                    shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Error during cleanup: {e}{Style.RESET_ALL}")

def main():
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}🎥 InstaScribe - Video Transcription Tool 🎥")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Supports Instagram and TikTok videos{Style.RESET_ALL}\n")
    
    transcriber = InstaTranscriber()
    
    try:
        urls = []
        
        print(f"{Fore.GREEN}Enter video URLs (one per line, press Enter twice when done):{Style.RESET_ALL}")
        
        while True:
            url = input(f"{Fore.WHITE}URL: {Style.RESET_ALL}").strip()
            
            if not url:
                if urls:
                    break
                else:
                    print(f"{Fore.YELLOW}Please enter at least one URL.{Style.RESET_ALL}")
                    continue
            
            urls.append(url)
            print(f"{Fore.GREEN}✓ Added: {url}{Style.RESET_ALL}")
        
        if urls:
            transcriber.process_urls(urls)
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operation cancelled by user.{Style.RESET_ALL}")
    
    except Exception as e:
        print(f"\n{Fore.RED}An error occurred: {str(e)}{Style.RESET_ALL}")
    
    finally:
        transcriber.cleanup()

if __name__ == "__main__":
    main() 