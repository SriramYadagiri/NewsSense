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