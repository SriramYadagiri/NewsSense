import html
import io
import json
import os
import re
from dotenv import load_dotenv
from flask import Flask, request, render_template
import requests
from openai import OpenAI, BadRequestError
from bs4 import BeautifulSoup
from newspaper import Article
import concurrent.futures
from agents.misinfo_agent import agent
from agents.misinfo_agent import verify_claims_with_agent

import PyPDF2
from docx import Document

load_dotenv(override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_WORDS = 5000  # Limit for summarization

app = Flask(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"

def get_trusted_headlines():
    api_key = os.getenv("NEWS_API_KEY")
    base_url = "https://newsdata.io/api/1/latest"

    trusted_sources = "bbc.com,reuters.com,apnews.com,forbes.com,wsj.com"

    params = {
        "domainurl": trusted_sources,
        "language": "en",
        "country": "us",
        "category": "top",
        "size": 10,
        "apikey": api_key
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        articles = data.get("results", [])

        return [
            {
                "title": article["title"],
                "source": article["source_name"],
                "url": article["link"],
                "image": article["image_url"]
            }
            for article in articles if article["image_url"]
        ]

    except requests.exceptions.RequestException as e:
        print("NewsAPI Request Error:", e)
        return []

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

    try:
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
    
    except BadRequestError as e:
        if e.code == "context_length_exceeded":
            return {"error": f"Input is too large. Please limit input to {MAX_WORDS} words or fewer."}
    except Exception as e:
        print(e)
        return {"error": "An error occurred while processing the request."}

def determine_bias(text):
    text_file_path = 'prompts/bias_message.txt'
    with open(text_file_path, 'r') as file:
            initial_prompt = file.read()

    user_message = f"Analyze the following text for bias and provide a bias score:\n\n{text}"

    try:
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
        return json.loads(output)
    except BadRequestError as e:
        if e.code == "context_length_exceeded":
            return {"error": f"Input is too large. Please limit input to {MAX_WORDS} words or fewer."}
    except Exception as e:
        print(e)
        return {"error": "An error occurred while processing the request."}

def apply_combined_highlights(text, bias_passages, misinfo_claims):
    spans = []

    # Collect bias highlights
    for b in bias_passages:
        passage = b["passage"].strip()
        if passage in text:
            spans.append({
                "type": "bias",
                "passage": passage,
                "reason": b["reasoning"].strip()
            })

    # Collect misinformation highlights
    print(misinfo_claims)
    for m in misinfo_claims:
        claim = m["original-passage"].strip()
        print(claim)
        if claim in text:
            print("Made it through")
            spans.append({
                "type": "misinfo",
                "passage": claim,
                "verdict": m["verdict"].strip(),
                "reason": f"{m['verdict']}: {m['justification']}"
            })

    # Avoid overlapping inserts: sort by first occurrence index
    def start_index(span):
        return text.find(span["passage"])

    spans = sorted(spans, key=start_index)
    print(spans)

    # Track modified positions to avoid re-highlighting same passage
    modified = set()
    for span in spans:
        passage = span["passage"]
        if passage in modified:
            continue  # Already replaced
        reason = html.escape(span["reason"])
        escaped_passage = html.escape(passage)

        if span["type"] == "bias":
            tag = f'<span class="highlight bias" data-reason="{reason}">{escaped_passage}</span>'
        else:
            tag = f'<span class="highlight misinfo {span["verdict"].lower()}" data-reason="{reason}">{escaped_passage}</span>'

        text = text.replace(passage, tag, 1)
        modified.add(passage)

    return text

def unbias(text, highlighted_passages):
    text_file_path = 'prompts/unbias_message.txt'
    with open(text_file_path, 'r') as file:
        initial_prompt = file.read()
    
    try:
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
    except BadRequestError as e:
        if e.code == "context_length_exceeded":
            return {"error": f"Input is too large. Please limit input to {MAX_WORDS} words or fewer."}
    except Exception as e:
        print(e)
        return {"error": "An error occurred while processing the request."}

# --- Routes ---

@app.route('/')
def home():
    headlines = get_trusted_headlines()
    return render_template('index.html', trusted_articles=headlines)

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

        # Check for errors in summarization or bias detection
        if "error" in summary:
            return render_template("index.html", error=summary["error"])
        if "error" in bias:
            return render_template("index.html", error=bias["error"])

        future_misinfo = executor.submit(verify_claims_with_agent, raw_text)
        future_unbias = executor.submit(unbias, raw_text, bias["highlighted_passages"])

        misinfo_verdicts = future_misinfo.result()
        unbiased_text = future_unbias.result()

        if "error" in unbiased_text:
            return render_template("index.html", error=unbiased_text["error"])

    highlighted_text = apply_combined_highlights(
        raw_text, bias["highlighted_passages"], misinfo_verdicts
    )

    score = bias["bias_score"]
    rubric = bias["rubric_justification"]

    return render_template('result.html',
                           summary=summary,
                           original_text=raw_text,
                           highlighted_text=highlighted_text,
                           unbiased_text=unbiased_text,
                           score=score,
                           rubric=rubric,)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)