import os
import glob
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPADATA_KEY = os.getenv("SUPADATA_KEY")
if not SUPADATA_KEY:
    print("Error: SUPADATA_KEY not found in .env")
    exit(1)

API_URL = "https://api.supadata.ai/v1/youtube/transcript"

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

def process_videos(input_file, output_txt, output_md, open_mode='w'):
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return

    with open(input_file, 'r') as f:
        lines = f.readlines()

    current_title = ""
    current_subtitle = ""
    video_count_in_title = 0
    
    # In append mode, we might skip the header if the file is not empty
    md_content = ""
    if open_mode == 'w' or (open_mode == 'a' and (not os.path.exists(output_md) or os.path.getsize(output_md) == 0)):
        md_content = "# Video Transcripts\n\n"
        
    txt_content = ""

    for line in lines:
        line = line.strip()
        # Takes care of multiple empty lines/newlines by skipping them
        if not line:
            continue

        if line.startswith("**"):
            current_subtitle = line[2:].strip()
            continue
        
        elif line.startswith("*"):
            current_title = line[1:].strip()
            current_subtitle = ""
            video_count_in_title = 0
            
            md_content += f"## {current_title}\n\n"
            txt_content += f"\n=== {current_title} ===\n"
            continue

        if "youtube.com" in line or "youtu.be" in line:
            video_count_in_title += 1
            if current_subtitle:
                header = current_subtitle
            else:
                header = f"Video {video_count_in_title}"

            print(f"Processing {header} ({line})...")
            transcript = get_transcript_supadata(line)
            
            if not isinstance(transcript, str):
                transcript = str(transcript)

            md_content += f"### {header}\n"
            md_content += f"**URL:** {line}\n\n"
            md_content += f"<details><summary>Show Transcript</summary>\n\n"
            md_content += transcript + "\n"
            md_content += "\n</details>\n\n"

            txt_content += f"\n--- {header} ({line}) ---\n"
            txt_content += transcript + "\n"

    with open(output_txt, open_mode) as f:
        f.write(txt_content)
    
    with open(output_md, open_mode) as f:
        f.write(md_content)
        
    print(f"Done! Saved to {output_txt} and {output_md}")

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

    print(f"\nStarting process...")
    print(f"Input: {video_file}")
    print(f"Output MD: {output_md} ({mode})")
    print(f"Output TXT: {output_txt} ({mode})")
    
    if input("\nProceed? (y/n): ").lower() != 'y':
        print("Aborted.")
        return

    process_videos(video_file, output_txt, output_md, mode)

if __name__ == "__main__":
    cli()
