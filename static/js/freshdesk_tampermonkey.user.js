// ==UserScript==
// @name         Sidecar → Freshdesk Auto Draft (FINAL STABLE)
// @namespace    sidecar
// @version      6.0
// @description  Sends ticket data to sidecar iframe via postMessage
// @match        https://*.freshdesk.com/a/tickets/*
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  const SIDECAR_BASE = "https://futurehub-sidecar-production.up.railway.app";
  const SIDECAR_PATH = "/sidecar/";
  const IFRAME_ID = "sidecar-iframe";
  const POLL_INTERVAL = 1500;
  const LOG = "[TM]";

  let lastSentTicketId = null;

  function log(...args) {
    console.log(LOG, ...args);
  }

  // -------------------------------------------------
  // 1. Extract ticket ID from Freshdesk SPA URL
  //    Format: /a/tickets/17 or /a/tickets/17/...
  // -------------------------------------------------
  function getTicketId() {
    const match = window.location.pathname.match(/\/a\/tickets\/(\d+)/);
    return match ? parseInt(match[1], 10) : null;
  }

  // -------------------------------------------------
  // 2. Scrape ticket subject from DOM
  // -------------------------------------------------
  function extractSubject() {
    const el =
      document.querySelector('[data-testid="ticket-subject"]') ||
      document.querySelector(".ticket-subject-heading") ||
      document.querySelector(".ticket-header") ||
      document.querySelector('[class*="subject"]');
    if (!el) return "";
    const firstLine = (el.innerText || "")
      .split("\n")
      .map(function (s) { return s.trim(); })
      .filter(Boolean)[0] || "";
    return firstLine.replace("Add AI summary", "").trim();
  }

  // -------------------------------------------------
  // 3. Scrape latest customer message from DOM
  // -------------------------------------------------
  function extractDescription() {
    // Try the ticket description first
    const descEl = document.querySelector(".ticket-description .text__content");
    if (descEl) {
      const text = (descEl.innerText || "").trim();
      if (text.length > 20) return text;
    }
    // Fall back to longest conversation node
    const nodes = Array.from(document.querySelectorAll(".text__content"));
    const texts = nodes
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
  // 4. Find or inject the sidecar iframe
  // -------------------------------------------------
  function getOrCreateIframe() {
    var iframe = document.getElementById(IFRAME_ID);
    if (iframe) return iframe;

    // Look for existing Freshdesk Marketplace sidebar iframe
    var marketplaceIframes = document.querySelectorAll(
      'iframe[src*="futurehub-sidecar"], iframe[src*="railway.app"]'
    );
    if (marketplaceIframes.length > 0) {
      iframe = marketplaceIframes[0];
      iframe.id = IFRAME_ID;
      log("Found existing marketplace iframe");
      return iframe;
    }

    // Inject our own sidebar iframe
    iframe = document.createElement("iframe");
    iframe.id = IFRAME_ID;
    iframe.src = SIDECAR_BASE + SIDECAR_PATH;
    iframe.style.cssText =
      "position:fixed;right:0;top:60px;width:420px;height:calc(100vh - 60px);" +
      "border:none;z-index:99999;background:#fff;box-shadow:-2px 0 8px rgba(0,0,0,0.12);";
    document.body.appendChild(iframe);
    log("Injected sidecar iframe");
    return iframe;
  }

  // -------------------------------------------------
  // 5. Send TICKET_DATA to iframe via postMessage
  // -------------------------------------------------
  function sendTicketData(iframe, ticketId, subject, description) {
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
  // 6. Main loop — detect ticket, scrape, send
  // -------------------------------------------------
  function poll() {
    var ticketId = getTicketId();
    if (!ticketId) return;

    // Only re-send when navigating to a different ticket
    if (ticketId === lastSentTicketId) return;

    var subject = extractSubject();
    var description = extractDescription();

    // Wait until DOM has loaded enough content
    if (!subject && !description) {
      log("Waiting for DOM content for ticket", ticketId);
      return;
    }

    var iframe = getOrCreateIframe();

    // If iframe just injected, wait for it to load before posting
    if (!iframe._loaded) {
      iframe.addEventListener(
        "load",
        function () {
          iframe._loaded = true;
          log("Iframe loaded, dispatching TICKET_DATA");
          sendTicketData(iframe, ticketId, subject, description);
          lastSentTicketId = ticketId;
        },
        { once: true }
      );
      // If already loaded (cached), the load event won't fire again
      if (iframe.contentWindow) {
        try {
          // Test if contentWindow is accessible (same won't be for cross-origin,
          // but postMessage still works)
          setTimeout(function () {
            if (!iframe._loaded) {
              iframe._loaded = true;
              log("Iframe ready (timeout fallback), dispatching TICKET_DATA");
              sendTicketData(iframe, ticketId, subject, description);
              lastSentTicketId = ticketId;
            }
          }, 2000);
        } catch (_e) {
          // cross-origin, wait for load event
        }
      }
      return;
    }

    sendTicketData(iframe, ticketId, subject, description);
    lastSentTicketId = ticketId;
  }

  // -------------------------------------------------
  // 7. Listen for INSERT_INTO_CRM from sidecar
  // -------------------------------------------------
  window.addEventListener("message", function (event) {
    if (!event.data || event.data.type !== "INSERT_INTO_CRM") return;

    log("Received INSERT_INTO_CRM from sidecar");

    var draft = event.data.draft || "";
    if (!draft) return;

    // Open reply editor if not already open
    var replyBtn =
      document.querySelector('button[data-test-id="ticket-action-reply"]') ||
      document.querySelector('button[aria-label="Reply"]');
    if (replyBtn) replyBtn.click();

    // Wait for Froala editor, then inject
    var attempts = 0;
    var editorInterval = setInterval(function () {
      var editor = document.querySelector(
        "div.fr-element.fr-view[contenteditable='true']"
      );
      if (editor && editor.offsetParent !== null) {
        clearInterval(editorInterval);
        editor.focus();
        editor.innerHTML = draft.replace(/\n/g, "<br>");
        editor.dispatchEvent(new Event("input", { bubbles: true }));
        log("Draft inserted into Freshdesk editor");
      }
      attempts++;
      if (attempts > 40) clearInterval(editorInterval);
    }, 250);
  });

  // -------------------------------------------------
  // 8. Start polling
  // -------------------------------------------------
  setInterval(poll, POLL_INTERVAL);
  log("v6.0 loaded — postMessage bridge active");
})();
