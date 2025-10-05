from flask import Flask, render_template, request, jsonify
import parser  # This imports our parser.py file
import fitz # PyMuPDF for the highlighter
import re
import os

app = Flask(__name__)
# Configure a folder to temporarily store uploaded files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def resume_parser_page():
    if request.method == 'POST':
        if 'resume_file' not in request.files:
            return "No file part", 400
        file = request.files['resume_file']
        if file.filename == '':
            return "No selected file", 400

        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            try:
                results = parser.parse_resume(filepath)
            except Exception as e:
                results = {"error": f"An error occurred during parsing: {str(e)}"}
            
            os.remove(filepath)
            
            return render_template('index.html', results=results, page='parser')

    return render_template('index.html', page='parser')


@app.route('/highlight', methods=['GET', 'POST'])
def text_highlighter_page():
    if request.method == 'POST':
        text_content = ""
        search_term = request.form.get('search_term', '').strip()
        
        pasted_text = request.form.get('pasted_text', '')
        if pasted_text:
            text_content = pasted_text
        elif 'document_file' in request.files and request.files['document_file'].filename != '':
            file = request.files['document_file']
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            text_content = parser.extract_text_from_pdf(filepath)
            os.remove(filepath)

        highlighted_text = ""
        count = 0
        if text_content and search_term:
            pattern = re.compile(re.escape(search_term), re.IGNORECASE)
            highlighted_text = pattern.sub(f'<mark>{search_term}</mark>', text_content)
            count = len(pattern.findall(text_content))

        return render_template('index.html', 
                               page='highlighter', 
                               highlighted_text=highlighted_text, 
                               search_term=search_term,
                               count=count)

    return render_template('index.html', page='highlighter')

if __name__ == '__main__':
    app.run(debug=True)