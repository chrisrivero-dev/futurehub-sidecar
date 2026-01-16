// static/js/ai_sidecar.js

// -------------------------------------
// Helper text inserted by Suggested Actions
// -------------------------------------
const ACTION_SNIPPETS = {
  "Request debug.log and getblockchaininfo output":
    "To help narrow this down, could you please share your debug.log file and the output of `getblockchaininfo`?\n\n",

  "Review logs for error patterns":
    "Once we have the logs, we’ll review them for any error patterns that could explain the behavior.\n\n",

  "Look up order in admin system":
    "Let me check the order details and see where things currently stand.\n\n",

  "Provide accurate tracking information":
    "I’ll confirm the latest tracking information and share an update with you.\n\n",
};
// -------------------------------------
// High-impact canned responses (v1)
// -------------------------------------
const CANNED_RESPONSES = {
  "Low or Zero Hashrate": {
    intents: ["not_hashing", "low_hashrate"],
    body: `Hi there,

If your Apollo II is still syncing, mining may appear stalled or show low or zero hashrate. This is expected behavior during initial sync.

Mining will not behave normally until the node is fully synced. What sync percentage does the dashboard currently show?

Best regards,
FutureBit Support`,
  },

  "Dashboard / Network Access Issues": {
    intents: ["dashboard_access", "network_issue"],
    body: `Hi there,

If apollo.local isn’t loading, try accessing the unit using its local IP address instead.

Please make sure the miner and your device are on the same network. Restarting the miner and router can also help.

Tools like Angry IP Scanner can help locate the unit on your local network.

Best regards,
FutureBit Support`,
  },

  "Node Sync Behavior (What’s Normal)": {
    intents: ["sync_delay", "setup_help"],
    body: `Hi there,

During initial setup, node sync can take a significant amount of time and this is expected.

Please ensure your internet connection is stable, keep the unit powered on, and avoid repeated reboots during sync.

If the sync appears stalled, a screenshot of the node status page will help confirm what’s happening.

Best regards,
FutureBit Support`,
  },

  "Firmware Update Instructions": {
    intents: ["firmware_update"],
    body: `Hi there,

You can update Apollo II firmware directly from the dashboard.

Go to Dashboard → Settings → Firmware, upload the latest firmware file, and allow the process to complete. The unit will reboot automatically when finished.

If you are asking about flashing storage media instead, let me know before proceeding.

Best regards,
FutureBit Support`,
  },

  "Request for More Information": {
    intents: ["general_support"],
    body: `Hi there,

To help troubleshoot this accurately, please share:
• Your product model
• Current firmware version
• A brief description of what you’re seeing
• A screenshot or photo, if available

With that information, I can guide next steps.

Best regards,
FutureBit Support`,
  },
};

// -------------------------------------
// Sidecar UI Controller
// -------------------------------------

class AISidecar {
  constructor() {
    this.form = document.getElementById("draft-request-form");
    this.emptyState = document.getElementById("empty-state");
    this.responseContainer = document.getElementById("response-container");
    this.generateBtn = document.getElementById("generate-btn");
    this.resetBtn = document.getElementById("reset-btn");

    this.init();
  }

  init() {
    // Form submission
    this.form.addEventListener("submit", (e) => {
      e.preventDefault();
      this.generateDraft();
    });

    // Reset button
    this.resetBtn.addEventListener("click", () => this.reset());

    // Copy draft button
    document
      .getElementById("copy-draft-btn")
      ?.addEventListener("click", () => this.copyDraft());

    // Insert draft button (UI stub)
    document
      .getElementById("insert-draft-btn")
      ?.addEventListener("click", () => {
        this.showToast("Insert functionality coming soon");
      });

    // Collapsible sections
    this.initCollapsibles();
  }
  async generateDraft() {
    const formData = new FormData(this.form);

    const payload = {
      subject: formData.get("subject"),
      latest_message: formData.get("latest_message"),
      conversation_history: [],
      customer_name: formData.get("customer_name") || undefined,
    };

    // Loading state
    this.generateBtn.disabled = true;
    const originalHTML = this.generateBtn.innerHTML;
    this.generateBtn.innerHTML = "Generating…";

    try {
      const response = await fetch("/api/v1/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error?.message || "Failed to generate draft");
      }

      console.log("FULL RESPONSE", data);

      // 🔗 Render everything from ONE place
      this.renderResponse(data);
    } catch (error) {
      console.error("Draft error:", error);
      this.showToast(error.message || "Failed to generate draft", "error");
    } finally {
      this.generateBtn.disabled = false;
      this.generateBtn.innerHTML = originalHTML;
    }
  }

  renderResponse(data) {
    // Hide empty state
    this.emptyState.classList.add("hidden");

    // Show the real cards (yesterday UI)
    document.getElementById("agent-guidance-card")?.classList.remove("hidden");
    document.getElementById("confidence-card")?.classList.remove("hidden");
    document.getElementById("draft-card")?.classList.remove("hidden");
    document.getElementById("actions-card")?.classList.remove("hidden");
    document.getElementById("quick-replies-card")?.classList.remove("hidden");
    document.getElementById("knowledge-card")?.classList.remove("hidden");
    document.getElementById("conversation-card")?.classList.remove("hidden");

    // 1. Agent Guidance
    this.renderGuidance(data.agent_guidance);

    // 2. Confidence & Risk
    this.renderConfidenceRisk(data.intent_classification);

    // 3. Intent Classification
    this.renderIntent(data.intent_classification);

    // 4. Draft Response
    this.renderDraft(data.draft);
    console.log("renderDraft called", data.draft);

    // 5. Suggested Actions
    this.renderSuggestedActions(
      data.agent_guidance.suggested_actions,
      data.intent_classification.primary_intent
    );

    // 6. Canned Response (if present)
    this.renderCannedResponse(data.agent_guidance.canned_response_suggestion);

    // 7. Conversation Context
    this.renderConversationContext();

    // Scroll to top of response
    this.responseContainer.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  renderGuidance(guidance) {
    // Badges
    const badgesContainer = document.getElementById("guidance-badges");
    let badges = "";

    if (guidance.auto_send_eligible) {
      badges += '<span class="badge badge-success">Auto-Send Eligible</span>';
    }

    if (guidance.requires_review) {
      badges += '<span class="badge badge-warning">Requires Review</span>';
    }

    badgesContainer.innerHTML = badges;

    // Reason & Recommendation
    document.getElementById("guidance-reason").textContent =
      guidance.reason || "N/A";
    document.getElementById("guidance-recommendation").textContent =
      guidance.recommendation || "N/A";
  }

  renderConfidenceRisk(classification) {
    const confidence = classification.confidence;

    // Confidence percentage
    const percentage = Math.round(confidence.overall * 100);
    document.getElementById("confidence-percentage").textContent =
      percentage + "%";

    // Confidence label badge
    const labelEl = document.getElementById("confidence-label");
    labelEl.textContent = confidence.label.toUpperCase();
    labelEl.className = `metric-badge confidence-${confidence.label}`;

    // Safety mode
    const safetyEl = document.getElementById("safety-mode");
    safetyEl.textContent = classification.safety_mode.toUpperCase();
    safetyEl.className = `metric-badge safety-${classification.safety_mode}`;

    // Ambiguity
    const ambiguityEl = document.getElementById("ambiguity-status");
    if (confidence.ambiguity_detected) {
      ambiguityEl.textContent = "DETECTED";
      ambiguityEl.className = "metric-badge badge-warning";
    } else {
      ambiguityEl.textContent = "NONE";
      ambiguityEl.className = "metric-badge badge-success";
    }
  }

  renderIntent(classification) {
    // Primary intent
    const primaryEl = document.getElementById("primary-intent");
    primaryEl.textContent = this.formatIntent(classification.primary_intent);

    // Secondary intents
    const secondaryContainer = document.getElementById(
      "secondary-intents-container"
    );
    const secondaryEl = document.getElementById("secondary-intents");

    if (
      classification.secondary_intents &&
      classification.secondary_intents.length > 0
    ) {
      secondaryEl.innerHTML = classification.secondary_intents
        .map(
          (intent) =>
            `<span class="intent-chip">${this.formatIntent(intent)}</span>`
        )
        .join("");
      secondaryContainer.classList.remove("hidden");
    } else {
      secondaryContainer.classList.add("hidden");
    }

    // Device behavior detected
    const deviceAlert = document.getElementById("device-behavior-alert");
    if (classification.device_behavior_detected) {
      deviceAlert.classList.remove("hidden");
    } else {
      deviceAlert.classList.add("hidden");
    }

    // Attempted actions
    const actionsContainer = document.getElementById(
      "attempted-actions-container"
    );
    const actionsEl = document.getElementById("attempted-actions");

    if (
      classification.attempted_actions &&
      classification.attempted_actions.length > 0
    ) {
      actionsEl.textContent = classification.attempted_actions.join(", ");
      actionsContainer.classList.remove("hidden");
    } else {
      actionsContainer.classList.add("hidden");
    }
  }

  renderDraft(draft) {
    // Draft type badge
    const typeBadge = document.getElementById("draft-type-badge");
    typeBadge.textContent = draft.type.toUpperCase();
    typeBadge.className = `badge draft-${draft.type}`;

    // Draft text
    document.getElementById("draft-text").value = draft.response_text;
  }

  renderSuggestedActions(actions, intent) {
    const list = document.getElementById("suggested-actions-list");
    list.innerHTML = "";

    // 1️⃣ Pull intent-matched canned responses
    const canned = this.getCannedForIntent(intent);

    // ⭐ Render canned responses FIRST (as buttons)
    canned.forEach((cannedItem) => {
      const li = document.createElement("li");
      li.className = "suggested-action canned clickable";

      li.innerHTML = `⭐ ${this.escapeHtml(cannedItem.title)}`;

      li.addEventListener("click", () => {
        const textarea = document.getElementById("draft-text");
        textarea.value = cannedItem.body;
        textarea.focus();

        this.showToast("Canned response inserted", "success");
      });

      list.appendChild(li);
    });

    // 2️⃣ Render normal suggested actions (non-clickable guidance)
    if (actions && actions.length > 0) {
      actions.forEach((action) => {
        const li = document.createElement("li");
        li.className = "suggested-action";
        li.textContent = action;
        list.appendChild(li);
      });
    }

    // 3️⃣ Empty state
    if (list.children.length === 0) {
      list.innerHTML =
        '<li class="help-text">No suggested actions available</li>';
    }
  }

  renderCannedResponse(cannedResponse) {
    const container = document.getElementById("canned-response-container");
    const btn = document.getElementById("canned-response-btn");
    const text = document.getElementById("canned-response-text");

    if (cannedResponse) {
      text.textContent = cannedResponse;
      container.classList.remove("hidden");

      btn.onclick = () => {
        this.showToast("Canned response functionality coming soon");
      };
    } else {
      container.classList.add("hidden");
    }
  }

  renderConversationContext() {
    const messagesContainer = document.getElementById("conversation-messages");

    // For now, show empty state since we're not passing history
    messagesContainer.innerHTML =
      '<p class="help-text">No conversation history in this request</p>';
  }

  initCollapsibles() {
    const toggles = document.querySelectorAll(".section-toggle");

    toggles.forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const content = toggle.nextElementSibling;
        toggle.classList.toggle("collapsed");
        content.classList.toggle("collapsed");
      });
    });
  }

  copyDraft() {
    const textarea = document.getElementById("draft-text");
    textarea.select();
    document.execCommand("copy");
    this.showToast("Draft copied to clipboard");
  }

  reset() {
    // Reset form
    this.form.reset();

    // Hide response, show empty state
    this.responseContainer.classList.add("hidden");
    this.emptyState.classList.remove("hidden");

    this.showToast("Form cleared");
  }

  showToast(message, type = "success") {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = `toast toast-${type}`;
    toast.classList.remove("hidden");

    setTimeout(() => {
      toast.classList.add("hidden");
    }, 3000);
  }

  formatIntent(intent) {
    return intent
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }
  getCannedForIntent(intent) {
    return Object.values(CANNED_RESPONSES).filter((c) =>
      c.intents.includes(intent)
    );
  }

  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  new AISidecar();
});
