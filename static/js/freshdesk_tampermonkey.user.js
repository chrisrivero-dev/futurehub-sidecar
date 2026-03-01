// ==UserScript==
// @name         Sidecar → Freshdesk Auto Draft (v8.0)
// @namespace    sidecar
// @version      8.0
// @description  SPA-aware: injects/hides iframe on ticket routes, auto-inserts drafts
// @match        https://*.freshdesk.com/*
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  var SIDECAR_BASE = "https://futurehub-sidecar-production.up.railway.app";
  var SIDECAR_PATH = "/sidecar/";
  var IFRAME_ID = "sidecar-iframe";
  var ROUTE_CHECK_MS = 800;
  var LOG = "[TM]";

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
  // Iframe management
  // -------------------------------------------------
  function getIframe() {
    return document.getElementById(IFRAME_ID);
  }

  function showIframe() {
    var iframe = getIframe();
    if (iframe) {
      iframe.style.display = "";
      return iframe;
    }

    // Check for marketplace iframe first
    var marketplaceIframes = document.querySelectorAll(
      'iframe[src*="futurehub-sidecar"], iframe[src*="railway.app"]'
    );
    if (marketplaceIframes.length > 0) {
      iframe = marketplaceIframes[0];
      iframe.id = IFRAME_ID;
      iframe._loaded = true;
      log("Found existing marketplace iframe");
      return iframe;
    }

    // Create new
    iframe = document.createElement("iframe");
    iframe.id = IFRAME_ID;
    iframe.src = SIDECAR_BASE + SIDECAR_PATH;
    iframe.style.cssText =
      "position:fixed;right:0;top:60px;width:420px;height:calc(100vh - 60px);" +
      "border:none;z-index:99999;background:#fff;box-shadow:-2px 0 8px rgba(0,0,0,0.12);";
    document.body.appendChild(iframe);

    iframe.addEventListener("load", function () {
      iframe._loaded = true;
    }, { once: true });

    log("Injected sidecar iframe");
    return iframe;
  }

  function hideIframe() {
    var iframe = getIframe();
    if (iframe) {
      iframe.style.display = "none";
    }
  }

  // -------------------------------------------------
  // Send TICKET_DATA
  // -------------------------------------------------
  function sendTicketData(iframe, ticketId, subject, description) {
    if (!iframe || !iframe.contentWindow) return;
    var message = {
      type: "TICKET_DATA",
      ticket: {
        id: ticketId,
        subject: subject,
        description_text: description,
        customer_name: ""
      }
    };
    log("Sending ticket ID:", ticketId, "subject:", subject.slice(0, 60));
    iframe.contentWindow.postMessage(message, SIDECAR_BASE);
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
  // Route watcher — single interval handles all SPA nav
  // -------------------------------------------------
  function routeCheck() {
    var currentPath = window.location.pathname;
    var pathChanged = currentPath !== lastPath;
    lastPath = currentPath;

    if (!isTicketRoute()) {
      // Not on a ticket page — hide iframe, reset state
      hideIframe();
      if (pathChanged) {
        lastSentTicketId = null;
      }
      return;
    }

    // On a ticket page
    var ticketId = getTicketId();
    if (!ticketId) return;

    var iframe = showIframe();

    // Only send data once per ticket
    if (ticketId === lastSentTicketId) return;

    var subject = extractSubject();
    var description = extractDescription();
    if (!subject && !description) return; // DOM not ready yet

    if (!iframe._loaded) {
      // Wait for load then send
      var onLoad = function () {
        iframe._loaded = true;
        sendTicketData(iframe, ticketId, subject, description);
        lastSentTicketId = ticketId;
      };
      iframe.addEventListener("load", onLoad, { once: true });
      // Timeout fallback
      setTimeout(function () {
        if (!iframe._loaded) onLoad();
      }, 2000);
      return;
    }

    sendTicketData(iframe, ticketId, subject, description);
    lastSentTicketId = ticketId;
  }

  // -------------------------------------------------
  // Listen for messages from sidecar
  // -------------------------------------------------
  window.addEventListener("message", function (event) {
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
  routeCheck(); // immediate first check
  log("v8.0 loaded — SPA-aware route watcher active");
})();
