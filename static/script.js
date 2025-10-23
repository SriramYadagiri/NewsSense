const form = document.getElementById('analyze-form');

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