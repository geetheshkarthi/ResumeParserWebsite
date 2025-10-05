import re
import fitz  # PyMuPDF
from pprint import pprint
from urllib.parse import urlparse

# A predefined list of skills.
SKILLS_DB = [
    'c++', 'python', 'javascript', 'risc-v', 'assembly', 'html', 'css', 'sql', 'pytorch',
    'numpy', 'pandas', 'matplotlib', 'express.js', 'react', 'socket.io', 'git', 'github',
    'latex', 'mysql', 'linux', 'vs code', 'jupyter notebook', 'java'
]

def extract_text_from_pdf(pdf_path):
    """Extracts all text from a given PDF file."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return None

def extract_name(text):
    """Extracts the full name."""
    pattern = r"^\s*((?:[A-Z]+\s?)+|(?:[A-Z][a-z]+\s?)+)\n"
    match = re.search(pattern, text)
    if match:
        name = match.group(1).strip()
        if len(name.split()) > 1 and "SKILLS" not in name:
            return name
    return None

def extract_contact_info(text, pdf_path):
    """Extracts general contact info and filters for main profile links."""
    info = {'email': None, 'phone': None, 'linkedin': None, 'repo_links': []}
    REPO_DOMAINS = ['github.com', 'gitlab.com', 'bitbucket.org']
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            for link in page.get_links():
                if 'uri' in link:
                    url = link['uri']
                    if "linkedin.com" in url and not info['linkedin']:
                        info['linkedin'] = url
                    # RESTORED GITHUB LINK DETECTION
                    elif any(domain in url for domain in REPO_DOMAINS):
                        path_parts = [part for part in urlparse(url).path.split('/') if part]
                        if len(path_parts) == 1:
                            if url not in info['repo_links']: info['repo_links'].append(url)
                    elif "mailto:" in url and not info['email']:
                        info['email'] = url.replace('mailto:', '')
        doc.close()
    except Exception as e:
        print(f"Could not extract hyperlinks: {e}")

    if not info['email']:
        match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
        if match: info['email'] = match.group(0)
    
    if not info['phone']:
        match = re.search(r"(\+?\d{1,3})?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        if match: info['phone'] = match.group(0).strip()
            
    return info

def extract_skills(text, skills_list):
    """Extracts skills from the text based on a predefined list."""
    found_skills = set()
    for skill in skills_list:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            found_skills.add(skill.lower())
    return sorted(list(found_skills))

def extract_cgpa(text):
    """Extracts CGPA using a highly robust three-step OR logic."""
    pattern1 = r"(?i)(?:CGPA|GPA)\s*[:\-]?\s*(\d\.\d+)"
    match = re.search(pattern1, text)
    if match: return match.group(1)

    edu_section_pattern = r"(?i)^EDUCATION\s*$([\s\S]*?)(?=^\s*[A-Z]{2,}|^\s*$)"
    edu_match = re.search(edu_section_pattern, text, re.MULTILINE)
    if edu_match:
        edu_text = edu_match.group(1)
        cgpa_match = re.search(r"\b(\d{1,2}\.\d+)\b", edu_text)
        if cgpa_match: return cgpa_match.group(1)

    pattern3 = r"\b(\d\.\d+)\b"
    match = re.search(pattern3, text)
    if match: return match.group(1)
        
    return None

def extract_project_titles(text):
    """
    Final, robust plain-text version. Filters out description lines and
    then merges titles that were split across multiple lines.
    """
    try:
        possible_headers = ['projects\n', 'p r o j e c t s\n']
        start_index = -1
        
        for header in possible_headers:
            try:
                start_index = text.lower().index(header) + len(header)
                break 
            except ValueError:
                continue 
        
        if start_index == -1: return []

    except ValueError:
        return []

    end_index = len(text)
    end_keywords = ['achievements', 'languages', 'skills', 'tools & platforms', 'relevant courses']
    for keyword in end_keywords:
        try:
            temp_index = text.lower().index(keyword, start_index)
            end_index = min(end_index, temp_index)
        except ValueError:
            continue

    projects_text = text[start_index:end_index]
    
    DESCRIPTION_STARTERS = {
        'developed', 'built', 'created', 'led', 'managed', 'a modern', 'implemented',
        'designed', 'enhanced', 'accelerated', 'integrated', 'trained', 'achieved',
        'tools used'
    }
    BULLETS = {'o', '▪', '•', '*', '-'}
    
    candidate_titles = []
    lines = projects_text.split('\n')
    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line: continue
        
        is_bullet_line = cleaned_line and cleaned_line[0] in BULLETS
        temp_line = cleaned_line.lstrip(''.join(BULLETS)).strip()
        is_verb_line = any(temp_line.lower().startswith(starter) for starter in DESCRIPTION_STARTERS)
        
        is_description = is_bullet_line or is_verb_line
        is_junk = len(cleaned_line) <= 2

        if not is_description and not is_junk:
            title = re.sub(r'\s*\[.*?\]', '', cleaned_line)
            if title:
                candidate_titles.append(title)
    
    if not candidate_titles:
        return []
        
    merged_titles = []
    current_title = candidate_titles[0]
    for i in range(1, len(candidate_titles)):
        next_title = candidate_titles[i]
        if next_title and (next_title[0].islower() or len(next_title.split()) < 3):
            current_title += " " + next_title
        else:
            merged_titles.append(current_title)
            current_title = next_title
    merged_titles.append(current_title)
            
    return merged_titles

def calculate_resume_score(data):
    """Calculates a resume score based on extracted entities."""
    score, feedback = 0, []
    MAX_SCORE = 100
    
    if data['contact']['email'] and data['contact']['phone']: score += 15; feedback.append("(+15) Email and Phone provided.")
    if data['contact']['linkedin']: score += 5; feedback.append("(+5) LinkedIn profile found.")
    if data['contact']['repo_links']: score += 5; feedback.append("(+5) Main code repository link(s) found.")

    num_skills = len(data['skills'])
    if num_skills > 0:
        skill_score = min(num_skills * 2, 25); score += skill_score; feedback.append(f"(+{skill_score}) Found {num_skills} relevant skills.")
        high_value = {'python', 'aws', 'docker', 'machine learning', 'react', 'java', 'kubernetes'}
        bonus_skills = high_value.intersection(set(data['skills']))
        if bonus_skills:
            bonus_score = min(len(bonus_skills) * 4, 20); score += bonus_score; feedback.append(f"(+{bonus_score}) Found high-demand skills: {', '.join(bonus_skills)}.")

    num_projects = len(data['projects'])
    if num_projects > 0:
        project_score = min(num_projects * 5, 20); score += project_score; feedback.append(f"(+{project_score}) Found {num_projects} project(s).")
        
    if data['cgpa']: score += 10; feedback.append(f"(+10) CGPA of {data['cgpa']} found.")

    return {'score': f"{min(score, MAX_SCORE)} / {MAX_SCORE}", 'feedback': feedback}

def parse_resume(pdf_path):
    """The main function to orchestrate the resume parsing."""
    print(f"--- Analyzing {pdf_path} ---")
    resume_text = extract_text_from_pdf(pdf_path)
    
    if not resume_text: return {"error": "Could not read text from PDF."}

    extracted_data = {
        'name': extract_name(resume_text),
        'contact': extract_contact_info(resume_text, pdf_path),
        'skills': extract_skills(resume_text, SKILLS_DB),
        'cgpa': extract_cgpa(resume_text),
        'projects': extract_project_titles(resume_text)
    }
    
    score_details = calculate_resume_score(extracted_data)
    
    print("--- Analysis Complete ---")
    
    return {'extracted_info': extracted_data, 'resume_score': score_details}