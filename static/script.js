/* ============================================================
   EduGenie — frontend logic (vanilla JS)
   Talks to the FastAPI backend via fetch(). No page reloads.
   ============================================================ */

(function () {
  "use strict";

  /* ---------- Small DOM helpers ---------- */
  const $ = (id) => document.getElementById(id);

  function escapeHtml(value) {
    const str = value == null ? "" : String(value);
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // Turn plain text (with newlines) into safe paragraphs.
  function textToParagraphs(text) {
    return String(text)
      .split(/\n{2,}/)
      .map((block) => block.trim())
      .filter(Boolean)
      .map((block) => "<p>" + escapeHtml(block).replace(/\n/g, "<br>") + "</p>")
      .join("");
  }

  /* ---------- UI state per section ---------- */
  function setLoading(section, isLoading) {
    const loader = $(section + "-loader");
    const button = document.querySelector('.btn[data-action="' + section + '"]');
    if (loader) loader.hidden = !isLoading;
    if (button) button.disabled = isLoading;
    if (isLoading) {
      const output = $(section + "-output");
      if (output) output.hidden = true;
    }
  }

  function showOutput(section, html, isError) {
    const output = $(section + "-output");
    if (!output) return;
    output.classList.toggle("output--error", Boolean(isError));
    output.innerHTML = html;
    output.hidden = false;
  }

  function showError(section, message) {
    showOutput(section, escapeHtml(message), true);
  }

  /* ---------- Network layer ---------- */
  async function callApi(url, options) {
    let response;
    try {
      response = await fetch(url, options);
    } catch (networkError) {
      throw new Error(
        "Couldn't reach EduGenie. Make sure the server is running, then try again."
      );
    }

    let data = null;
    try {
      data = await response.json();
    } catch (parseError) {
      data = null;
    }

    if (!response.ok) {
      const detail = data && (data.detail || data.error || data.message);
      throw new Error(detail || "The assistant ran into a problem. Please try again.");
    }
    return data || {};
  }

  function requireInput(section, value) {
    if (!value || !value.trim()) {
      showError(section, "Enter something first, then submit.");
      const input = $(section + "-input");
      if (input) input.focus();
      return false;
    }
    return true;
  }

  /* ============================================================
     SECTION HANDLERS
     ============================================================ */

  // 1. Question answering  ->  GET /qa?question=...
  async function handleQa() {
    const value = $("qa-input").value;
    if (!requireInput("qa", value)) return;

    setLoading("qa", true);
    try {
      const data = await callApi("/qa?question=" + encodeURIComponent(value.trim()));
      const answer = data.answer || "No answer was returned.";
      showOutput("qa", textToParagraphs(answer));
    } catch (err) {
      showError("qa", err.message);
    } finally {
      setLoading("qa", false);
    }
  }

  // 2. Concept explanation  ->  POST /explain { topic }
  async function handleExplain() {
    const value = $("explain-input").value;
    if (!requireInput("explain", value)) return;

    setLoading("explain", true);
    try {
      const data = await callApi("/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: value.trim() }),
      });
      const explanation = data.explanation || "No explanation was returned.";
      showOutput("explain", textToParagraphs(explanation));
    } catch (err) {
      showError("explain", err.message);
    } finally {
      setLoading("explain", false);
    }
  }

  // 3. Quiz generator  ->  POST /quiz { topic }
  async function handleQuiz() {
    const value = $("quiz-input").value;
    if (!requireInput("quiz", value)) return;

    setLoading("quiz", true);
    try {
      const data = await callApi("/quiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: value.trim() }),
      });
      const quiz = Array.isArray(data.quiz) ? data.quiz : [];
      if (quiz.length === 0) {
        showError("quiz", "No quiz questions came back. Try a different topic.");
        return;
      }
      renderQuiz(quiz);
    } catch (err) {
      showError("quiz", err.message);
    } finally {
      setLoading("quiz", false);
    }
  }

  // 4. Text summarizer  ->  POST /summarize { text }
  async function handleSummarize() {
    const value = $("summarize-input").value;
    if (!requireInput("summarize", value)) return;

    setLoading("summarize", true);
    try {
      const data = await callApi("/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: value.trim() }),
      });
      const summary = data.summary || "No summary was returned.";
      showOutput("summarize", textToParagraphs(summary));
    } catch (err) {
      showError("summarize", err.message);
    } finally {
      setLoading("summarize", false);
    }
  }

  // 5. Learning recommendations  ->  POST /learn/recommendations { topic }
  async function handleLearn() {
    const value = $("learn-input").value;
    if (!requireInput("learn", value)) return;

    setLoading("learn", true);
    try {
      const data = await callApi("/learn/recommendations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: value.trim() }),
      });
      renderLearningPath(data);
    } catch (err) {
      showError("learn", err.message);
    } finally {
      setLoading("learn", false);
    }
  }

  /* ============================================================
     RENDERERS
     ============================================================ */

  // Interactive MCQ rendering.
  function renderQuiz(quiz) {
    const output = $("quiz-output");
    output.classList.remove("output--error");
    output.innerHTML = "";

    quiz.forEach((item, index) => {
      const options = Array.isArray(item.options) ? item.options : [];
      const correctIndex = resolveCorrectIndex(item.answer, options);

      const wrap = document.createElement("div");
      wrap.className = "quiz-item";

      const q = document.createElement("p");
      q.className = "quiz-item__q";
      q.innerHTML =
        '<span class="quiz-item__num">' +
        (index + 1) +
        ".</span><span>" +
        escapeHtml(item.question || "Untitled question") +
        "</span>";
      wrap.appendChild(q);

      const list = document.createElement("ul");
      list.className = "quiz-options";

      const result = document.createElement("p");
      result.className = "quiz-item__result";

      options.forEach((option, optIndex) => {
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "quiz-option";
        btn.textContent = String(option);

        btn.addEventListener("click", function () {
          // Lock all options for this question once answered.
          const allButtons = list.querySelectorAll(".quiz-option");
          allButtons.forEach((b) => {
            b.disabled = true;
          });

          const isCorrectPick = optIndex === correctIndex;
          if (isCorrectPick) {
            btn.classList.add("is-correct");
            result.textContent = "Correct!";
            result.className = "quiz-item__result ok";
          } else {
            btn.classList.add("is-wrong");
            const correctBtn = allButtons[correctIndex];
            if (correctBtn) correctBtn.classList.add("is-correct");
            const correctText =
              correctIndex >= 0 && options[correctIndex] != null
                ? String(options[correctIndex])
                : "the highlighted option";
            result.textContent = "Not quite — the answer is " + correctText + ".";
            result.className = "quiz-item__result no";
          }
        });

        li.appendChild(btn);
        list.appendChild(li);
      });

      wrap.appendChild(list);
      wrap.appendChild(result);
      output.appendChild(wrap);
    });

    output.hidden = false;
  }

  // Figure out which option is correct, tolerant of several answer formats:
  // exact option text, a letter (A/B/C/D), or a numeric index.
  function resolveCorrectIndex(answer, options) {
    if (answer == null || !Array.isArray(options)) return -1;

    // Exact / trimmed text match.
    const answerStr = String(answer).trim();
    let idx = options.findIndex(
      (opt) => String(opt).trim().toLowerCase() === answerStr.toLowerCase()
    );
    if (idx !== -1) return idx;

    // Single letter (A, B, C, D...).
    if (/^[a-zA-Z]$/.test(answerStr)) {
      const letterIdx = answerStr.toUpperCase().charCodeAt(0) - 65;
      if (letterIdx >= 0 && letterIdx < options.length) return letterIdx;
    }

    // Numeric index (0-based or 1-based).
    if (/^\d+$/.test(answerStr)) {
      const n = parseInt(answerStr, 10);
      if (n >= 0 && n < options.length) return n;
      if (n - 1 >= 0 && n - 1 < options.length) return n - 1;
    }

    return -1;
  }

  // Beginner / Intermediate / Advanced roadmap.
  function renderLearningPath(data) {
    const output = $("learn-output");
    output.classList.remove("output--error");

    const levels = [
      { key: "beginner", label: "Beginner", cls: "level__badge--beginner" },
      { key: "intermediate", label: "Intermediate", cls: "level__badge--intermediate" },
      { key: "advanced", label: "Advanced", cls: "level__badge--advanced" },
    ];

    let html = "";
    let hasAny = false;

    levels.forEach((level) => {
      const items = normalizeList(data[level.key]);
      if (items.length === 0) return;
      hasAny = true;

      html += '<div class="level">';
      html += '<span class="level__badge ' + level.cls + '">' + level.label + "</span>";
      html += '<ul class="level__list">';
      items.forEach((item) => {
        html += "<li>" + escapeHtml(item) + "</li>";
      });
      html += "</ul></div>";
    });

    if (!hasAny) {
      showError("learn", "No recommendations came back. Try a different topic.");
      return;
    }

    output.innerHTML = html;
    output.hidden = false;
  }

  // Accept arrays of strings or arrays of objects, and flatten to strings.
  function normalizeList(value) {
    if (!Array.isArray(value)) return [];
    return value
      .map((item) => {
        if (item == null) return "";
        if (typeof item === "string") return item;
        if (typeof item === "object") {
          // Common shapes: { topic, resource } or { name, url }
          return Object.values(item)
            .filter((v) => v != null && v !== "")
            .join(" — ");
        }
        return String(item);
      })
      .map((s) => s.trim())
      .filter(Boolean);
  }

  /* ============================================================
     WIRING
     ============================================================ */
  const HANDLERS = {
    qa: handleQa,
    explain: handleExplain,
    quiz: handleQuiz,
    summarize: handleSummarize,
    learn: handleLearn,
  };

  function init() {
    // Click handlers on every submit button.
    document.querySelectorAll(".btn[data-action]").forEach((btn) => {
      const action = btn.getAttribute("data-action");
      const handler = HANDLERS[action];
      if (handler) btn.addEventListener("click", handler);
    });

    // Keyboard shortcut: Ctrl/Cmd + Enter submits the section you're typing in.
    Object.keys(HANDLERS).forEach((section) => {
      const input = $(section + "-input");
      if (!input) return;
      input.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
          event.preventDefault();
          HANDLERS[section]();
        }
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
