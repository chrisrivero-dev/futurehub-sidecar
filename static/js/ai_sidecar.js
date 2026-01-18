// static/js/ai_sidecar.js

// -------------------------------------
// Helper text inserted by Suggested Actions
// -------------------------------------
const ACTION_SNIPPETS = {
  "Request debug.log and getblockchaininfo output":
    "To help narrow this down, could you please share your debug.log file and the output of `getblockchaininfo`?\n\n",

  "Review logs for error patterns":
    "Once we have the logs, we'll review them for any error patterns that could explain the behavior.\n\n",

  "Look up order in admin system":
    "Let me check the order details and see where things currently stand.\n\n",

  "Provide accurate tracking information":
    "I'll confirm the latest tracking information and share an update with you.\n\n",
};

// -------------------------------------
// Intent -> Recommended canned response (v1)
// Used ONLY for recommendation/highlight.
// Actual dropdown content is loaded from /static/data/canned_responses.json
// -------------------------------------
const CANNED_RESPONSES = {
  "Low or Zero Hashrate": {
    intents: ["not_hashing", "low_hashrate"],
  },
  "Dashboard / Network Access Issues": {
    intents: ["dashboard_access", "network_issue"],
  },
  "Node Sync Behavior (What's Normal)": {
    intents: ["sync_delay", "setup_help"],
  },
  "Firmware Update Instructions": {
    intents: ["firmware_update"],
  },
  "Request for More Information": {
    intents: ["general_support"],
  },
};

// -------------------------------------
// Main AISidecar Class
// -------------------------------------
class AISidecar {
  constructor() {
    this.form = document.getElementById("draft-request-form");
    this.emptyState = document.getElementById("empty-state");
    this.responseContainer = document.getElementById("response-container");
    this.generateBtn = document.getElementById("generate-btn");
    this.resetBtn = document.getElementById("reset-btn");

    // Draft textarea (where inserts should go)
    this.draftTextarea =
      document.getElementById("draft-text") ||
      document.getElementById("draft-message-box");

    // -----------------------------
    // FOLLOW-UP QUESTIONS: HARD OFF BY DEFAULT
    // -----------------------------
    this.followupSection = document.getElementById("followup-section");
    if (this.followupSection) {
      this.followupSection.style.display = "none";
    }

    // Canned dropdown refs
    this.cannedBtn = document.getElementById("canned-dropdown-btn");
    this.cannedMenu = document.getElementById("canned-dropdown-menu");

    // State
    this.cannedResponses = [];
    this.recommendedCannedTitle = null;

    // Wire base UI
    this.init();

    // Load canned responses from JSON and render
    this.loadCannedResponses();
  }

  // -----------------------------
  // Init + event wiring
  // -----------------------------
  init() {
    // Form submission (prevent default, use JS)
    if (this.form) {
      this.form.addEventListener("submit", (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.generateDraft();
        return false;
      });
    }

    // Generate button click
    if (this.generateBtn) {
      this.generateBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        console.log("🔥 generateDraft() click");
        this.generateDraft();
      });
    }

    // Reset button
    if (this.resetBtn) {
      this.resetBtn.addEventListener("click", () => this.reset());
    }

    // Copy draft
    const copyBtn = document.getElementById("copy-draft-btn");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => this.copyDraft());
    }

    // Insert draft (stub)
    const insertBtn = document.getElementById("insert-draft-btn");
    if (insertBtn) {
      insertBtn.addEventListener("click", () => {
        this.showToast("Insert functionality coming soon");
      });
    }

    // Collapsible sections
    this.initCollapsibles();

    // Canned Responses dropdown open/close (wired ONCE)
    if (this.cannedBtn && this.cannedMenu) {
      this.cannedBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.toggleCannedDropdown();
      });

      document.addEventListener("click", (e) => {
        if (!this.cannedBtn || !this.cannedMenu) return;

        const clickedInside =
          this.cannedBtn.contains(e.target) ||
          this.cannedMenu.contains(e.target);

        if (!clickedInside) {
          this.closeCannedDropdown();
        }
      });
    }
  }

  // -----------------------------
  // Auto-Send Card Methods
  // -----------------------------
  showAutoSendCard(options) {
    const reason = options && options.reason ? options.reason : "";

    const card = document.getElementById("auto-send-card");
    if (card) {
      card.classList.remove("hidden");
    }

    const reasonEl = document.getElementById("auto-send-reason");
    if (reasonEl) {
      reasonEl.textContent = reason || "This ticket qualifies for auto-send.";
    }

    const badgeEl = document.getElementById("auto-send-badge");
    if (badgeEl) {
      badgeEl.classList.remove("hidden");
    }

    console.log("✅ Auto-send eligible:", reason);
  }

  hideAutoSendCard() {
    const card = document.getElementById("auto-send-card");
    if (card) {
      card.classList.add("hidden");
    }

    const badgeEl = document.getElementById("auto-send-badge");
    if (badgeEl) {
      badgeEl.classList.add("hidden");
    }
  }

  // -----------------------------
  // Canned Responses (JSON source of truth)
  // -----------------------------
  async loadCannedResponses() {
    try {
      const res = await fetch("/static/data/canned_responses.json");
      if (!res.ok) throw new Error("Failed to load canned responses");

      const data = await res.json();
      this.cannedResponses = Array.isArray(data) ? data : [];
      this.renderCannedResponses();
    } catch (err) {
      console.error("Canned responses load error:", err);
    }
  }

  getRecommendedCannedTitle(primaryIntent) {
    if (!primaryIntent) return null;

    const entries = Object.entries(CANNED_RESPONSES);
    for (let i = 0; i < entries.length; i++) {
      const title = entries[i][0];
      const item = entries[i][1];
      if (
        item &&
        Array.isArray(item.intents) &&
        item.intents.includes(primaryIntent)
      ) {
        return title;
      }
    }
    return null;
  }

  renderCannedResponses() {
    if (!this.cannedMenu) return;

    this.cannedMenu.innerHTML = "";

    if (
      !Array.isArray(this.cannedResponses) ||
      this.cannedResponses.length === 0
    ) {
      const empty = document.createElement("div");
      empty.className = "help-text";
      empty.textContent = "No canned responses available.";
      this.cannedMenu.appendChild(empty);
      return;
    }

    for (let i = 0; i < this.cannedResponses.length; i++) {
      const item = this.cannedResponses[i];

      const title = item?.title ? String(item.title) : "Untitled";
      const category = item?.category ? String(item.category) : "";
      const content = item?.content ? String(item.content) : "";

      // Recommended title is a TITLE, not an ID.
      const isRecommended =
        this.recommendedCannedTitle &&
        title === String(this.recommendedCannedTitle);

      const entry = document.createElement("button");
      entry.type = "button";
      entry.className = `canned-item${isRecommended ? " recommended" : ""}`;
      entry.setAttribute("role", "menuitem");
      entry.dataset.cannedId = item?.id || title;

      entry.innerHTML = `
        <div class="canned-title">
          ${isRecommended ? "★ " : ""}${title}
        </div>
        <div class="canned-meta">${category}</div>
      `;

      entry.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.insertCannedResponse({ title, content });
        this.closeCannedDropdown();
      });

      this.cannedMenu.appendChild(entry);
    }
  }

  insertCannedResponse(item) {
    if (!this.draftTextarea) return;

    const current = this.draftTextarea.value || "";
    const spacer = current.trim() ? "\n\n" : "";
    this.draftTextarea.value = current + spacer + (item.content || "");
    this.draftTextarea.focus();

    this.showToast(`Inserted: ${item.title}`);
  }

  toggleCannedDropdown() {
    if (!this.cannedMenu || !this.cannedBtn) return;

    const isOpen = this.cannedBtn.getAttribute("aria-expanded") === "true";
    this.cannedBtn.setAttribute("aria-expanded", String(!isOpen));
    this.cannedMenu.classList.toggle("hidden", isOpen);
  }

  closeCannedDropdown() {
    if (!this.cannedMenu || !this.cannedBtn) return;

    this.cannedMenu.classList.add("hidden");
    this.cannedBtn.setAttribute("aria-expanded", "false");
  }

  // -----------------------------
  // Draft generation
  // -----------------------------
  async generateDraft() {
    if (!this.form) return;

    const formData = new FormData(this.form);

    const payload = {
      subject: formData.get("subject"),
      latest_message: formData.get("latest_message"),
      conversation_history: [],
      customer_name: formData.get("customer_name") || undefined,
    };

    // Loading state
    const originalHTML = this.generateBtn ? this.generateBtn.innerHTML : "";
    if (this.generateBtn) {
      this.generateBtn.disabled = true;
      this.generateBtn.innerHTML = "Generating…";
    }

    try {
      const response = await fetch("/api/v1/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          (data && data.error && data.error.message) ||
            "Failed to generate draft"
        );
      }

      console.log("FULL RESPONSE", data);
      this.renderResponse(data);
    } catch (error) {
      console.error("Draft error:", error);
      this.showToast(
        (error && error.message) || "Failed to generate draft",
        "error"
      );
    } finally {
      if (this.generateBtn) {
        this.generateBtn.disabled = false;
        this.generateBtn.innerHTML = originalHTML;
      }
    }
  }

  resolveRecommendedCannedTitle(primaryIntent) {
    if (!primaryIntent) return null;

    for (const [title, cfg] of Object.entries(CANNED_RESPONSES)) {
      if (Array.isArray(cfg.intents) && cfg.intents.includes(primaryIntent)) {
        return title;
      }
    }
    return null;
  }

  // -----------------------------
  // Rendering
  // -----------------------------
  renderResponse(data) {
    // Hide empty state
    if (this.emptyState) this.emptyState.classList.add("hidden");

    // Show response container
    if (this.responseContainer) {
      this.responseContainer.classList.remove("hidden");
    }
    // -----------------------------
    // Auto-send visibility (read-only)
    // -----------------------------
    if (data?.auto_send === true) {
      console.log("✅ Auto-send eligible:", data.auto_send_reason);

      this.showAutoSendCard({
        reason: data.auto_send_reason || "Eligible for auto-send",
      });
    } else {
      this.hideAutoSendCard();
    }

    // -----------------------------
    // Auto-send visibility (read-only)
    // -----------------------------
    if (data && data.auto_send === true) {
      this.showAutoSendCard({ reason: data.auto_send_reason });
    } else {
      this.hideAutoSendCard();
    }

    // Show cards (if ids exist in DOM)
    const idsToShow = [
      "agent-guidance-card",
      "confidence-card",
      "draft-card",
      "actions-card",
      "quick-replies-card",
      "knowledge-card",
      "conversation-card",
    ];
    for (let i = 0; i < idsToShow.length; i++) {
      const el = document.getElementById(idsToShow[i]);
      if (el) el.classList.remove("hidden");
    }

    // 1. Agent Guidance
    this.renderGuidance(data ? data.agent_guidance : null);

    // 2. Confidence & Risk
    this.renderConfidenceRisk(data ? data.intent_classification : null);

    // 3. Intent Classification
    this.renderIntent(data ? data.intent_classification : null);

    // 4. Draft Response
    this.renderDraft(
      data ? data.draft : null,
      data ? data.agent_guidance : null
    );

    // 5. Follow-up Questions (Phase 3.1)
    const followups =
      data && data.agent_guidance
        ? data.agent_guidance.suggested_followups
        : null;

    this.renderFollowupQuestions(followups);

    // 6. Canned response recommendation + highlight
    const primaryIntent =
      data && data.intent_classification
        ? data.intent_classification.primary_intent
        : null;

    this.recommendedCannedTitle =
      this.resolveRecommendedCannedTitle(primaryIntent);

    // Re-render dropdown so highlight applies
    this.renderCannedResponses();

    // 7. Conversation Context
    this.renderConversationContext();

    // Scroll to top
    if (this.responseContainer && this.responseContainer.scrollIntoView) {
      this.responseContainer.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }

  renderGuidance(guidance) {
    const badgesContainer = document.getElementById("guidance-badges");
    let badges = "";

    if (guidance && guidance.auto_send_eligible) {
      badges += '<span class="badge badge-success">Auto-Send Eligible</span>';
    }
    if (guidance && guidance.requires_review) {
      badges += '<span class="badge badge-warning">Requires Review</span>';
    }
    if (badgesContainer) badgesContainer.innerHTML = badges;

    const reasonEl = document.getElementById("guidance-reason");
    const recEl = document.getElementById("guidance-recommendation");

    if (reasonEl) reasonEl.textContent = (guidance && guidance.reason) || "N/A";
    if (recEl)
      recEl.textContent = (guidance && guidance.recommendation) || "N/A";
  }

  renderConfidenceRisk(classification) {
    if (!classification || !classification.confidence) return;

    const confidence = classification.confidence;
    const percentage = Math.round((confidence.overall || 0) * 100);

    const pctEl = document.getElementById("confidence-percentage");
    if (pctEl) pctEl.textContent = percentage + "%";

    const labelEl = document.getElementById("confidence-label");
    if (labelEl) {
      const label = (confidence.label || "unknown").toLowerCase();
      labelEl.textContent = label.toUpperCase();
      labelEl.className = `metric-badge confidence-${label}`;
    }

    const safetyEl = document.getElementById("safety-mode");
    if (safetyEl) {
      const sm = (classification.safety_mode || "unknown").toLowerCase();
      safetyEl.textContent = sm.toUpperCase();
      safetyEl.className = `metric-badge safety-${sm}`;
    }

    const ambiguityEl = document.getElementById("ambiguity-status");
    if (ambiguityEl) {
      if (confidence.ambiguity_detected) {
        ambiguityEl.textContent = "DETECTED";
        ambiguityEl.className = "metric-badge badge-warning";
      } else {
        ambiguityEl.textContent = "NONE";
        ambiguityEl.className = "metric-badge badge-success";
      }
    }
  }

  renderIntent(classification) {
    if (!classification) return;

    const primaryEl = document.getElementById("primary-intent");
    if (primaryEl) {
      primaryEl.textContent = this.formatIntent(classification.primary_intent);
    }

    const secondaryContainer = document.getElementById(
      "secondary-intents-container"
    );
    const secondaryEl = document.getElementById("secondary-intents");

    if (
      secondaryContainer &&
      secondaryEl &&
      Array.isArray(classification.secondary_intents) &&
      classification.secondary_intents.length > 0
    ) {
      secondaryEl.innerHTML = classification.secondary_intents
        .map(
          (intent) =>
            `<span class="intent-chip">${this.formatIntent(intent)}</span>`
        )
        .join("");
      secondaryContainer.classList.remove("hidden");
    } else if (secondaryContainer) {
      secondaryContainer.classList.add("hidden");
    }

    const deviceAlert = document.getElementById("device-behavior-alert");
    if (deviceAlert) {
      if (classification.device_behavior_detected) {
        deviceAlert.classList.remove("hidden");
      } else {
        deviceAlert.classList.add("hidden");
      }
    }

    const actionsContainer = document.getElementById(
      "attempted-actions-container"
    );
    const actionsEl = document.getElementById("attempted-actions");

    if (
      actionsContainer &&
      actionsEl &&
      Array.isArray(classification.attempted_actions) &&
      classification.attempted_actions.length > 0
    ) {
      actionsEl.textContent = classification.attempted_actions.join(", ");
      actionsContainer.classList.remove("hidden");
    } else if (actionsContainer) {
      actionsContainer.classList.add("hidden");
    }
  }

  // -----------------------------
  // Draft rendering
  // -----------------------------
  renderDraft(draft, guidance) {
    console.log("RENDER DRAFT HIT", draft);

    const textarea = this.draftTextarea;
    if (!textarea) {
      console.warn("renderDraft: textarea not found");
      return;
    }

    let text = "";

    // ✅ Case 1: Expected (string)
    if (draft && typeof draft.response_text === "string") {
      text = draft.response_text;

      // ✅ Case 2: Nested response_text (YOUR CURRENT SHAPE)
    } else if (
      draft &&
      typeof draft.response_text === "object" &&
      typeof draft.response_text.response_text === "string"
    ) {
      text = draft.response_text.response_text;

      // ❌ Fallback (debug only)
    } else {
      console.warn("renderDraft: invalid draft payload", draft);
      textarea.value = "";
      return;
    }

    textarea.value = text;

    // Badge
    const sourceBadge = document.getElementById("draft-source-badge");
    if (sourceBadge && guidance) {
      if (guidance.auto_send_eligible) {
        sourceBadge.textContent = "AI Draft · Auto-Send Ready";
        sourceBadge.className = "badge badge-success";
      } else if (guidance.requires_review) {
        sourceBadge.textContent = "AI Draft · Review Required";
        sourceBadge.className = "badge badge-warning";
      } else {
        sourceBadge.textContent = "AI Draft";
        sourceBadge.className = "badge badge-neutral";
      }
    }
  }

  renderFollowupQuestions(followups) {
    const list = document.getElementById("suggested-actions-list");
    if (!list) return;

    list.innerHTML = "";

    const section = document.getElementById("followup-section");

    // HARD GATE: hide section unless followups exist
    if (!Array.isArray(followups) || followups.length === 0) {
      if (section) section.style.display = "none";
      return;
    }

    // Enable section only when followups exist
    if (section) section.style.display = "block";

    followups.forEach((f, index) => {
      // ✅ MATCH BACKEND SHAPE EXACTLY
      const text = f.question;

      if (!text) return;

      const item = document.createElement("button");
      item.type = "button";
      item.className = "followup-action";
      item.setAttribute("data-preview", f.key || "");

      item.innerHTML = `
        <span class="followup-index">${index + 1}</span>
        <span class="followup-text">${text}</span>
      `;

      item.title = text; // hover preview fallback

      item.addEventListener("click", () => {
        if (!this.draftTextarea) return;

        const cur = this.draftTextarea.value || "";
        const spacer = cur && !cur.endsWith("\n") ? "\n\n" : "";
        this.draftTextarea.value = cur + spacer + text;
        this.draftTextarea.focus();

        this.showToast("Inserted follow-up question");
      });

      list.appendChild(item);
    });
  }

  renderConversationContext() {
    const messagesContainer = document.getElementById("conversation-messages");
    if (!messagesContainer) return;

    messagesContainer.innerHTML =
      '<p class="help-text">No conversation history in this request</p>';
  }

  // ✅ Must exist, because init() calls it
  initCollapsibles() {
    const toggles = document.querySelectorAll(".section-toggle");
    toggles.forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const content = toggle.nextElementSibling;
        toggle.classList.toggle("collapsed");
        if (content) content.classList.toggle("collapsed");
      });
    });
  }

  copyDraft() {
    const textarea = document.getElementById("draft-text");
    if (!textarea) return;

    textarea.select();
    document.execCommand("copy");
    this.showToast("Draft copied to clipboard");
  }

  reset() {
    if (this.form) this.form.reset();

    if (this.responseContainer) this.responseContainer.classList.add("hidden");
    if (this.emptyState) this.emptyState.classList.remove("hidden");

    if (this.cannedMenu) this.cannedMenu.classList.add("hidden");
    if (this.cannedBtn) this.cannedBtn.setAttribute("aria-expanded", "false");

    if (this.draftTextarea) this.draftTextarea.value = "";

    // Hide auto-send card on reset
    this.hideAutoSendCard();

    this.showToast("Form cleared");
  }

  showToast(message, type = "success") {
    const toast = document.getElementById("toast");
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast toast-${type}`;
    toast.classList.remove("hidden");

    setTimeout(() => {
      toast.classList.add("hidden");
    }, 3000);
  }

  formatIntent(intent) {
    if (!intent) return "";
    return String(intent)
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }
}

// -------------------------------------
// Initialize on DOM Ready
// -------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  window.aiSidecar = new AISidecar();
});

// ------------------------------------
// Follow-up questions toggle (Phase 3.1)
// ------------------------------------
document.addEventListener("click", (e) => {
  if (!e.target.classList.contains("followups-toggle")) return;

  const list = e.target.nextElementSibling;
  if (!list) return;

  list.classList.toggle("hidden");

  e.target.textContent = list.classList.contains("hidden")
    ? "▼ Follow-up questions (optional)"
    : "▲ Follow-up questions (optional)";
});
