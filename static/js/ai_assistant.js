// static/js/ai_assistant.js
// AI Assistant Client - Clean Version
// Single source of truth: GET /api/tickets/<id>

class AIAssistant {
  constructor(ticketId) {
    this.ticketId = ticketId;
    this.panel = document.getElementById("ai-assistant-panel");
    this.statusContainer = document.getElementById("ai-status-container");
    this.analysisResults = document.getElementById("analysis-results");
    this.analyzeBtn = document.getElementById("ai-analyze-btn");

    // State elements
    this.states = {
      idle: document.getElementById("state-idle"),
      processing: document.getElementById("state-processing"),
      failed: document.getElementById("state-failed"),
      timeout: document.getElementById("state-timeout"),
    };

    this.init();
  }

  init() {
    // Load ticket data once
    this.loadTicketData();
  }

  async loadTicketData() {
    try {
      const response = await fetch(`/api/tickets/${this.ticketId}`);
      if (!response.ok) throw new Error("Failed to fetch ticket");

      const ticket = await response.json();
      this.renderState(ticket);
    } catch (error) {
      console.error("Error loading ticket data:", error);
      this.renderState({ sidecar_status: "idle", ai_assistant_enabled: false });
    }
  }

  renderState(ticketData) {
    const status = ticketData.sidecar_status || "idle";

    // Hide all states first
    Object.values(this.states).forEach((el) => {
      if (el) el.classList.add("hidden");
    });
    this.analysisResults.classList.add("hidden");

    // Show appropriate state
    switch (status) {
      case "idle":
        if (this.states.idle) this.states.idle.classList.remove("hidden");
        break;

      case "processing":
        if (this.states.processing)
          this.states.processing.classList.remove("hidden");
        break;

      case "completed":
        this.loadAnalysisResults(ticketData);
        break;

      case "failed":
        if (this.states.failed) {
          this.states.failed.classList.remove("hidden");
          const errorMsg = document.getElementById("error-message");
          if (errorMsg) {
            errorMsg.textContent =
              ticketData.sidecar_error || "Unknown error occurred";
          }
        }
        break;

      case "timeout":
        if (this.states.timeout) this.states.timeout.classList.remove("hidden");
        break;
    }
  }

  async loadAnalysisResults(ticketData) {
    try {
      // For Day 7: Use mock data
      // Future: Retrieve actual sidecar response from database
      const mockAnalysis = this.getMockAnalysis();
      this.renderAnalysis(mockAnalysis, ticketData);
    } catch (error) {
      console.error("Error loading analysis results:", error);
      this.renderState({
        sidecar_status: "failed",
        sidecar_error: "Failed to load results",
      });
    }
  }

  renderAnalysis(data, ticketData) {
    if (!data) return;

    // Show analysis results section
    this.analysisResults.classList.remove("hidden");

    // Render intent & confidence
    const intentEl = document.getElementById("intent-value");
    const confidenceEl = document.getElementById("confidence-value");
    const confidenceBar = document.getElementById("confidence-bar");

    if (intentEl) {
      intentEl.textContent = this.formatIntent(data.intent);
    }

    if (confidenceEl && confidenceBar) {
      const confidence = Math.round(data.confidence * 100);
      confidenceEl.textContent = `${confidence}%`;
      confidenceBar.style.width = `${confidence}%`;

      // Color based on confidence
      if (confidence >= 85) {
        confidenceBar.className =
          "h-2 rounded-full transition-all duration-300 bg-green-500";
      } else if (confidence >= 70) {
        confidenceBar.className =
          "h-2 rounded-full transition-all duration-300 bg-yellow-500";
      } else {
        confidenceBar.className =
          "h-2 rounded-full transition-all duration-300 bg-red-500";
      }
    }

    // Render auto-send eligibility from ticket data
    this.renderAutoSendEligibility(ticketData);

    // Render summary
    const summaryEl = document.getElementById("summary-text");
    if (summaryEl && data.analysis) {
      summaryEl.textContent = data.analysis.summary || "No summary available";
    }

    // Render sentiment & urgency
    const sentimentEl = document.getElementById("sentiment-value");
    const urgencyEl = document.getElementById("urgency-value");

    if (sentimentEl && data.analysis) {
      sentimentEl.textContent = this.formatSentiment(data.analysis.sentiment);
    }

    if (urgencyEl && data.analysis) {
      urgencyEl.textContent = this.formatUrgency(data.analysis.urgency);
    }

    // Render draft preview if available
    if (data.draft) {
      this.renderDraftPreview(data.draft);
    }

    // Render suggestions
    if (data.suggestions && data.suggestions.length > 0) {
      this.renderSuggestions(data.suggestions);
    }
  }

  renderDraftPreview(draft) {
    const draftPreview = document.getElementById("draft-preview");
    const draftText = document.getElementById("draft-text");

    if (draftPreview && draftText) {
      draftText.textContent = draft;
      draftPreview.classList.remove("hidden");

      // Remove existing send button if present
      const existingBtn = document.getElementById("send-draft-btn");
      if (existingBtn) {
        existingBtn.remove();
      }

      // Create send button container
      const btnContainer = document.createElement("div");
      btnContainer.className = "mt-3 pt-3 border-t border-gray-200";

      const sendBtn = document.createElement("button");
      sendBtn.id = "send-draft-btn";
      sendBtn.type = "button";
      sendBtn.className =
        "w-full px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors";
      sendBtn.innerHTML = `
                <div class="flex items-center justify-center space-x-2">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                    </svg>
                    <span>Send Draft</span>
                </div>
            `;

      // Click handler opens confirmation modal
      sendBtn.addEventListener("click", () => {
        this.openSendConfirmation(draft);
      });

      btnContainer.appendChild(sendBtn);
      draftPreview.appendChild(btnContainer);
    }
  }

  renderAutoSendEligibility(ticketData) {
    try {
      // Get DOM elements
      const eligibleState = document.getElementById("eligible-state");
      const notEligibleState = document.getElementById("not-eligible-state");
      const notEvaluatedState = document.getElementById("not-evaluated-state");
      const eligibleReason = document.getElementById("eligible-reason");
      const notEligibleReason = document.getElementById("not-eligible-reason");
      const evaluatedTimestamp = document.getElementById("evaluated-timestamp");

      // Hide all states first
      if (eligibleState) eligibleState.classList.add("hidden");
      if (notEligibleState) notEligibleState.classList.add("hidden");
      if (notEvaluatedState) notEvaluatedState.classList.add("hidden");
      if (evaluatedTimestamp) evaluatedTimestamp.classList.add("hidden");

      // Show appropriate state based on ticket data
      if (ticketData.auto_send_evaluated_at) {
        if (ticketData.auto_send_eligible) {
          // Show eligible state
          if (eligibleState) {
            eligibleState.classList.remove("hidden");
            if (eligibleReason && ticketData.auto_send_reason) {
              eligibleReason.textContent = ticketData.auto_send_reason;
            }
          }
        } else {
          // Show not eligible state
          if (notEligibleState) {
            notEligibleState.classList.remove("hidden");
            if (notEligibleReason && ticketData.auto_send_reason) {
              notEligibleReason.textContent = ticketData.auto_send_reason;
            }
          }
        }

        // Show evaluation timestamp
        if (evaluatedTimestamp && ticketData.auto_send_evaluated_at) {
          evaluatedTimestamp.textContent = `Evaluated ${this.formatTimestamp(
            ticketData.auto_send_evaluated_at
          )}`;
          evaluatedTimestamp.classList.remove("hidden");
        }
      } else {
        // Show not evaluated state
        if (notEvaluatedState) {
          notEvaluatedState.classList.remove("hidden");
        }
      }
    } catch (error) {
      console.error("Error rendering auto-send eligibility:", error);
      const notEvaluatedState = document.getElementById("not-evaluated-state");
      if (notEvaluatedState) {
        notEvaluatedState.classList.remove("hidden");
      }
    }
  }

  renderSuggestions(suggestions) {
    const section = document.getElementById("suggestions-section");
    const list = document.getElementById("suggestions-list");

    if (!section || !list) return;

    list.innerHTML = "";

    suggestions.forEach((suggestion) => {
      const item = document.createElement("div");
      item.className =
        "p-3 bg-white border border-gray-200 rounded-lg hover:border-blue-300 transition-colors cursor-pointer";

      item.innerHTML = `
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <p class="text-sm font-medium text-gray-900">${this.escapeHtml(
                          suggestion.title
                        )}</p>
                        <p class="text-xs text-gray-500 mt-1">${this.escapeHtml(
                          suggestion.preview
                        )}</p>
                    </div>
                    ${
                      suggestion.confidence
                        ? `
                        <span class="ml-2 text-xs text-gray-500">${Math.round(
                          suggestion.confidence * 100
                        )}%</span>
                    `
                        : ""
                    }
                </div>
            `;

      list.appendChild(item);
    });

    section.classList.remove("hidden");
  }

  async openSendConfirmation(draft) {
    try {
      // Fetch ticket data for recipient info
      const response = await fetch(`/api/tickets/${this.ticketId}`);
      if (!response.ok) throw new Error("Failed to fetch ticket");

      const ticket = await response.json();

      // Open confirmation modal
      confirmationModal.open({
        draft: draft,
        recipient: ticket.customer_email,
        onConfirm: async () => {
          await this.sendDraft(draft);
        },
        onCancel: () => {
          console.log("Send cancelled by user");
        },
      });
    } catch (error) {
      console.error("Error opening confirmation:", error);
      alert("Failed to open confirmation. Please try again.");
    }
  }

  async sendDraft(draft) {
    try {
      const response = await fetch(
        `/api/tickets/${this.ticketId}/send-ai-draft`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: draft,
            ai_generated: true,
            approval_granted: true,
          }),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to send");
      }

      const result = await response.json();

      // Show success message
      this.showSuccess("Message sent successfully");

      // Reload page to show new reply
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } catch (error) {
      console.error("Error sending draft:", error);
      throw error; // Re-throw to be handled by modal
    }
  }

  showSuccess(message) {
    // Simple success notification
    const notification = document.createElement("div");
    notification.className =
      "fixed top-4 right-4 px-6 py-3 bg-green-600 text-white rounded-lg shadow-lg z-50";
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 3000);
  }

  formatIntent(intent) {
    const intentMap = {
      shipping_status: "Shipping Inquiry",
      general_question: "General Question",
      setup_help: "Setup Assistance",
      sync_panic: "Sync Issue",
      not_hashing: "Mining Problem",
      diagnostic_intake: "Technical Diagnosis",
      hardware_failure: "Hardware Issue",
    };
    return intentMap[intent] || intent;
  }

  formatSentiment(sentiment) {
    const sentimentMap = {
      positive: "😊 Positive",
      neutral: "😐 Neutral",
      negative: "😟 Negative",
      frustrated: "😤 Frustrated",
    };
    return sentimentMap[sentiment] || sentiment;
  }

  formatUrgency(urgency) {
    const urgencyMap = {
      low: "🟢 Low",
      medium: "🟡 Medium",
      high: "🔴 High",
    };
    return urgencyMap[urgency] || urgency;
  }

  formatTimestamp(isoString) {
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);

      if (diffMins < 1) return "just now";
      if (diffMins < 60)
        return `${diffMins} minute${diffMins > 1 ? "s" : ""} ago`;

      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24)
        return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;

      const diffDays = Math.floor(diffHours / 24);
      if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;

      return date.toLocaleDateString();
    } catch (error) {
      return isoString;
    }
  }

  getMockAnalysis() {
    // Day 7: Return mock data for display testing
    // This will be replaced with real sidecar response data
    return {
      intent: "shipping_status",
      confidence: 0.92,
      analysis: {
        summary: "Customer asking about order delivery status",
        sentiment: "neutral",
        urgency: "medium",
      },
      draft:
        "Thank you for contacting us about your order.\n\nI can help you check the status of your shipment. Could you please provide your order number so I can look up the tracking information?\n\nBest regards,\nFutureBit Support",
      suggestions: [
        {
          type: "canned_response",
          title: "Request Order Number",
          preview: "Ask customer for order number to track shipment",
          confidence: 0.95,
        },
        {
          type: "similar_ticket",
          title: "Similar Shipping Inquiry (#847)",
          preview: "Resolved shipping status question",
          confidence: 0.88,
        },
      ],
    };
  }

  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  show() {
    if (this.panel) {
      this.panel.classList.remove("hidden");
    }
  }

  hide() {
    if (this.panel) {
      this.panel.classList.add("hidden");
    }
  }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  const ticketIdEl = document.querySelector("[data-ticket-id]");
  if (ticketIdEl) {
    const ticketId = ticketIdEl.dataset.ticketId;
    window.aiAssistant = new AIAssistant(ticketId);
  }
});
