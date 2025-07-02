#!/usr/bin/env python3
"""
CSV Profile Transcriber - Transcribe Instagram posts from CSV data

This tool reads Instagram post data from CSV files (exported from browser extensions)
and transcribes the top-performing posts based on engagement metrics.
"""

import os
import csv
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from colorama import init, Fore, Style
from insta_transcriber import InstaTranscriber

# Initialize colorama
init()

class CSVProfileTranscriber:
    def __init__(self, output_dir: str = "csv_profile_transcriptions"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.transcriber = InstaTranscriber(output_dir=str(self.output_dir))
    
    def read_csv_data(self, csv_file: str) -> List[Dict]:
        """Read Instagram post data from CSV file"""
        print(f"{Fore.CYAN}Reading CSV file: {csv_file}{Style.RESET_ALL}")
        
        try:
            # Try to read with pandas first for better handling
            df = pd.read_csv(csv_file)
            
            # Convert to list of dictionaries
            posts = df.to_dict('records')
            
            print(f"{Fore.GREEN}✓ Successfully read {len(posts)} posts from CSV{Style.RESET_ALL}")
            
            # Show column names for reference
            print(f"{Fore.YELLOW}Available columns: {list(df.columns)}{Style.RESET_ALL}")
            
            return posts
            
        except Exception as e:
            print(f"{Fore.RED}✗ Error reading CSV file: {str(e)}{Style.RESET_ALL}")
            
            # Fallback to basic CSV reader
            try:
                posts = []
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    posts = list(reader)
                
                print(f"{Fore.GREEN}✓ Fallback read successful: {len(posts)} posts{Style.RESET_ALL}")
                return posts
                
            except Exception as e2:
                print(f"{Fore.RED}✗ Fallback also failed: {str(e2)}{Style.RESET_ALL}")
                return []
    
    def normalize_column_names(self, posts: List[Dict]) -> List[Dict]:
        """Normalize column names to standard format"""
        if not posts:
            return posts
        
        # Common column name mappings
        column_mappings = {
            'reel': 'url',
            'post_url': 'url',
            'link': 'url',
            'views': 'view_count',
            'view_count': 'view_count',
            'likes': 'like_count',
            'like_count': 'like_count',
            'comments': 'comment_count',
            'comment_count': 'comment_count',
            'profile': 'profile_name',
            'username': 'profile_name',
            'account': 'profile_name'
        }
        
        normalized_posts = []
        for post in posts:
            normalized_post = {}
            
            for key, value in post.items():
                # Normalize key name
                normalized_key = column_mappings.get(key.lower(), key.lower())
                normalized_post[normalized_key] = value
            
            normalized_posts.append(normalized_post)
        
        return normalized_posts
    
    def filter_video_posts(self, posts: List[Dict]) -> List[Dict]:
        """Filter to only include video posts (Reels and video posts)"""
        video_posts = []
        
        for post in posts:
            url = post.get('url', '')
            
            # Check if it's a video post (Reel or video post)
            if '/reel/' in url or '/p/' in url:
                # Additional check: if it has view count, it's likely a video
                view_count = post.get('view_count', 0)
                if isinstance(view_count, str):
                    try:
                        view_count = int(view_count.replace(',', ''))
                    except:
                        view_count = 0
                
                if view_count > 0 or '/reel/' in url:
                    video_posts.append(post)
        
        print(f"{Fore.GREEN}✓ Filtered to {len(video_posts)} video posts{Style.RESET_ALL}")
        return video_posts
    
    def filter_non_pinned_posts(self, posts: List[Dict]) -> List[Dict]:
        """Filter out pinned posts (usually the first few posts)"""
        # Simple heuristic: remove first 3 posts as they're often pinned
        # You can adjust this logic based on your needs
        
        if len(posts) <= 3:
            print(f"{Fore.YELLOW}⚠ Only {len(posts)} posts available, not filtering pinned posts{Style.RESET_ALL}")
            return posts
        
        non_pinned = posts[3:]  # Skip first 3 posts
        print(f"{Fore.GREEN}✓ Filtered out 3 potentially pinned posts, {len(non_pinned)} remaining{Style.RESET_ALL}")
        return non_pinned
    
    def sort_posts_by_metric(self, posts: List[Dict], sort_by: str = "view_count") -> List[Dict]:
        """Sort posts by the specified engagement metric"""
        print(f"{Fore.YELLOW}Sorting posts by {sort_by}...{Style.RESET_ALL}")
        
        def get_numeric_value(post, key):
            """Convert string numbers to integers for sorting"""
            value = post.get(key, 0)
            
            if isinstance(value, str):
                # Remove commas and convert to int
                try:
                    return int(value.replace(',', '').replace(' ', ''))
                except:
                    return 0
            elif isinstance(value, (int, float)):
                return int(value)
            else:
                return 0
        
        try:
            sorted_posts = sorted(
                posts, 
                key=lambda x: get_numeric_value(x, sort_by), 
                reverse=True
            )
            
            print(f"{Fore.GREEN}✓ Posts sorted by {sort_by}{Style.RESET_ALL}")
            
            # Show top 5 for preview
            print(f"\n{Fore.CYAN}Top 5 posts by {sort_by}:{Style.RESET_ALL}")
            for i, post in enumerate(sorted_posts[:5], 1):
                url = post.get('url', 'No URL')
                metric_value = get_numeric_value(post, sort_by)
                print(f"  {i}. {metric_value:,} {sort_by} - {url}")
            
            return sorted_posts
            
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ Could not sort by {sort_by}: {e}{Style.RESET_ALL}")
            print(f"Using original order...")
            return posts
    
    def select_top_posts(self, posts: List[Dict], count: int) -> List[Dict]:
        """Select the top N posts"""
        selected = posts[:count]
        print(f"{Fore.GREEN}✓ Selected top {len(selected)} posts for transcription{Style.RESET_ALL}")
        return selected
    
    def transcribe_posts(self, posts: List[Dict], profile_name: str = "unknown", quick_transcribe: bool = False) -> Optional[str]:
        """Transcribe the selected posts and create combined document"""
        if not posts:
            print(f"{Fore.RED}No posts to transcribe{Style.RESET_ALL}")
            return None
        
        if quick_transcribe and len(posts) == 1:
            print(f"\n{Fore.YELLOW}⚡ Quick transcribe mode: Single reel transcription{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.CYAN}Starting transcription of {len(posts)} posts...{Style.RESET_ALL}")
        
        transcriptions = []
        successful_count = 0
        
        for i, post in enumerate(posts, 1):
            url = post.get('url', '')
            if not url:
                print(f"{Fore.YELLOW}⚠ Post {i}: No URL found, skipping{Style.RESET_ALL}")
                continue
            
            print(f"\n{Fore.CYAN}[{i}/{len(posts)}] Transcribing: {url}{Style.RESET_ALL}")
            
            try:
                # Use the existing transcriber's process_url method
                success = self.transcriber.process_url(url)
                
                if success:
                    # Find the most recent transcription file
                    transcription_files = list(self.transcriber.output_dir.glob("*.txt"))
                    if transcription_files:
                        # Get the most recent file
                        latest_file = max(transcription_files, key=lambda x: x.stat().st_mtime)
                        
                        # Read the transcription content
                        with open(latest_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # Extract just the transcription part (after the metadata)
                            lines = content.split('\n')
                            transcription_start = 0
                            for j, line in enumerate(lines):
                                if line.startswith('-' * 50):
                                    transcription_start = j + 1
                                    break
                            
                            transcription_text = '\n'.join(lines[transcription_start:]).strip()
                        
                        transcriptions.append({
                            'post_number': i,
                            'url': url,
                            'transcription': transcription_text,
                            'csv_data': post,
                            'file_path': str(latest_file.name)
                        })
                        successful_count += 1
                        print(f"{Fore.GREEN}✓ Post {i} transcribed successfully{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}⚠ Post {i} transcription file not found{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⚠ Post {i} transcription failed{Style.RESET_ALL}")
                    
            except Exception as e:
                print(f"{Fore.RED}✗ Post {i} error: {str(e)}{Style.RESET_ALL}")
        
        if not transcriptions:
            print(f"\n{Fore.RED}No posts were successfully transcribed{Style.RESET_ALL}")
            return None
        
        print(f"\n{Fore.GREEN}✓ Successfully transcribed {successful_count}/{len(posts)} posts{Style.RESET_ALL}")
        
        # Create combined document
        return self.create_combined_document(transcriptions, profile_name, quick_transcribe)
    
    def create_combined_document(self, transcriptions: List[Dict], profile_name: str, quick_transcribe: bool = False) -> str:
        """Create a combined document with all transcriptions"""
        
        if quick_transcribe and len(transcriptions) == 1:
            # For quick transcribe, use a simpler naming convention
            reel_id = self.extract_reel_id(transcriptions[0]['url'])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quick_{profile_name}_{reel_id}_{timestamp}.txt"
        else:
            # Use the existing naming convention for multiple reels
            filename = f"{profile_name}top{len(transcriptions)}transcripts.txt"
        
        filepath = self.output_dir / filename
        
        # If file exists, add timestamp to make it unique
        if filepath.exists():
            filename = f"{profile_name}top{len(transcriptions)}transcripts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = self.output_dir / filename
        
        # Create the document
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Instagram Profile Transcription Report (CSV-Based)\n")
            f.write("=" * 80 + "\n\n")
            
            # Header information
            f.write(f"Profile: @{profile_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Posts Transcribed: {len(transcriptions)}\n")
            f.write(f"Source: CSV data import\n\n")
            
            # Table of contents
            f.write("## Table of Contents\n")
            f.write("-" * 40 + "\n\n")
            
            for trans in transcriptions:
                csv_data = trans['csv_data']
                views = csv_data.get('view_count', 'N/A')
                likes = csv_data.get('like_count', 'N/A')
                comments = csv_data.get('comment_count', 'N/A')
                
                f.write(f"{trans['post_number']:2d}. Post {trans['post_number']}\n")
                f.write(f"    URL: {trans['url']}\n")
                f.write(f"    Views: {views}\n")
                f.write(f"    Likes: {likes}\n")
                f.write(f"    Comments: {comments}\n\n")
            
            f.write("=" * 80 + "\n\n")
            
            # Detailed transcriptions
            for trans in transcriptions:
                csv_data = trans['csv_data']
                
                f.write(f"## POST #{trans['post_number']}\n")
                f.write("-" * 60 + "\n\n")
                
                f.write(f"**URL:** {trans['url']}\n")
                f.write(f"**Views:** {csv_data.get('view_count', 'N/A')}\n")
                f.write(f"**Likes:** {csv_data.get('like_count', 'N/A')}\n")
                f.write(f"**Comments:** {csv_data.get('comment_count', 'N/A')}\n")
                
                if trans['file_path']:
                    f.write(f"**Individual File:** {trans['file_path']}\n")
                
                f.write(f"\n**TRANSCRIPTION:**\n")
                f.write("-" * 20 + "\n")
                f.write(f"{trans['transcription']}\n\n")
                
                f.write("=" * 80 + "\n\n")
        
        print(f"{Fore.GREEN}✓ Combined document created: {filename}{Style.RESET_ALL}")
        
        # Clean up individual transcription files to save space
        self.cleanup_individual_files(transcriptions)
        
        return str(filepath)
    
    def cleanup_individual_files(self, transcriptions: List[Dict]):
        """Clean up individual transcription files after creating combined document"""
        print(f"{Fore.BLUE}🗑️ Cleaning up individual transcription files...{Style.RESET_ALL}")
        
        cleaned_count = 0
        for trans in transcriptions:
            if trans.get('file_path'):
                individual_file_path = self.output_dir / trans['file_path']
                try:
                    if individual_file_path.exists():
                        individual_file_path.unlink()
                        cleaned_count += 1
                        print(f"{Fore.BLUE}   🗑️ Removed: {trans['file_path']}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}   ⚠️ Could not remove {trans['file_path']}: {e}{Style.RESET_ALL}")
        
        if cleaned_count > 0:
            print(f"{Fore.GREEN}✓ Cleaned up {cleaned_count} individual transcription files{Style.RESET_ALL}")
        
        # Also ensure the transcriber's cleanup is called
        try:
            self.transcriber.cleanup()
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Error during transcriber cleanup: {e}{Style.RESET_ALL}")
    
    def extract_reel_id(self, url: str) -> str:
        """Extract reel ID from Instagram URL for file naming"""
        try:
            if '/reel/' in url:
                # Extract reel ID from URL like: https://www.instagram.com/username/reel/ABC123/
                parts = url.split('/reel/')
                if len(parts) > 1:
                    reel_id = parts[1].split('/')[0].split('?')[0]
                    return reel_id[:10]  # Limit length for filename
            return "unknown"
        except:
            return "unknown"
    
    def process_csv_file(
        self, 
        csv_file: str, 
        top_count: int = 5, 
        sort_by: str = "view_count",
        filter_pinned: bool = True,
        profile_name: str = None,
        quick_transcribe: bool = False
    ) -> Optional[str]:
        """Main method to process CSV file and transcribe top posts"""
        
        if quick_transcribe:
            print(f"{Fore.CYAN}⚡ Quick CSV Profile Transcriber{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}🎬 CSV Profile Transcriber{Style.RESET_ALL}")
        print(f"CSV File: {csv_file}")
        print(f"Top Posts: {top_count}")
        print(f"Sort By: {sort_by}")
        print(f"Filter Pinned: {filter_pinned}\n")
        
        # Read CSV data
        posts = self.read_csv_data(csv_file)
        if not posts:
            return None
        
        # Normalize column names
        posts = self.normalize_column_names(posts)
        
        # Extract profile name if not provided
        if not profile_name:
            if posts and 'profile_name' in posts[0]:
                profile_name = posts[0]['profile_name']
            else:
                profile_name = Path(csv_file).stem
        
        # Filter to video posts only
        posts = self.filter_video_posts(posts)
        if not posts:
            print(f"{Fore.RED}No video posts found in CSV{Style.RESET_ALL}")
            return None
        
        # Filter out pinned posts if requested
        if filter_pinned:
            posts = self.filter_non_pinned_posts(posts)
        
        # Sort by engagement metric
        posts = self.sort_posts_by_metric(posts, sort_by)
        
        # Select top N posts
        top_posts = self.select_top_posts(posts, top_count)
        
        # Transcribe posts
        return self.transcribe_posts(top_posts, profile_name, quick_transcribe)

def main():
    parser = argparse.ArgumentParser(
        description="Transcribe Instagram posts from CSV data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s data.csv
  %(prog)s data.csv --top 10 --sort like_count
  %(prog)s data.csv --top 5 --sort view_count --no-filter-pinned
  %(prog)s data.csv --profile username --output my_transcriptions

CSV Format:
  The CSV should contain columns like: Profile, Reel, Views, Likes, Comments
  Column names are automatically normalized (case-insensitive).
        """
    )
    
    parser.add_argument("csv_file", help="Path to CSV file with Instagram post data")
    parser.add_argument("--top", "-t", type=int, default=5, 
                       help="Number of top posts to transcribe (default: 5)")
    parser.add_argument("--sort", "-s", default="view_count",
                       choices=["view_count", "like_count", "comment_count"],
                       help="Sort posts by metric (default: view_count)")
    parser.add_argument("--profile", "-p", 
                       help="Profile name (auto-detected from CSV if not provided)")
    parser.add_argument("--output", "-o", default="csv_profile_transcriptions",
                       help="Output directory (default: csv_profile_transcriptions)")
    parser.add_argument("--no-filter-pinned", action="store_true",
                       help="Don't filter out pinned posts")
    parser.add_argument("--preview", action="store_true",
                       help="Show preview of CSV data without transcribing")
    
    args = parser.parse_args()
    
    # Check if CSV file exists
    if not Path(args.csv_file).exists():
        print(f"{Fore.RED}Error: CSV file '{args.csv_file}' not found{Style.RESET_ALL}")
        return
    
    print(f"{Fore.CYAN}{'='*70}")
    print(f"🎬 CSV Profile Transcriber 🎬")
    print(f"{'='*70}{Style.RESET_ALL}\n")
    
    # Create transcriber
    transcriber = CSVProfileTranscriber(args.output)
    
    if args.preview:
        # Just show preview of data
        posts = transcriber.read_csv_data(args.csv_file)
        if posts:
            posts = transcriber.normalize_column_names(posts)
            posts = transcriber.filter_video_posts(posts)
            if not args.no_filter_pinned:
                posts = transcriber.filter_non_pinned_posts(posts)
            posts = transcriber.sort_posts_by_metric(posts, args.sort)
            top_posts = transcriber.select_top_posts(posts, args.top)
            
            print(f"\n{Fore.CYAN}Preview of top {len(top_posts)} posts:{Style.RESET_ALL}")
            for i, post in enumerate(top_posts, 1):
                print(f"{i:2d}. {post.get('url', 'No URL')}")
                print(f"    Views: {post.get('view_count', 'N/A')}")
                print(f"    Likes: {post.get('like_count', 'N/A')}")
                print(f"    Comments: {post.get('comment_count', 'N/A')}\n")
    else:
        # Process and transcribe
        result = transcriber.process_csv_file(
            csv_file=args.csv_file,
            top_count=args.top,
            sort_by=args.sort,
            filter_pinned=not args.no_filter_pinned,
            profile_name=args.profile,
            quick_transcribe=False
        )
        
        if result:
            print(f"\n{Fore.GREEN}🎉 Process completed!{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Combined transcription saved to: {result}{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}⚠ No transcriptions were created{Style.RESET_ALL}")

if __name__ == "__main__":
    main() 