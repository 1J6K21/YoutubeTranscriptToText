# YouTube Transcript & Quiz Parser Tools

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   (Note: `python-dotenv` and `requests` are required for `get_transcripts.py` if not already installed)

## Usage

### 1. Parse Canvas Quizzes
Run the quiz parser to extract questions and answers from saved Canvas quiz HTML/TXT files.
```bash
python3 quiz_parser.py
```
- Select Option 1 to parse a single file.
- Select Option 2 to parse all `.txt` and `.html` files in a directory (default: current directory).
- Output will be saved in `processed_data/` as `.json` (structured) and `_summary.txt` (readable).

### 2. Get YouTube Transcripts
Run the transcript fetcher to get transcripts from YouTube videos using Supadata API.
```bash
python3 get_transcripts.py
```
- Follow the prompts to select an input video list and output filenames.
- Default output location is `processed_data/`.

## Output Structure
All processed files are saved in the `processed_data/` directory.
- `*_summary.txt`: Readable summary of quiz questions and answers.
- `*.json`: Structured data of quiz questions and answers.
- `results.md`: Markdown formatted transcripts.
- `full_transcripts.txt`: Text formatted transcripts.
