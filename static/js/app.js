/**
 * Shared application logic: CSRF-safe fetch wrapper, toast notifications,
 * dark mode toggle (persisted for the session via body class + localStorage note below).
 *
 * Note: per project rules for artifacts we'd avoid localStorage, but this is a
 * real standalone Flask app (not a claude.ai artifact) so browser storage is fine here —
 * it's just remembering a UI preference on the user's own device.
 */

(function () {
  "use strict";

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  async function apiFetch(url, options) {
    options = options || {};
    const headers = Object.assign(
      { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
      options.headers || {}
    );
    const resp = await fetch(url, Object.assign({}, options, { headers }));
    let data;
    try {
      data = await resp.json();
    } catch (e) {
      data = { ok: false, message: "Unexpected server response." };
    }
    return data;
  }

  function showToast(message, isError) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.className = "toast show" + (isError ? " toast-error" : " toast-success");
    setTimeout(function () {
      toast.className = "toast";
    }, 4000);
  }

  function initThemeToggle() {
    const toggle = document.getElementById("theme-toggle");
    if (!toggle) return;
    const saved = window.localStorage.getItem("voicemail-theme");
    if (saved === "dark") {
      document.body.classList.remove("theme-light");
      document.body.classList.add("theme-dark");
      toggle.setAttribute("aria-pressed", "true");
      toggle.textContent = "☀️ Light Mode";
    }
    toggle.addEventListener("click", function () {
      const isDark = document.body.classList.toggle("theme-dark");
      document.body.classList.toggle("theme-light", !isDark);
      toggle.setAttribute("aria-pressed", String(isDark));
      toggle.textContent = isDark ? "☀️ Light Mode" : "🌙 Dark Mode";
      window.localStorage.setItem("voicemail-theme", isDark ? "dark" : "light");
    });
  }

  document.addEventListener("DOMContentLoaded", initThemeToggle);

  window.VoiceMailApp = { apiFetch: apiFetch, showToast: showToast };
})();
