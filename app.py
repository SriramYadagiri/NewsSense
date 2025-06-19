from flask import Flask, render_template
from flask_session import Session
import openai
from newspaper import Article

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
    # extract input from form (text/url/file)
    # run your bias detection and summarization logic
    # return result.html with: highlighted_text, lean, unbiased_text
    return render_template('result.html', highlighted_text="highlighted_text", lean="lean_label", unbiased_text="unbiased_version")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
