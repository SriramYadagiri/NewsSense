import io
from flask import Flask, request, render_template
from flask_session import Session
import openai
from newspaper import Article

import PyPDF2
from docx import Document

app = Flask(__name__)

# Session configuration
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Home route
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    pasted_text = request.form.get('article_text', '').strip()
    article_url = request.form.get('article_url', '').strip()
    uploaded_file = request.files.get('article_file')

    raw_text = ""

    # Step 2: Detect input method
    if pasted_text:
        method = "pasted text"
        raw_text = pasted_text

    elif article_url:
        method = "URL"
        try:
            article = Article(article_url)
            article.download()
            article.parse()
            raw_text = article.text
        except Exception as e:
            return render_template("index.html", error="Failed to extract article from URL.")

    elif uploaded_file and uploaded_file.filename != '':
        method = "file upload"
        filename = uploaded_file.filename
        if filename.endswith('.txt'):
            raw_text = uploaded_file.read().decode('utf-8')

        elif filename.endswith('.pdf'):
            pdf = PyPDF2.PdfReader(uploaded_file)
            raw_text = ""
            for page in pdf.pages:
                raw_text += page.extract_text()
        elif filename.endswith('.docx'):
            raw_text = ""
            docx_file = io.BytesIO(uploaded_file.read())
            doc = Document(docx_file)
            for para in doc.paragraphs:
                raw_text += para.text + "\n"
        else:
            return render_template("index.html", error="Unsupported file type. Only .txt, .pdf, and .docx files are allowed.")
    else:
        return render_template("index.html", error="No input detected. Please paste text, enter a URL, or upload a file.")
    
    return render_template('result.html', highlighted_text=raw_text, lean="lean_label", unbiased_text="unbiased_version")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
