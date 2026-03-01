// ==UserScript==
// @name         Sidecar → Freshdesk Auto Draft (v9.0)
// @namespace    sidecar
// @version      9.0
// @description  Standalone window: opens sidecar in separate window, postMessage bridge
// @match        https://*.freshdesk.com/*
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  var SIDECAR_URL = "https://futurehub-sidecar-production.up.railway.app/sidecar/";
  var SIDECAR_ORIGIN = "https://futurehub-sidecar-production.up.railway.app";
  var WINDOW_NAME = "FH_SIDECAR_WINDOW";
  var ROUTE_CHECK_MS = 800;
  var LOG = "[TM]";

  var sidecarWindow = null;
  var lastSentTicketId = null;
  var lastPath = null;

  function log() {
    var args = [LOG];
    for (var i = 0; i < arguments.length; i++) args.push(arguments[i]);
    console.log.apply(console, args);
  }

  // -------------------------------------------------
  // Route detection
  // -------------------------------------------------
  function getTicketId() {
    var match = window.location.pathname.match(/\/a\/tickets\/(\d+)/);
    return match ? parseInt(match[1], 10) : null;
  }

  function isTicketRoute() {
    return /\/a\/tickets\/\d+/.test(window.location.pathname);
  }

  // -------------------------------------------------
  // DOM scraping
  // -------------------------------------------------
  function extractSubject() {
    var el =
      document.querySelector('[data-testid="ticket-subject"]') ||
      document.querySelector(".ticket-subject-heading") ||
      document.querySelector(".ticket-header") ||
      document.querySelector('[class*="subject"]');
    if (!el) return "";
    var firstLine = (el.innerText || "")
      .split("\n")
      .map(function (s) { return s.trim(); })
      .filter(Boolean)[0] || "";
    return firstLine.replace("Add AI summary", "").trim();
  }

  function extractDescription() {
    var descEl = document.querySelector(".ticket-description .text__content");
    if (descEl) {
      var text = (descEl.innerText || "").trim();
      if (text.length > 20) return text;
    }
    var nodes = Array.from(document.querySelectorAll(".text__content"));
    var texts = nodes
      .map(function (n) { return (n.innerText || "").trim(); })
      .filter(function (t) {
        return t.length > 40 &&
          !t.includes("reported via email") &&
          !t.startsWith("Status:");
      });
    if (!texts.length) return "";
    return texts
      .sort(function (a, b) { return b.length - a.length; })[0]
      .replace("Show more", "")
      .trim();
  }

  // -------------------------------------------------
  // Standalone window management
  // -------------------------------------------------
  function openOrReuseSidecar() {
    if (sidecarWindow && !sidecarWindow.closed) {
      sidecarWindow.focus();
      return sidecarWindow;
    }
    sidecarWindow = window.open(
      SIDECAR_URL,
      WINDOW_NAME,
      "width=500,height=900"
    );
    log("Opened sidecar window");
    return sidecarWindow;
  }

  // -------------------------------------------------
  // Send TICKET_DATA to standalone window
  // -------------------------------------------------
  function sendTicketData(ticketId, subject, description) {
    var win = openOrReuseSidecar();
    if (!win) {
      log("Failed to open sidecar window");
      return;
    }

    var message = {
      type: "TICKET_DATA",
      ticket: {
        id: ticketId,
        subject: subject,
        description_text: description,
        customer_name: "",
        originDomain: window.location.hostname
      }
    };

    // Window may still be loading — retry postMessage until ready
    var sent = false;
    var attempts = 0;
    var sendInterval = setInterval(function () {
      try {
        win.postMessage(message, SIDECAR_ORIGIN);
        if (!sent) {
          log("Sent TICKET_DATA to sidecar, ticket:", ticketId);
          sent = true;
        }
        clearInterval(sendInterval);
      } catch (_e) {
        // Window not ready yet
      }
      attempts++;
      if (attempts > 20) {
        clearInterval(sendInterval);
        log("Failed to send TICKET_DATA after retries");
      }
    }, 300);
  }

  // -------------------------------------------------
  // Insert into Froala editor
  // -------------------------------------------------
  function insertIntoEditor(draftText) {
    if (!draftText) return;

    var replyBtn =
      document.querySelector('button[data-test-id="ticket-action-reply"]') ||
      document.querySelector('button[aria-label="Reply"]');
    if (replyBtn) replyBtn.click();

    var attempts = 0;
    var editorInterval = setInterval(function () {
      var editor = document.querySelector(
        "div.fr-element.fr-view[contenteditable='true']"
      );
      if (editor && editor.offsetParent !== null) {
        clearInterval(editorInterval);
        editor.focus();
        editor.innerHTML = draftText.replace(/\n/g, "<br>");
        editor.dispatchEvent(new Event("input", { bubbles: true }));
        log("Draft auto-inserted into Freshdesk editor");
      }
      attempts++;
      if (attempts > 40) clearInterval(editorInterval);
    }, 250);
  }

  // -------------------------------------------------
  // Route watcher
  // -------------------------------------------------
  function routeCheck() {
    var currentPath = window.location.pathname;
    var pathChanged = currentPath !== lastPath;
    lastPath = currentPath;

    if (!isTicketRoute()) {
      if (pathChanged) {
        lastSentTicketId = null;
      }
      return;
    }

    var ticketId = getTicketId();
    if (!ticketId) return;
    if (ticketId === lastSentTicketId) return;

    var subject = extractSubject();
    var description = extractDescription();
    if (!subject && !description) return;

    sendTicketData(ticketId, subject, description);
    lastSentTicketId = ticketId;
  }

  // -------------------------------------------------
  // Listen for messages from sidecar window
  // -------------------------------------------------
  window.addEventListener("message", function (event) {
    if (event.origin !== SIDECAR_ORIGIN) return;
    if (!event.data) return;

    if (event.data.type === "DRAFT_READY") {
      var currentId = getTicketId();
      if (event.data.ticket_id && currentId && event.data.ticket_id !== currentId) {
        log("Ignoring stale DRAFT_READY for ticket", event.data.ticket_id, "current:", currentId);
        return;
      }
      log("Received DRAFT_READY, length:", (event.data.draft || "").length);
      insertIntoEditor(event.data.draft || "");
      return;
    }

    if (event.data.type === "INSERT_INTO_CRM") {
      log("Received INSERT_INTO_CRM");
      insertIntoEditor(event.data.draft || "");
    }
  });

  // -------------------------------------------------
  // Start
  // -------------------------------------------------
  setInterval(routeCheck, ROUTE_CHECK_MS);
  routeCheck();
  log("v9.0 loaded — standalone window mode");
})();
