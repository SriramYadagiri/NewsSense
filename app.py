import html
import io
import json
import os
import re
from dotenv import load_dotenv
from flask import Flask, request, render_template
import requests
from openai import OpenAI
from bs4 import BeautifulSoup
from newspaper import Article
import concurrent.futures

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
    return "".join(formatted)


def scrape_with_newspaper_or_fallback(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        if article.text.strip():
            return article.text
    except Exception as e:
        print("Newspaper3k failed:", e)

    # fallback to BeautifulSoup
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        paragraphs = soup.find_all('p')
        return ''.join(p.get_text() for p in paragraphs if p.get_text(strip=True))
    except Exception as e:
        print("Requests + BS4 scraping failed:", e)
        return ""

def summarize_article(text):
    text_file_path = 'prompts/summary_message.txt'
    with open(text_file_path, 'r') as file:
            initial_prompt = file.read()

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": initial_prompt},
            {"role": "user", "content": "Summarize the following article:\n\n" + text}
        ],
        temperature=0,
        top_p=1,
        max_tokens=1000
    )

    output = response.choices[0].message.content.strip()
    return output

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
        temperature=0,
        top_p=1,
        max_tokens=1500
    )

    output = response.choices[0].message.content.strip()
    print("Bias Analysis: " + output)
    return json.loads(output)

def highlight_bias(text, highlighted_passages):
    for obj in highlighted_passages:
        passage = obj["passage"].strip()
        reasoning = obj["reasoning"].strip()

        escaped_passage = html.escape(passage)
        escaped_reasoning = html.escape(reasoning)

        if passage in text:
            replacement = (
                f'<span class="highlight" data-reason="{escaped_reasoning}">{escaped_passage}</span>'
            )
            text = text.replace(passage, replacement, 1)
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
        temperature=0,
        top_p=1,
        max_tokens=1500
    )
    
    output = response.choices[0].message.content.strip()
    return output

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
        raw_text = scrape_with_newspaper_or_fallback(article_url)
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

    # Run summarization, bias detection, and unbiasing in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_summary = executor.submit(summarize_article, raw_text)
        future_bias = executor.submit(determine_bias, raw_text)

        summary = future_summary.result()
        bias = future_bias.result()

        future_unbias = executor.submit(unbias, raw_text, bias["highlighted_passages"])
        unbiased_text = future_unbias.result()

    highlighted_text = highlight_bias(raw_text, bias["highlighted_passages"])
    score = bias["bias_score"]
    rubric = bias["rubric_justification"]

    return render_template('result.html',
                           summary=summary,
                           original_text=format_text_into_paragraphs(raw_text),
                           highlighted_text=format_text_into_paragraphs(highlighted_text),
                           unbiased_text=format_text_into_paragraphs(unbiased_text),
                           score=score,
                           rubric=rubric,)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)