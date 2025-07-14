const form = document.getElementById('analyze-form');
const overlay = document.getElementById('loading-overlay');

form.addEventListener('submit', () => {
    overlay.style.display = 'block';
});

const scroller = document.getElementById('headlineScroller');

function scrLeft() {
    scroller.scrollBy({ left: -300, behavior: 'smooth' });
}

function scrRight() {
    scroller.scrollBy({ left: 300, behavior: 'smooth' });
}

// Optional: Hide arrows if 4 or fewer cards
document.addEventListener('DOMContentLoaded', () => {
    const cardCount = document.querySelectorAll('.headline-card').length;
    if (cardCount <= 4) {
        document.querySelectorAll('.arrow').forEach(btn => btn.style.display = 'none');
    }
});

const messages = [
        "Analyzing article, please wait...",
        "Identifying bias...",
        "Scoring article...",
        "Summarizing content...",
        "Rewrting text in an unbiased form..."
    ];

let currentIndex = 0;
const messageElement = document.getElementById("loading-message");

setInterval(() => {
    currentIndex = (currentIndex + 1) % messages.length;
    messageElement.textContent = messages[currentIndex];
}, 5000); 