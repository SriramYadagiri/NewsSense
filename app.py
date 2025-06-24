import io
import json
import os
import re
from dotenv import load_dotenv
from flask import Flask, request, render_template
import requests
from openai import OpenAI
from bs4 import BeautifulSoup

import PyPDF2
from docx import Document

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"

def format_text_into_paragraphs(text):
    paragraphs = re.split(r'\n\s*\n', text.strip())
    formatted = []
    for p in paragraphs:
        if '<div class="highlight-section">' in p:
            formatted.append(p)
        else:
            formatted.append(f"<p>{p.strip()}</p>")
    return "<br>".join(formatted)


def scrape_with_requests(url):
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = ''.join(p.get_text() for p in paragraphs if p.get_text(strip=True))
        return text
    except Exception as e:
        print("Requests scraping failed:", e)
        return ""

def summarize_article(text):
    text_file_path = 'prompts/summary_message.txt'
    with open(text_file_path, 'r') as file:
            initial_prompt = file.read()

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": initial_prompt},
            {"role": "user", "content": "Summarize and clean the following article for readability:\n\n" + text}
        ],
        temperature=0.3,
        max_tokens=1500
    )

    output = response.choices[0].message.content.strip()
    return json.loads(output)

def determine_bias(text):
    text_file_path = 'prompts/bias_message.txt'
    with open(text_file_path, 'r') as file:
            initial_prompt = file.read()

    user_message = f"Analyze the following text for bias and provide a bias score:\n\n{text}"

    response = client.chat.completions.create(
        model="gpt-4",
        messages = [
            {"role": "system", "content": initial_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.3,
        max_tokens=1000
    )

    output = response.choices[0].message.content.strip()
    return json.loads(output)

def highlight_bias(text, highlighted_passages):
    for obj in highlighted_passages:
        passage = obj["passage"].strip()
        reasoning = obj["reasoning"].strip()

        if passage in text:
            replacement = (
                f'<div class="highlight-section">'
                f'<span class="highlight">{passage}<br><span class="bias-reasoning">{reasoning}</span></span>'
                f'</div>'
            )
            text = text.replace(passage, replacement, 1)  # Replace only once
    return text

def unbias(text, highlighted_passages):
    text_file_path = 'prompts/unbias_message.txt'
    with open(text_file_path, 'r') as file:
        initial_prompt = file.read()
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": initial_prompt},
            {"role": "user", "content": f"Biased Phrases: {highlighted_passages}\n\nArticle:\n{text}"}
        ],
        temperature=0.5,
        max_tokens=1500
    )
    
    output = response.choices[0].message.content.strip()
    return output

def identify_lean(text):
    prompt = f"Based on the article's text alone without inferring from its source, identify where the article leans ideologically in 1 or 2 words (left, right, center, etc),:\n\n{text}"

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes news and articles."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=300
    )

    return response.choices[0].message.content.strip()

def highlight_bias(text):
    prompt = f"Retype word for word the article's text and highlight places where ideological bias is present:\n\n{text}"

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes news and articles."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=300
    )

    return response.choices[0].message.content.strip()

def unbias(text):
    prompt = f"Retype the article in an unbiased fashion:\n\n{text}"

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes news and articles."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=300
    )

    return response.choices[0].message.content.strip()

# --- Routes ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    pasted_text = request.form.get('article_text', '').strip()
    article_url = request.form.get('article_url', '').strip()
    uploaded_file = request.files.get('article_file')
    raw_text = ""

    if pasted_text:
        raw_text = pasted_text

    elif article_url:
        raw_text = scrape_with_requests(article_url)
        if not raw_text:
            return render_template("index.html", error="Failed to extract article from URL. Try pasting the article text directly or uploading a file.")

    elif uploaded_file and uploaded_file.filename != '':
        filename = uploaded_file.filename.lower()
        if filename.endswith('.txt'):
            raw_text = uploaded_file.read().decode('utf-8')

        elif filename.endswith('.pdf'):
            pdf = PyPDF2.PdfReader(uploaded_file)
            pages_text = []
            for page in pdf.pages:
                pages_text.append(page.extract_text() or "")
            raw_text = "\n\n".join(pages_text)

        elif filename.endswith('.docx'):
            docx_file = io.BytesIO(uploaded_file.read())
            doc = Document(docx_file)
            paras = [para.text for para in doc.paragraphs if para.text.strip()]
            raw_text = "\n\n".join(paras)

        else:
            return render_template("index.html", error="Unsupported file type. Only .txt, .pdf, and .docx are allowed.")

    else:
        return render_template("index.html", error="No input detected. Please paste text, enter a URL, or upload a file.")

    new_article = summarize_article(raw_text)
    raw_text = new_article["text"]
    bias = determine_bias(raw_text)
    highlighted_text = highlight_bias(raw_text, bias["highlighted_passages"])

    unbiased_text = unbias(raw_text, bias["highlighted_passages"])

    lean = bias["bias_label"]  # Replace with bias detection model output

    summary = new_article["summary"]

    return render_template('result.html',
                           summary=summary,
                           highlighted_text=format_text_into_paragraphs(highlighted_text),
                           unbiased_text=format_text_into_paragraphs(unbiased_text),
                           lean=lean)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)