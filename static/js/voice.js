/**
 * VoiceMail core voice engine.
 * Wraps the browser's SpeechSynthesis (text-to-speech) and
 * SpeechRecognition (speech-to-text) APIs behind a small, forgiving helper
 * object so every page can just call VoiceMail.speak(...) / VoiceMail.listen(...).
 *
 * Browser support note: SpeechRecognition is best supported in Chrome/Edge.
 * If it's unavailable, listen() rejects with a clear error and every page
 * falls back to plain text inputs (the app never becomes unusable).
 */

(function (window) {
  "use strict";

  const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;
  let currentUtterance = null;
  let recognitionInstance = null;
  let isListening = false;

  function speak(text, opts) {
    opts = opts || {};
    return new Promise(function (resolve) {
      if (!("speechSynthesis" in window)) {
        console.warn("Text-to-speech is not supported in this browser.");
        resolve();
        return;
      }
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.rate = opts.rate || 1.0;
      utter.pitch = opts.pitch || 1.0;
      utter.volume = opts.volume !== undefined ? opts.volume : 1.0;
      utter.onend = resolve;
      utter.onerror = resolve;
      currentUtterance = utter;
      window.speechSynthesis.speak(utter);

      const liveRegion = document.getElementById("live-region");
      if (liveRegion) liveRegion.textContent = text;
    });
  }

  function stopSpeaking() {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  }

  function isRecognitionSupported() {
    return !!SpeechRecognitionImpl;
  }

  /**
   * listen(): resolves with recognised text, or rejects with {code, message}.
   * options.timeoutMs: how long to wait for speech before giving up (default 8000).
   */
  function listen(options) {
    options = options || {};
    const timeoutMs = options.timeoutMs || 8000;

    return new Promise(function (resolve, reject) {
      if (!SpeechRecognitionImpl) {
        reject({ code: "unsupported", message: "Speech recognition is not supported in this browser. Please use Chrome or Edge, or type your answer instead." });
        return;
      }
      if (isListening) {
        reject({ code: "busy", message: "Already listening." });
        return;
      }

      const recognition = new SpeechRecognitionImpl();
      recognitionInstance = recognition;
      recognition.lang = options.lang || "en-US";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      let settled = false;
      const timer = setTimeout(function () {
        if (!settled) {
          settled = true;
          try { recognition.stop(); } catch (e) {}
          reject({ code: "timeout", message: "I didn't hear anything. Please try again." });
        }
      }, timeoutMs);

      recognition.onresult = function (event) {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        const transcript = event.results[0][0].transcript.trim();
        resolve(transcript);
      };

      recognition.onerror = function (event) {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        let message = "I couldn't understand that. Please try again.";
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          message = "Microphone access was denied. Please allow microphone access and try again.";
        } else if (event.error === "no-speech") {
          message = "I didn't hear anything. Please try again.";
        } else if (event.error === "audio-capture") {
          message = "No microphone was found. Please check your device and try again.";
        }
        reject({ code: event.error, message: message });
      };

      recognition.onend = function () {
        isListening = false;
      };

      try {
        isListening = true;
        recognition.start();
      } catch (e) {
        isListening = false;
        settled = true;
        clearTimeout(timer);
        reject({ code: "start-failed", message: "Could not start the microphone. Please try again." });
      }
    });
  }

  function stopListening() {
    if (recognitionInstance) {
      try { recognitionInstance.stop(); } catch (e) {}
    }
  }

  window.VoiceMail = window.VoiceMail || {};
  window.VoiceMail.speak = speak;
  window.VoiceMail.stopSpeaking = stopSpeaking;
  window.VoiceMail.listen = listen;
  window.VoiceMail.stopListening = stopListening;
  window.VoiceMail.isRecognitionSupported = isRecognitionSupported;

})(window);
