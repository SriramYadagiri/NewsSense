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
        "Rewriting text in an unbiased form..."
    ];

let currentIndex = 0;
const messageElement = document.getElementById("loading-message");

setInterval(() => {
    currentIndex = (currentIndex + 1) % messages.length;
    messageElement.textContent = messages[currentIndex];
}, 5000); 

const toggleButton = document.getElementById("darkModeToggle");

function setDarkMode(enabled) {
    document.body.classList.toggle("dark-mode", enabled);
    localStorage.setItem("darkMode", enabled);
    toggleButton.textContent = enabled ? "Light Mode" : "Dark Mode";
    document.getElementById("logo-img").src = enabled ? "../static/images/logo-dark.png" : "../static/images/logo-light.png";
}

// Load saved preference
const saved = localStorage.getItem("darkMode") === "true";
setDarkMode(saved);

// Toggle on click
toggleButton.addEventListener("click", () => {
    setDarkMode(!document.body.classList.contains("dark-mode"));
    console.log("Dark mode toggled");
});