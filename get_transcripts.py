import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPADATA_KEY = os.getenv("SUPADATA_KEY")
if not SUPADATA_KEY:
    print("Error: SUPADATA_KEY not found in .env")
    exit(1)

# Correct API endpoint based on typical Supadata usage found
API_URL = "https://api.supadata.ai/v1/youtube/transcript"

def get_transcript_supadata(video_url):
    print(f"Fetching transcript for {video_url}...")
    headers = {
        "x-api-key": SUPADATA_KEY
    }
    # Supadata often takes just 'url' and returns JSON with 'content'
    # 'text=True' usually returns just the text, but let's handle JSON 
    # to be safe and extract manually if needed.
    params = {
        "url": video_url,
        "text": True 
    }
    
    try:
        response = requests.get(API_URL, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            # If text=True is respected, 'content' might be a string.
            # If not, it might be a list of segments.
            content = data.get('content')
            
            if isinstance(content, list):
                # Join if it's a list of segments
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

def process_videos(input_file, output_txt, output_md):
    with open(input_file, 'r') as f:
        lines = f.readlines()

    current_title = ""
    current_subtitle = ""
    video_count_in_title = 0
    
    md_content = "# Video Transcripts\n\n"
    txt_content = ""

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
            
            # Ensure transcript is a string
            if not isinstance(transcript, str):
                transcript = str(transcript)

            # Append to Markdown
            md_content += f"### {header}\n"
            md_content += f"**URL:** {line}\n\n"
            md_content += f"<details><summary>Show Transcript</summary>\n\n"
            md_content += transcript + "\n"
            md_content += "\n</details>\n\n"

            # Append to Text
            txt_content += f"\n--- {header} ({line}) ---\n"
            txt_content += transcript + "\n"

    with open(output_txt, 'w') as f:
        f.write(txt_content)
    
    with open(output_md, 'w') as f:
        f.write(md_content)
        
    print(f"Done! Saved to {output_txt} and {output_md}")

if __name__ == "__main__":
    process_videos('videos.txt', 'full_transcripts.txt', 'results.md')
