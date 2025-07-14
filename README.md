# NewsSense: Bias & Misinformation Detection

NewsSense is a Flask-based web app that allows users to upload or link to news articles and receive:
- A concise **summary**
- A detailed **bias score and rubric**
- **Highlighted biased phrases** and an **unbiased rewrite**
- **Flagged misinformation claims** based on trusted sources

---

## Features

- Uses OpenAI to summarize and detect bias
- Verifies factual claims using an agentic AI
- Supports article input via text, PDF, DOCX, or URL
- Live scrolling feed of **trusted news headlines**
- Interactive highlights with tooltips for bias and misinformation

---

## Installation

1. **Clone the repo**
```bash
git clone https://github.com/yourusername/newssense.git
cd newssense
```

2. **Create a virtual environment \(Optional\)**
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**\
Create a .env file in the root directory with the following content:
```
OPENAI_API_KEY=...
NEWS_API_KEY=...
```

5. **Run the App**
```bash
python app.py
```