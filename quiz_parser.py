import os
import glob
import json
import re

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: BeautifulSoup not found. Please run 'pip install beautifulsoup4'.")
    exit(1)

def clean_text(text):
    if not text:
        return ""
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_html_quiz(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    questions = []

    # Iterate through all question holders
    question_holders = soup.find_all('div', class_=re.compile(r'question_holder'))
    
    for q_holder in question_holders:
        q_data = {}
        
        # Get Question Name (e.g., Question 1)
        name_tag = q_holder.find('span', class_='name question_name')
        if name_tag:
            q_data['question_number'] = clean_text(name_tag.get_text())
        
        # Get Question ID
        q_id_tag = q_holder.find('span', class_='id') or q_holder.find('span', class_='question_id')
        if q_id_tag:
             q_data['question_id'] = clean_text(q_id_tag.get_text())
        
        # Get Question Type
        type_tag = q_holder.find('span', class_='question_type')
        if type_tag:
            q_data['question_type'] = clean_text(type_tag.get_text())

        # Get Question Text
        text_div = q_holder.find('div', class_='question_text')
        if text_div:
            # Extract text, possibly keeping some structure if needed, but clean_text is safer for now
            # For dropdowns, we might need to look at select elements within the text
            q_data['question_text'] = clean_text(text_div.get_text())
            
            # Handle dropdowns embedded in text
            dropdowns = text_div.find_all('select', class_='question_input')
            if dropdowns:
                q_data['dropdown_options'] = []
                for dd in dropdowns:
                    options = [opt.text for opt in dd.find_all('option') if opt.get('value')]
                    q_data['dropdown_options'].append(options)

        # Get Answers
        answers_div = q_holder.find('div', class_='answers')
        answers = []
        if answers_div:
            # Iterate through answers
            # Structure varies slightly by question type
            answer_divs = answers_div.find_all('div', class_=re.compile(r'answer'))
            
            seen_answers = set()
            for ans in answer_divs:
                if 'answer_for_' in str(ans.get('class', [])) or 'answer' in ans.get('class', []):
                     # Skip if it's just a wrapper or duplicate
                     if 'answer_group' in ans.get('class', []):
                         continue
                         
                     ans_data = {}
                     
                     # Check if correct/selected
                     ans_classes = ans.get('class', [])
                     if 'correct_answer' in ans_classes:
                         ans_data['is_correct'] = True
                     if 'selected_answer' in ans_classes:
                         ans_data['is_selected'] = True
                     if 'wrong_answer' in ans_classes: # Sometimes explicit
                          ans_data['is_wrong'] = True

                     # Get Answer Text
                     # It might be in a label -> answer_text div
                     text_div = ans.find('div', class_='answer_text')
                     if text_div:
                         ans_data['text'] = clean_text(text_div.get_text())
                     else:
                        # Sometimes answer text is directly in the label or element text
                        # Try finding input value or label text
                        label = ans.find('label')
                        if label:
                            ans_data['text'] = clean_text(label.get_text())

                     # Handle Matching Questions (left/right)
                     match_left = ans.find('div', class_='answer_match_left')
                     match_right = ans.find('div', class_='answer_match_right')
                     if match_left and match_right:
                         left_text = clean_text(match_left.get_text())
                         # Right side typically uses a select or text
                         right_select = match_right.find('select')
                         right_text = ""
                         if right_select:
                             # Selected option
                             selected_opt = right_select.find('option', selected=True)
                             if selected_opt:
                                 right_text = clean_text(selected_opt.get_text())
                             else:
                                 right_text = clean_text(right_select.get_text())
                         else:
                             right_text = clean_text(match_right.get_text())
                         
                         ans_data['match_pair'] = f"{left_text} -> {right_text}"
                         ans_data['text'] = ans_data['match_pair'] # Use pair as main text

                     if ans_data.get('text') and ans_data['text'] not in seen_answers:
                         answers.append(ans_data)
                         seen_answers.add(ans_data['text'])
        
        q_data['answers'] = answers
        questions.append(q_data)
        
    return questions

def save_json(data, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"JSON saved to {output_path}")

def save_txt(questions, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        for q in questions:
            f.write(f"{q.get('question_number', 'Question')}: {q.get('question_text', '')}\n")
            
            # Type specific formatting?
            if q.get('question_type'):
                f.write(f"Type: {q.get('question_type')}\n")
            
            if q.get('dropdown_options'):
                f.write("Dropdown Options:\n")
                for opts in q['dropdown_options']:
                    f.write(f"  - {', '.join(opts)}\n")

            f.write("Answers:\n")
            for ans in q.get('answers', []):
                prefix = "  [ ] "
                if ans.get('is_correct'):
                    prefix = "  [x] (Correct) "
                elif ans.get('is_selected'):
                     prefix = "  [x] (Selected) "
                
                f.write(f"{prefix}{ans.get('text', '')}\n")
            
            f.write("\n" + "-"*40 + "\n\n")
    print(f"TXT saved to {output_path}")

def main():
    print("=== Quiz Parser ===")
    
    # Input Selection
    print("Select input source:")
    print("1. File")
    print("2. Directory (parse all .txt/.html files)")
    choice = input("Enter choice (1 or 2): ").strip()
    
    input_files = []
    if choice == '1':
        # List files
        files = glob.glob("*.txt") + glob.glob("*.html")
        for i, f in enumerate(files):
            print(f"{i+1}. {f}")
        file_choice = input(f"Select file (1-{len(files)}): ").strip()
        if file_choice.isdigit() and 1 <= int(file_choice) <= len(files):
            input_files.append(files[int(file_choice)-1])
        else:
             print("Invalid selection.")
             return
    elif choice == '2':
        input_dir = input("Enter directory path (default: current): ").strip() or "."
        if os.path.isdir(input_dir):
            input_files = glob.glob(os.path.join(input_dir, "*.txt")) + glob.glob(os.path.join(input_dir, "*.html"))
        else:
            print("Invalid directory.")
            return

    if not input_files:
        print("No files found to process.")
        return

    # Determine base directory from the first input file
    first_file = input_files[0]
    base_input_dir = os.path.dirname(os.path.abspath(first_file))

    # Output Directories
    results_dir = os.path.join(base_input_dir, "results")
    json_dir = os.path.join(results_dir, "json")
    txt_dir = os.path.join(results_dir, "quiz_txt")

    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
    if not os.path.exists(txt_dir):
        os.makedirs(txt_dir)
        
    print(f"\nProcessing {len(input_files)} files...")
    print(f"Output directory: {results_dir}")

    for file_path in input_files:
        print(f"Parsing {file_path}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            quiz_data = parse_html_quiz(content)
            
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Save to specific subdirectories
            json_path = os.path.join(json_dir, f"{base_name}.json")
            txt_path = os.path.join(txt_dir, f"{base_name}_summary.txt")
            
            save_json(quiz_data, json_path)
            save_txt(quiz_data, txt_path)
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    print("\nDone!")

if __name__ == "__main__":
    main()
