const state = {
    uploadedFilename: null,
    statusRotator: null,
};

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const prefersCoarsePointer = window.matchMedia("(pointer: coarse)");

const typingLines = [
    "Detect helmet violations, flag triple riding, and transform raw traffic clips into annotated evidence with a cinematic dashboard experience.",
    "Upload footage, run YOLOv8-powered analysis, and surface formal email-ready incidents in a modern futuristic interface.",
];

function initTypingAnimation() {
    const target = document.getElementById("typing-text");
    if (!target) {
        return;
    }

    if (prefersReducedMotion.matches) {
        target.textContent = typingLines[0];
        return;
    }

    let lineIndex = 0;
    let charIndex = 0;
    let deleting = false;

    function tick() {
        const line = typingLines[lineIndex];
        target.textContent = line.slice(0, charIndex);

        if (!deleting) {
            charIndex += 1;
            if (charIndex > line.length) {
                deleting = true;
                setTimeout(tick, 1600);
                return;
            }
        } else {
            charIndex -= 1;
            if (charIndex < 0) {
                deleting = false;
                lineIndex = (lineIndex + 1) % typingLines.length;
                charIndex = 0;
            }
        }

        const delay = deleting ? 18 : 34;
        setTimeout(tick, delay);
    }

    tick();
}

function initRevealAnimations() {
    if (prefersReducedMotion.matches) {
        document.querySelectorAll(".reveal").forEach(el => el.classList.add("visible"));
        return;
    }

    const observer = new IntersectionObserver(
        entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("visible");
                }
            });
        },
        { threshold: 0.16 }
    );

    document.querySelectorAll(".reveal").forEach(el => observer.observe(el));
}

function initTiltCards() {
    if (prefersReducedMotion.matches || prefersCoarsePointer.matches) {
        return;
    }

    document.querySelectorAll(".tilt-card").forEach(card => {
        card.addEventListener("mousemove", event => {
            const bounds = card.getBoundingClientRect();
            const offsetX = event.clientX - bounds.left;
            const offsetY = event.clientY - bounds.top;
            const rotateY = ((offsetX / bounds.width) - 0.5) * 9;
            const rotateX = ((offsetY / bounds.height) - 0.5) * -9;
            card.style.transform = `translateY(-10px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });

        card.addEventListener("mouseleave", () => {
            card.style.transform = "";
        });
    });
}

function initParticles() {
    const host = document.getElementById("particles");
    if (!host || prefersReducedMotion.matches) {
        return;
    }

    const count = 38;

    for (let i = 0; i < count; i += 1) {
        const dot = document.createElement("span");
        const size = Math.random() * 4 + 2;
        dot.style.position = "absolute";
        dot.style.left = `${Math.random() * 100}%`;
        dot.style.top = `${Math.random() * 100}%`;
        dot.style.width = `${size}px`;
        dot.style.height = `${size}px`;
        dot.style.borderRadius = "999px";
        dot.style.background = i % 2 === 0 ? "rgba(89,243,255,0.55)" : "rgba(139,92,246,0.35)";
        dot.style.boxShadow = "0 0 18px rgba(89,243,255,0.35)";
        dot.style.animation = `drift ${12 + Math.random() * 12}s ease-in-out ${Math.random() * 4}s infinite`;
        host.appendChild(dot);
    }
}

function initMobileMenu() {
    const button = document.getElementById("mobile-menu-button");
    const menu = document.getElementById("mobile-menu");
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

function setStatusPanel(show, text) {
    const panel = document.getElementById("status-panel");
    const statusText = document.getElementById("status-text");
    panel.classList.toggle("hidden", !show);
    if (text) {
        statusText.textContent = text;
    }
}

function startStatusRotation() {
    const messages = [
        "Preparing detector, loading frames, and annotating violations.",
        "Associating riders with motorcycles and evaluating helmet compliance.",
        "Saving processed footage, evidence snapshots, and result metadata.",
    ];
    let index = 0;
    setStatusPanel(true, messages[index]);

    clearInterval(state.statusRotator);
    state.statusRotator = setInterval(() => {
        index = (index + 1) % messages.length;
        setStatusPanel(true, messages[index]);
    }, 2200);
}

function stopStatusRotation() {
    clearInterval(state.statusRotator);
    state.statusRotator = null;
}

function updatePreview(file, src) {
    document.getElementById("preview-shell").classList.remove("hidden");
    document.getElementById("preview-shell").classList.add("animate-pop");
    document.getElementById("file-name").textContent = file.name;
    const video = document.getElementById("preview-video");
    video.src = src;
    video.load();
}

async function uploadVideo(formData) {
    const response = await fetch("/upload", {
        method: "POST",
        body: formData,
    });
    return response.json();
}

async function processVideo(filename) {
    const response = await fetch("/process", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ filename }),
    });
    return response.json();
}

function buildAnalysisSummary(result) {
    const counts = result.labels_detected || {};
    const mailLine = result.mail_sent
        ? "Evidence alert email was sent successfully."
        : (result.mail_message || "Email alert was not sent.");

    const items = [
        {
            icon: "AI",
            title: "Detection Outcome",
            text: `${result.violation_count ?? 0} high-priority incident markers were recorded in the processed clip.`,
        },
        {
            icon: "NH",
            title: "No Helmet Review",
            text: `${counts["No Helmet"] ?? 0} rider observations were flagged as helmet non-compliant.`,
        },
        {
            icon: "TR",
            title: "Triple Riding Review",
            text: `${counts["Triple Riding"] ?? 0} motorcycle groups were flagged for carrying three or more riders.`,
        },
        {
            icon: "ML",
            title: "Alert Pipeline",
            text: mailLine,
        },
    ];

    return items.map(item => `
        <div class="summary-row">
            <span class="summary-badge">${item.icon}</span>
            <div class="summary-copy">
                <strong>${item.title}</strong>
                <p>${item.text}</p>
            </div>
        </div>
    `).join("");
}

function renderSnapshots(result) {
    const container = document.getElementById("snapshots-container");
    const evidenceCount = document.getElementById("evidence-count");
    const snapshots = Array.isArray(result.snapshots) ? result.snapshots : [];

    evidenceCount.textContent = `${snapshots.length} ${snapshots.length === 1 ? "Frame" : "Frames"}`;
    container.innerHTML = "";

    if (!snapshots.length) {
        container.innerHTML = `
            <div class="summary-row sm:col-span-2">
                <span class="summary-badge">0</span>
                <div class="summary-copy">
                    <strong>No Evidence Frames Saved</strong>
                    <p>No snapshot was stored for this run. When a violation is captured, the same evidence image used for email alerts will appear here.</p>
                </div>
            </div>
        `;
        return;
    }

    snapshots.forEach((src, index) => {
        const card = document.createElement("article");
        card.className = "snapshot-card animate-pop";
        card.innerHTML = `
            <img src="${src}" alt="Violation evidence frame ${index + 1}">
            <div class="snapshot-meta">
                <strong>Evidence Frame ${index + 1}</strong>
                <p>This saved frame is available in the app and is used for the alert workflow.</p>
            </div>
        `;
        container.appendChild(card);
    });
}

function renderResults(result) {
    const panel = document.getElementById("results-panel");
    panel.classList.remove("hidden");
    panel.classList.add("animate-pop");

    document.getElementById("result-video").src = result.processed_video_url;
    document.getElementById("violation-count").textContent = result.violation_count ?? 0;
    document.getElementById("result-message").textContent = result.message || "Processing finished.";
    document.getElementById("analysis-summary").innerHTML = buildAnalysisSummary(result);

    const labelsContainer = document.getElementById("labels-container");
    labelsContainer.innerHTML = "";

    Object.entries(result.labels_detected || {}).forEach(([label, count]) => {
        const pill = document.createElement("span");
        pill.className = "label-pill";
        pill.textContent = `${label}: ${count}`;
        labelsContainer.appendChild(pill);
    });

    renderSnapshots(result);
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function initUploadFlow() {
    const form = document.getElementById("upload-form");
    const input = document.getElementById("video-input");
    const dropZone = document.getElementById("drop-zone");
    const processButton = document.getElementById("process-button");
    const uploadBadge = document.getElementById("upload-badge");

    ["dragenter", "dragover"].forEach(eventName => {
        dropZone.addEventListener(eventName, event => {
            event.preventDefault();
            dropZone.classList.add("drag-active");
        });
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropZone.addEventListener(eventName, event => {
            event.preventDefault();
            dropZone.classList.remove("drag-active");
        });
    });

    dropZone.addEventListener("drop", event => {
        const files = event.dataTransfer.files;
        if (files.length) {
            input.files = files;
            updatePreview(files[0], URL.createObjectURL(files[0]));
        }
    });

    input.addEventListener("change", () => {
        if (input.files.length) {
            updatePreview(input.files[0], URL.createObjectURL(input.files[0]));
        }
    });

    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (!input.files.length) {
            setStatusPanel(true, "Select a video file before uploading.");
            return;
        }

        const submitButton = document.getElementById("upload-button");
        submitButton.disabled = true;
        submitButton.textContent = "Uploading...";
        startStatusRotation();

        try {
            const formData = new FormData();
            formData.append("video", input.files[0]);
            const result = await uploadVideo(formData);

            if (!result.success) {
                throw new Error(result.message || "Upload failed.");
            }

            state.uploadedFilename = result.filename;
            processButton.disabled = false;
            uploadBadge.textContent = "Uploaded";
            setStatusPanel(true, result.message || "Upload completed.");
        } catch (error) {
            setStatusPanel(true, error.message);
        } finally {
            stopStatusRotation();
            submitButton.disabled = false;
            submitButton.textContent = "Upload Video";
        }
    });

    processButton.addEventListener("click", async () => {
        if (!state.uploadedFilename) {
            setStatusPanel(true, "Upload a video first.");
            return;
        }

        processButton.disabled = true;
        processButton.textContent = "Processing...";
        startStatusRotation();

        try {
            const result = await processVideo(state.uploadedFilename);
            if (!result.success) {
                throw new Error(result.message || "Processing failed.");
            }

            renderResults(result);
            const mailStatus = result.mail_message ? ` ${result.mail_message}` : "";
            setStatusPanel(true, `Analysis complete. Processed video and metrics are ready.${mailStatus}`);
        } catch (error) {
            setStatusPanel(true, error.message);
        } finally {
            stopStatusRotation();
            processButton.disabled = false;
            processButton.textContent = "Run Detection";
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initTypingAnimation();
    initRevealAnimations();
    initTiltCards();
    initParticles();
    initMobileMenu();
    initUploadFlow();
});
