import os
import glob
import requests
import json
import time
import re
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

# Load environment variables
load_dotenv()

SUPADATA_KEY = os.getenv("SUPADATA_KEY")
if not SUPADATA_KEY:
    print("Warning: SUPADATA_KEY not found in .env (Supadata API will be unavailable).")

API_URL = "https://api.supadata.ai/v1/youtube/transcript"

def extract_video_id(url):
    """Extracts the YouTube video ID from standard watch or youtu.be URLs."""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if match:
        return match.group(1)
    return None

def get_transcript_youtube_api(video_url):
    print(f"Fetching transcript using free youtube-transcript-api...")
    video_id = extract_video_id(video_url)
    if not video_id:
        return f"Error: Could not extract video ID from '{video_url}'."
    
    try:
        # Fallback languages (e.g. English natively, or auto-generated English)
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        
        full_text = " ".join([seg['text'] for seg in transcript_list])
        full_text = " ".join(full_text.split())
        return full_text
        
    except Exception as e:
        return f"Youtube Transcript API Exception: {str(e)}"

def get_transcript_supadata(video_url):
    print(f"Fetching transcript for {video_url}...")
    headers = {
        "x-api-key": SUPADATA_KEY
    }
    params = {
        "url": video_url,
        "text": True 
    }
    
    try:
        response = requests.get(API_URL, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('content')
            
            if isinstance(content, list):
                full_text = ""
                for seg in content:
                    if isinstance(seg, dict):
                        full_text += seg.get('text', '') + " "
                    elif isinstance(seg, str):
                        full_text += seg + " "
                return full_text.strip()
            elif isinstance(content, str):
                return content
            else:
                return f"Unexpected content format: {type(content)}"

        else:
            return f"Error {response.status_code}: {response.text}"
            
    except Exception as e:
        return f"Exception: {str(e)}"

def process_videos(input_file, output_txt, output_md, open_mode='w', api_choice='2'):
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return

    with open(input_file, 'r') as f:
        lines = f.readlines()

    # Load existing content to avoid duplicates if appending/resuming
    existing_video_ids = set()
    if open_mode == 'a' and os.path.exists(output_txt):
        with open(output_txt, 'r') as f:
            content = f.read()
            # Find all video IDs already in the file (11-character alphanumeric/dash/underscore)
            existing_video_ids.update(re.findall(r"(?:v=|\/|embed\/|youtu\.be\/)([0-9A-Za-z_-]{11})", content))
        if existing_video_ids:
            print(f"Resuming: Found {len(existing_video_ids)} videos already processed.")

    current_title = ""
    current_subtitle = ""
    video_count_in_title = 0
    global_video_count = 0
    
    # Track what has been written to the file this session or was already there
    last_written_title = ""
    
    # Initial setup for output files
    if open_mode == 'w':
        # Clear existing or create new
        with open(output_md, 'w') as f:
            f.write("# Video Transcripts\n\n")
        with open(output_txt, 'w') as f:
            pass 
    elif open_mode == 'a' and (not os.path.exists(output_md) or os.path.getsize(output_md) == 0):
        with open(output_md, 'a') as f:
            f.write("# Video Transcripts\n\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("**"):
            current_subtitle = line[2:].strip()
            continue
        
        elif line.startswith("*"):
            current_title = line[1:].strip()
            current_subtitle = ""
            video_count_in_title = 0
            # Note: We write this header only when we actually process a video under it
            # to avoid duplicating headers if resuming.
            continue

        if "youtube.com" in line or "youtu.be" in line:
            video_count_in_title += 1
            video_id = extract_video_id(line)
            
            if video_id and video_id in existing_video_ids:
                # If we've already seen this video, we skip it but update context
                last_written_title = current_title
                print(f"Skipping already processed video: {line}")
                continue

            # New video to process
            global_video_count += 1
            header = current_subtitle if current_subtitle else f"Video {video_count_in_title}"

            # Open files in append mode for this specific entry
            with open(output_txt, 'a') as f_txt, open(output_md, 'a') as f_md:
                # Write Title header if it changed and we haven't written it yet
                if current_title and current_title != last_written_title:
                    f_md.write(f"## {current_title}\n\n")
                    f_txt.write(f"\n=== {current_title} ===\n")
                    last_written_title = current_title

                print(f"Processing {header} ({line})...")
                
                if api_choice == '2':
                    if global_video_count > 1:
                        print(f"Waiting 10 seconds before next request (avoiding rate limit)...")
                        time.sleep(10)
                    transcript = get_transcript_youtube_api(line)
                else:
                    transcript = get_transcript_supadata(line)
                
                if not isinstance(transcript, str):
                    transcript = str(transcript)

                # MD Output
                f_md.write(f"### {header}\n")
                f_md.write(f"**URL:** {line}\n\n")
                f_md.write(f"<details><summary>Show Transcript</summary>\n\n")
                f_md.write(transcript + "\n")
                f_md.write("\n</details>\n\n")
                f_md.flush()

                # TXT Output
                f_txt.write(f"\n--- {header} ({line}) ---\n")
                f_txt.write(transcript + "\n")
                f_txt.flush()

    print(f"Done! All videos processed and saved to {output_txt} and {output_md}")

def select_input_file():
    txt_files = glob.glob("*.txt")
    if not txt_files:
        return input("No .txt files found. Enter input filename: ").strip()
    
    print("\nSelect input file containing video URLs:")
    for i, file in enumerate(txt_files):
        print(f"{i + 1}. {file}")
    
    while True:
        try:
            choice = input(f"Enter number (1-{len(txt_files)}) or filename: ")
            if choice.isdigit() and 1 <= int(choice) <= len(txt_files):
                return txt_files[int(choice) - 1]
            else: 
                 # Allow typing filename
                 return choice.strip()
        except:
            pass

def cli():
    print("=== YouTube Transcript Fetcher CLI ===")
    
    # 1. Input Videos File
    video_file = select_input_file()

    # Create output directories
    base_output_dir = "transcripts"
    md_dir = os.path.join(base_output_dir, "markdown")
    txt_dir = os.path.join(base_output_dir, "txt")

    if not os.path.exists(md_dir):
        os.makedirs(md_dir)
    if not os.path.exists(txt_dir):
        os.makedirs(txt_dir)

    # 2. Output Filename
    print("\nEnter output filename (WITHOUT extension):")
    print("Example: 'module_1' (will create transcripts/markdown/module_1.md and transcripts/txt/module_1.txt)")
    base_name = input("Filename: ").strip()
    
    # Strip extension if user accidentally added one
    if base_name.endswith(".txt") or base_name.endswith(".md"):
        base_name = os.path.splitext(base_name)[0]
    
    if not base_name:
        base_name = "transcripts" # Default

    output_md = os.path.join(md_dir, f"{base_name}.md")
    output_txt = os.path.join(txt_dir, f"{base_name}.txt")

    # 4. Mode
    mode = 'w'
    if os.path.exists(output_md) or os.path.exists(output_txt):
        print(f"\nOutput file(s) exist.")
        print("1. Overwrite (w)")
        print("2. Append (a)")
        while True:
            c = input("Choice: ").strip().lower()
            if c == '1' or c == 'w':
                mode = 'w'
                break
            elif c == '2' or c == 'a':
                mode = 'a'
                break

    print("\nSelect Transcript API:")
    print("1. Supadata API (Fast, requires SUPADATA_KEY)")
    print("2. YoutubeTranscriptApi (Free, automatically delayed 10s between calls)")
    api_choice = '2'
    while True:
        c = input("Choice (1 or 2): ").strip()
        if c == '1':
            if not SUPADATA_KEY:
                print("Error: Supadata API requires SUPADATA_KEY in .env. Please choose 2.")
                continue
            api_choice = '1'
            break
        elif c == '2':
            api_choice = '2'
            break

    api_name = "Supadata" if api_choice == '1' else "Youtube-Transcript-Api"
    print(f"\nStarting process [{api_name}]...")
    print(f"Input: {video_file}")
    print(f"Output MD: {output_md} ({mode})")
    print(f"Output TXT: {output_txt} ({mode})")
    
    if input("\nProceed? (y/n): ").lower() != 'y':
        print("Aborted.")
        return

    process_videos(video_file, output_txt, output_md, mode, api_choice)

if __name__ == "__main__":
    cli()
