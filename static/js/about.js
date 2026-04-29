const typingRoles = [
    "AI Developer | System Builder | YouTuber | Video Editor",
    "Machine Learning Enthusiast | UI Lover | Problem Solver",
];

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

function initAboutTyping() {
    const target = document.getElementById("typing-line");
    if (!target) {
        return;
    }

    if (prefersReducedMotion.matches) {
        target.textContent = typingRoles[0];
        return;
    }

    let lineIndex = 0;
    let charIndex = 0;
    let deleting = false;

    function step() {
        const current = typingRoles[lineIndex];
        target.textContent = current.slice(0, charIndex);

        if (!deleting) {
            charIndex += 1;
            if (charIndex > current.length) {
                deleting = true;
                setTimeout(step, 1500);
                return;
            }
        } else {
            charIndex -= 1;
            if (charIndex < 0) {
                deleting = false;
                lineIndex = (lineIndex + 1) % typingRoles.length;
                charIndex = 0;
            }
        }

        setTimeout(step, deleting ? 18 : 34);
    }

    step();
}

function initAboutReveal() {
    if (prefersReducedMotion.matches) {
        document.querySelectorAll(".reveal").forEach(el => el.classList.add("visible"));
        return;
    }

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
            }
        });
    }, { threshold: 0.14 });

    document.querySelectorAll(".reveal").forEach(el => observer.observe(el));
}

function initAboutParticles() {
    const layer = document.getElementById("about-particles");
    if (!layer || prefersReducedMotion.matches) {
        return;
    }

    for (let i = 0; i < 34; i += 1) {
        const dot = document.createElement("span");
        const size = Math.random() * 3 + 2;
        dot.style.position = "absolute";
        dot.style.left = `${Math.random() * 100}%`;
        dot.style.top = `${Math.random() * 100}%`;
        dot.style.width = `${size}px`;
        dot.style.height = `${size}px`;
        dot.style.borderRadius = "999px";
        dot.style.background = i % 3 === 0 ? "rgba(255,79,179,0.38)" : "rgba(89,243,255,0.4)";
        dot.style.boxShadow = "0 0 16px rgba(89,243,255,0.22)";
        dot.style.animation = `floatDot ${12 + Math.random() * 14}s ease-in-out ${Math.random() * 4}s infinite`;
        layer.appendChild(dot);
    }

    const style = document.createElement("style");
    style.textContent = `
        @keyframes floatDot {
            0%, 100% { transform: translate3d(0, 0, 0) scale(1); opacity: 0.45; }
            50% { transform: translate3d(12px, -16px, 0) scale(1.15); opacity: 0.9; }
        }
    `;
    document.head.appendChild(style);
}

function initScrollProgress() {
    const bar = document.getElementById("scroll-progress");
    if (!bar) {
        return;
    }

    window.addEventListener("scroll", () => {
        const doc = document.documentElement;
        const max = doc.scrollHeight - doc.clientHeight;
        const ratio = max > 0 ? (doc.scrollTop / max) * 100 : 0;
        bar.style.width = `${ratio}%`;
    }, { passive: true });
}

function initCursorGlow() {
    const glow = document.getElementById("cursor-glow");
    if (!glow || window.matchMedia("(pointer: coarse)").matches || prefersReducedMotion.matches) {
        if (glow) {
            glow.style.display = "none";
        }
        return;
    }

    window.addEventListener("mousemove", event => {
        glow.style.left = `${event.clientX}px`;
        glow.style.top = `${event.clientY}px`;
    });
}

function initAboutMobileMenu() {
    const button = document.getElementById("about-mobile-menu-button");
    const menu = document.getElementById("about-mobile-menu");
    if (!button || !menu) {
        return;
    }

    const setOpen = open => {
        button.setAttribute("aria-expanded", String(open));
        button.classList.toggle("is-open", open);
        menu.hidden = !open;
        menu.classList.toggle("is-open", open);
    };

    setOpen(false);

    button.addEventListener("click", () => {
        const isOpen = button.getAttribute("aria-expanded") === "true";
        setOpen(!isOpen);
    });

    menu.querySelectorAll("a").forEach(link => {
        link.addEventListener("click", () => setOpen(false));
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth >= 768) {
            setOpen(false);
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initAboutTyping();
    initAboutReveal();
    initAboutParticles();
    initScrollProgress();
    initCursorGlow();
    initAboutMobileMenu();
});
