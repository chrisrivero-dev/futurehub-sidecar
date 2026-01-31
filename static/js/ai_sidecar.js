// static/js/ai_sidecar.js
// Executive Summary is derived from existing per-ticket signals.
// No analytics, no historical data, no AI calls.
// This is a deterministic view layer.

// -------------------------------------
// Helper text inserted by Suggested Actions
// -------------------------------------
const ACTION_SNIPPETS = {
  'Request debug.log and getblockchaininfo output':
    'To help narrow this down, could you please share your debug.log file and the output of `getblockchaininfo`?\n\n',

  'Review logs for error patterns':
    "Once we have the logs, we'll review them for any error patterns that could explain the behavior.\n\n",

  'Look up order in admin system':
    'Let me check the order details and see where things currently stand.\n\n',

  'Provide accurate tracking information':
    "I'll confirm the latest tracking information and share an update with you.\n\n",
};

// -------------------------------------
// Intent -> Recommended canned response (v1)
// Used ONLY for recommendation/highlight.
// Actual dropdown content is loaded from /static/data/canned_responses.json
// -------------------------------------
const CANNED_RESPONSES = {
  'Low or Zero Hashrate': {
    intents: ['not_hashing', 'low_hashrate'],
  },
  'Dashboard / Network Access Issues': {
    intents: ['dashboard_access', 'network_issue'],
  },
  "Node Sync Behavior (What's Normal)": {
    intents: ['sync_delay', 'setup_help'],
  },
  'Firmware Update Instructions': {
    intents: ['firmware_update'],
  },
  'Request for More Information': {
    intents: ['general_support'],
  },
};

class AISidecar {
  constructor() {
    this.panel = document.getElementById('ai-assistant-panel');
    this.form = document.getElementById('draft-request-form');
    this.emptyState = document.getElementById('empty-state');
    this.responseContainer = document.getElementById('response-container');
    this.generateBtn = document.getElementById('generate-btn');
    this.resetBtn = document.getElementById('reset-btn');

    this.draftTextarea =
      document.getElementById('draft-text') ||
      document.getElementById('draft-message-box');

    this.cannedBtn = document.getElementById('canned-dropdown-btn');
    this.cannedMenu = document.getElementById('canned-dropdown-menu');

    this.recommendedCannedTitle = null;
    this.cannedResponses = [];

    this.init();
    this.bindCollapseToggle();
    this.bindResetButton();
    this.loadCannedResponses();
  }
  // -----------------------------
  // Reset Button
  // -----------------------------
  bindResetButton() {
    if (!this.resetBtn) return;

    this.resetBtn.addEventListener('click', (e) => {
      e.stopPropagation();

      this.form?.reset();
      this.responseContainer?.classList.add('hidden');
      this.emptyState?.classList.remove('hidden');
      document.getElementById('auto-send-card')?.classList.add('hidden');

      this.hideAutoSendCard();
      this.showToast('Form cleared');
    });
  }

  // -----------------------------
  // Collapse / Expand
  // -----------------------------
  bindCollapseToggle() {
    const toggleBtn = document.getElementById('collapse-toggle');
    const wrapper = document.querySelector('.sidecar-wrapper');
    if (!toggleBtn || !wrapper) return;

    const chevron = toggleBtn.querySelector('.collapse-chevron');
    let isCollapsed = false;

    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();

      isCollapsed = !isCollapsed;
      wrapper.classList.toggle('sidecar-collapsed', isCollapsed);
      toggleBtn.setAttribute('aria-expanded', String(!isCollapsed));

      if (chevron) {
        chevron.style.transform = isCollapsed
          ? 'rotate(180deg)'
          : 'rotate(0deg)';
      }
    });
  }

  // -----------------------------
  // Init + event wiring
  // -----------------------------
  init() {
    // Form submission (prevent default, use JS)
    if (this.form) {
      this.form.addEventListener('submit', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.generateDraft();
        return false;
      });
    }

    // Generate button click
    if (this.generateBtn) {
      this.generateBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        console.log('🔥 generateDraft() click');
        this.generateDraft();
      });
    }

    // Copy draft
    const copyBtn = document.getElementById('copy-draft-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => this.copyDraft());
    }

    // Insert draft (stub)
    const insertBtn = document.getElementById('insert-draft-btn');
    if (insertBtn) {
      insertBtn.addEventListener('click', () => {
        this.showToast('Insert functionality coming soon');
      });
    }

    // Collapsible sections
    this.initCollapsibles();

    // Canned Responses dropdown open/close (wired ONCE)
    if (this.cannedBtn && this.cannedMenu) {
      this.cannedBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.toggleCannedDropdown();
      });

      document.addEventListener('click', (e) => {
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
  showAutoSendCard(options = {}) {
    const card = document.getElementById('auto-send-card');
    if (!card) return;

    card.classList.remove('hidden');

    const reasonEl = document.getElementById('auto-send-reason');
    if (reasonEl) {
      reasonEl.textContent =
        options.reason || 'This ticket qualifies for auto-send.';
    }

    const badgeEl = document.getElementById('auto-send-badge');
    if (badgeEl) badgeEl.classList.remove('hidden');

    // 🔒 SINGLE SOURCE OF TRUTH
    this.autoSendEligible = true;
  }

  hideAutoSendCard() {
    const card = document.getElementById('auto-send-card');
    if (card) {
      card.classList.add('hidden');
    }

    const badgeEl = document.getElementById('auto-send-badge');
    if (badgeEl) {
      badgeEl.classList.add('hidden');
    }
  }

  // -----------------------------
  // Canned Responses (JSON source of truth)
  // -----------------------------
  async loadCannedResponses() {
    try {
      const res = await fetch('/static/data/canned_responses.json');
      if (!res.ok) throw new Error('Failed to load canned responses');

      const data = await res.json();
      this.cannedResponses = Array.isArray(data) ? data : [];
      this.renderCannedResponses();
    } catch (err) {
      console.error('Canned responses load error:', err);
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

    this.cannedMenu.innerHTML = '';

    if (
      !Array.isArray(this.cannedResponses) ||
      this.cannedResponses.length === 0
    ) {
      const empty = document.createElement('div');
      empty.className = 'help-text';
      empty.textContent = 'No canned responses available.';
      this.cannedMenu.appendChild(empty);
      return;
    }

    for (let i = 0; i < this.cannedResponses.length; i++) {
      const item = this.cannedResponses[i];

      const title = item?.title ? String(item.title) : 'Untitled';
      const category = item?.category ? String(item.category) : '';
      const content = item?.content ? String(item.content) : '';

      // Recommended title is a TITLE, not an ID.
      const isRecommended =
        this.recommendedCannedTitle &&
        title === String(this.recommendedCannedTitle);

      const entry = document.createElement('button');
      entry.type = 'button';
      entry.className = `canned-item${isRecommended ? ' recommended' : ''}`;
      entry.setAttribute('role', 'menuitem');
      entry.dataset.cannedId = item?.id || title;

      entry.innerHTML = `
        <div class="canned-title">
          ${isRecommended ? '★ ' : ''}${title}
        </div>
        <div class="canned-meta">${category}</div>
      `;

      entry.addEventListener('click', (e) => {
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

    const current = this.draftTextarea.value || '';
    const spacer = current.trim() ? '\n\n' : '';
    this.draftTextarea.value = current + spacer + (item.content || '');
    this.draftTextarea.focus();

    this.showToast(`Inserted: ${item.title}`);
  }

  toggleCannedDropdown() {
    if (!this.cannedMenu || !this.cannedBtn) return;

    const isOpen = this.cannedBtn.getAttribute('aria-expanded') === 'true';
    this.cannedBtn.setAttribute('aria-expanded', String(!isOpen));
    this.cannedMenu.classList.toggle('hidden', isOpen);
  }

  closeCannedDropdown() {
    if (!this.cannedMenu || !this.cannedBtn) return;

    this.cannedMenu.classList.add('hidden');
    this.cannedBtn.setAttribute('aria-expanded', 'false');
  }

  // -----------------------------
  // Draft generation
  // -----------------------------
  async generateDraft() {
    if (!this.form) return;

    const formData = new FormData(this.form);

    const payload = {
      subject: formData.get('subject'),
      latest_message: formData.get('latest_message'),
      conversation_history: [],
      customer_name: formData.get('customer_name') || undefined,
    };

    // Loading state
    const originalHTML = this.generateBtn ? this.generateBtn.innerHTML : '';
    if (this.generateBtn) {
      this.generateBtn.disabled = true;
      this.generateBtn.innerHTML = 'Generating…';
    }

    try {
      const response = await fetch('/api/v1/draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const contentType = response.headers.get('content-type') || '';

      if (!contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Non-JSON response from /api/v1/draft:', text);

        this.showToast('Server error. Please try again.', 'error');
        return;
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          (data && data.error && data.error.message) ||
            'Failed to generate draft'
        );
      }

      console.log('FULL RESPONSE', data);
      this.renderResponse(data);
    } catch (error) {
      console.error('Draft error:', error);
      this.showToast(
        (error && error.message) || 'Failed to generate draft',
        'error'
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
    if (this.emptyState) this.emptyState.classList.add('hidden');

    // Show response container
    if (this.responseContainer) {
      this.responseContainer.classList.remove('hidden');
    }
    // -----------------------------
    // Auto-send visibility (read-only)
    // -----------------------------
    if (data?.auto_send === true) {
      console.log('✅ Auto-send eligible:', data.auto_send_reason);

      this.showAutoSendCard({
        reason: data.auto_send_reason || 'Eligible for auto-send',
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
      'agent-guidance-card',
      'confidence-card',
      'draft-card',
      'actions-card',
      'quick-replies-card',
      'knowledge-card',
      'conversation-card',
    ];
    for (let i = 0; i < idsToShow.length; i++) {
      const el = document.getElementById(idsToShow[i]);
      if (el) el.classList.remove('hidden');
    }

    // 1. Agent Guidance
    this.renderGuidance(data ? data.agent_guidance : null);

    // 2. Confidence & Risk
    this.renderConfidenceRisk(
      data?.intent_classification || data?.agent_guidance || null
    );

    // 3. Intent Classification
    this.renderIntent(data ? data.intent_classification : null);

    // 4. Draft Response
    if (data && data.draft) {
      this.renderDraft(data.draft, data.agent_guidance);
    } else {
      console.warn('⚠️ No draft returned by backend', data);

      this.showToast(
        data?.reason || 'No draft was generated for this request',
        'warning'
      );
    }

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
        behavior: 'smooth',
        block: 'start',
      });
    }
  }

  renderGuidance(guidance) {
    const badgesContainer = document.getElementById('guidance-badges');
    let badges = '';

    if (guidance && guidance.auto_send_eligible) {
      badges += '<span class="badge badge-success">Auto-Send Eligible</span>';
    }
    if (guidance && guidance.requires_review) {
      badges += '<span class="badge badge-warning">Requires Review</span>';
    }
    if (badgesContainer) badgesContainer.innerHTML = badges;

    const reasonEl = document.getElementById('guidance-reason');
    const recEl = document.getElementById('guidance-recommendation');

    if (reasonEl) reasonEl.textContent = (guidance && guidance.reason) || 'N/A';
    if (recEl)
      recEl.textContent = (guidance && guidance.recommendation) || 'N/A';
  }
  renderConfidenceRisk(input) {
    if (!input) return;

    // Normalize confidence
    const confidence =
      typeof input.confidence === 'number'
        ? input.confidence
        : input.confidence?.overall;

    if (typeof confidence !== 'number') return;

    const safety =
      input.safety_mode ?? input.confidence?.safety ?? 'acceptable';

    const ambiguity = input.ambiguity ?? input.confidence?.ambiguity ?? 'none';

    // ---- DOM TARGETS (MATCH HTML EXACTLY) ----
    const confidencePctEl = document.getElementById('confidence-percentage');
    const confidenceLabelEl = document.getElementById('confidence-label');
    const safetyEl = document.getElementById('safety-mode');
    const ambiguityEl = document.getElementById('ambiguity-status');

    if (!confidencePctEl || !confidenceLabelEl) return;

    // ---- CONFIDENCE ----
    const pct = Math.round(confidence * 100);
    confidencePctEl.textContent = `${pct}%`;

    confidenceLabelEl.textContent =
      pct >= 85 ? 'HIGH' : pct >= 65 ? 'MEDIUM' : 'LOW';

    confidenceLabelEl.className = `metric-badge ${
      pct >= 85 ? 'badge-success' : pct >= 65 ? 'badge-warning' : 'badge-danger'
    }`;

    // ---- SAFETY MODE ----
    if (safetyEl) {
      safetyEl.textContent = safety.toUpperCase();
      safetyEl.className = `metric-badge ${
        safety === 'safe' || safety === 'acceptable'
          ? 'badge-success'
          : 'badge-danger'
      }`;
    }

    // ---- AMBIGUITY ----
    if (ambiguityEl) {
      ambiguityEl.textContent = ambiguity.toUpperCase();
      ambiguityEl.className = `metric-badge ${
        ambiguity === 'none' ? 'badge-success' : 'badge-warning'
      }`;
    }

    // ---- EXECUTIVE SUMMARY (DERIVED, READ-ONLY) ----
    if (typeof window.renderExecutiveSummary === 'function') {
      window.renderExecutiveSummary({
        resolutionLikely: confidence >= 0.7,
        missingInfo: input.missing_info_detected === true,
        autoSendEligible: this.autoSendEligible === true,
        ambiguityDetected: ambiguity !== 'none',
        safetyRisk: safety !== 'safe' && safety !== 'acceptable',
        notes: input.notes || '',
      });
    }
  }

  renderIntent(classification) {
    if (!classification) return;

    const primaryEl = document.getElementById('primary-intent');
    if (primaryEl) {
      primaryEl.textContent = this.formatIntent(classification.primary_intent);
    }

    const secondaryContainer = document.getElementById(
      'secondary-intents-container'
    );
    const secondaryEl = document.getElementById('secondary-intents');

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
        .join('');
      secondaryContainer.classList.remove('hidden');
    } else if (secondaryContainer) {
      secondaryContainer.classList.add('hidden');
    }

    const deviceAlert = document.getElementById('device-behavior-alert');
    if (deviceAlert) {
      if (classification.device_behavior_detected) {
        deviceAlert.classList.remove('hidden');
      } else {
        deviceAlert.classList.add('hidden');
      }
    }

    const actionsContainer = document.getElementById(
      'attempted-actions-container'
    );
    const actionsEl = document.getElementById('attempted-actions');

    if (
      actionsContainer &&
      actionsEl &&
      Array.isArray(classification.attempted_actions) &&
      classification.attempted_actions.length > 0
    ) {
      actionsEl.textContent = classification.attempted_actions.join(', ');
      actionsContainer.classList.remove('hidden');
    } else if (actionsContainer) {
      actionsContainer.classList.add('hidden');
    }
  }

  renderDraft(draft, guidance) {
    console.log('RENDER DRAFT HIT', draft);

    const textarea = this.draftTextarea;
    if (!textarea) {
      console.warn('renderDraft: textarea not found');
      return;
    }

    let text = '';

    // ✅ CASE 1 — Expected legacy shape
    if (draft && typeof draft.response_text === 'string') {
      text = draft.response_text;

      // ✅ CASE 2 — Nested legacy shape
    } else if (
      draft &&
      typeof draft.response_text === 'object' &&
      typeof draft.response_text.response_text === 'string'
    ) {
      text = draft.response_text.response_text;

      // ✅ CASE 3 — NEW backend shape (FINAL, CORRECT)
    } else if (
      draft &&
      typeof draft.response_text === 'object' &&
      typeof draft.response_text.text === 'string'
    ) {
      text = draft.response_text.text;

      // ❌ Hard failure (debug only)
    } else {
      console.error('❌ renderDraft: invalid draft payload', draft);
      textarea.value = '';
      return;
    }

    textarea.value = text;

    // Badge logic (unchanged)
    const sourceBadge = document.getElementById('draft-source-badge');
    if (sourceBadge && guidance) {
      if (guidance.auto_send_eligible) {
        sourceBadge.textContent = 'AI Draft · Auto-Send Ready';
        sourceBadge.className = 'badge badge-success';
      } else if (guidance.requires_review) {
        sourceBadge.textContent = 'AI Draft · Review Required';
        sourceBadge.className = 'badge badge-warning';
      } else {
        sourceBadge.textContent = 'AI Draft';
        sourceBadge.className = 'badge badge-neutral';
      }
    }
  }

  renderFollowupQuestions(followups) {
    const list = document.getElementById('suggested-actions-list');
    if (!list) return;

    list.innerHTML = '';

    const section = document.getElementById('followup-section');

    // HARD GATE: hide section unless followups exist
    if (!Array.isArray(followups) || followups.length === 0) {
      if (section) section.style.display = 'none';
      return;
    }

    // Enable section only when followups exist
    if (section) section.style.display = 'block';

    followups.forEach((f, index) => {
      // ✅ MATCH BACKEND SHAPE EXACTLY
      const text = f.question;

      if (!text) return;

      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'followup-action';
      item.setAttribute('data-preview', f.key || '');

      item.innerHTML = `
        <span class="followup-index">${index + 1}</span>
        <span class="followup-text">${text}</span>
      `;

      item.title = text; // hover preview fallback

      item.addEventListener('click', () => {
        if (!this.draftTextarea) return;

        const cur = this.draftTextarea.value || '';
        const spacer = cur && !cur.endsWith('\n') ? '\n\n' : '';
        this.draftTextarea.value = cur + spacer + text;
        this.draftTextarea.focus();

        this.showToast('Inserted follow-up question');
      });

      list.appendChild(item);
    });
  }

  renderConversationContext() {
    const messagesContainer = document.getElementById('conversation-messages');
    if (!messagesContainer) return;

    messagesContainer.innerHTML =
      '<p class="help-text">No conversation history in this request</p>';
  }

  // ✅ Must exist, because init() calls it
  initCollapsibles() {
    const toggles = document.querySelectorAll('.section-toggle');
    toggles.forEach((toggle) => {
      toggle.addEventListener('click', () => {
        const content = toggle.nextElementSibling;
        toggle.classList.toggle('collapsed');
        if (content) content.classList.toggle('collapsed');
      });
    });
  }

  copyDraft() {
    const textarea = document.getElementById('draft-text');
    if (!textarea) return;

    textarea.select();
    document.execCommand('copy');
    this.showToast('Draft copied to clipboard');
  }

  reset() {
    if (this.form) this.form.reset();

    if (this.responseContainer) this.responseContainer.classList.add('hidden');
    if (this.emptyState) this.emptyState.classList.remove('hidden');

    if (this.cannedMenu) this.cannedMenu.classList.add('hidden');
    if (this.cannedBtn) this.cannedBtn.setAttribute('aria-expanded', 'false');

    if (this.draftTextarea) this.draftTextarea.value = '';

    // Hide auto-send card on reset
    this.hideAutoSendCard();

    this.showToast('Form cleared');
  }

  showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast toast-${type}`;
    toast.classList.remove('hidden');

    setTimeout(() => {
      toast.classList.add('hidden');
    }, 3000);
  }

  formatIntent(intent) {
    if (!intent) return '';
    return String(intent)
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }
}

// ------------------------------------
// Follow-up questions toggle (Phase 3.1)
// ------------------------------------
document.addEventListener('click', (e) => {
  if (!e.target.classList.contains('followups-toggle')) return;

  const list = e.target.nextElementSibling;
  if (!list) return;

  list.classList.toggle('hidden');

  e.target.textContent = list.classList.contains('hidden')
    ? '▼ Follow-up questions (optional)'
    : '▲ Follow-up questions (optional)';
});
/// Canned Responses Dropdown — click-away close ONLY
(function () {
  const dropdownBtn = document.getElementById('canned-dropdown-btn');
  const dropdownMenu = document.getElementById('canned-dropdown-menu');

  if (!dropdownBtn || !dropdownMenu) return;

  document.addEventListener('click', function (e) {
    if (dropdownMenu.classList.contains('hidden')) return;

    const container = dropdownBtn.closest('.canned-dropdown');
    if (container && container.contains(e.target)) return;

    dropdownMenu.classList.add('hidden');
    dropdownBtn.setAttribute('aria-expanded', 'false');
  });
})();
function updateExecutiveSummary({
  confidence,
  safety,
  ambiguity,
  autoSendEligible,
}) {
  document.getElementById('exec-draft-outcome').textContent =
    safety === 'safe' ? 'Ready to send' : 'Needs review';

  document.getElementById('exec-recommended-action').textContent =
    autoSendEligible ? 'Auto-send' : 'Manual review';

  document.getElementById('exec-auto-send-status').textContent =
    autoSendEligible ? 'Yes' : 'No';

  document.getElementById('exec-primary-risk').textContent =
    ambiguity === 'high'
      ? 'Missing or unclear info'
      : safety !== 'safe'
        ? 'Policy / safety concern'
        : 'None detected';

  document.getElementById('exec-notes').textContent = autoSendEligible
    ? 'Response meets auto-send criteria.'
    : 'Human review recommended before sending.';
}
const RALPH_WEEKLY_SUMMARY_URL =
  'http://127.0.0.1:5000/insights/weekly-summary';

let cachedWeeklySummary = null;
let lastWeeklyFetch = 0;
const WEEKLY_CACHE_MS = 6 * 60 * 60 * 1000; // 6 hours

async function fetchWeeklySummary() {
  const now = Date.now();

  if (cachedWeeklySummary && now - lastWeeklyFetch < WEEKLY_CACHE_MS) {
    return cachedWeeklySummary;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 3000);

  try {
    const res = await fetch(RALPH_WEEKLY_SUMMARY_URL, {
      signal: controller.signal,
    });

    if (!res.ok) throw new Error('Weekly summary fetch failed');

    cachedWeeklySummary = await res.json();
    lastWeeklyFetch = now;
    return cachedWeeklySummary;
  } catch (err) {
    console.warn('Weekly summary unavailable', err);
    return null;
  } finally {
    clearTimeout(timeoutId);
  }
}
function renderWeeklySummary(summary) {
  const body = document.getElementById('weekly-summary-body');
  if (!body) return;

  if (!summary) {
    body.innerHTML = `<p class="muted">Summary unavailable.</p>`;
    return;
  }

  body.innerHTML = `
    <div class="summary-section">
      <strong>Top Intents</strong>
      <ul>
        ${summary.top_intents
          .map((i) => `<li>${i.intent} (${i.event_count})</li>`)
          .join('')}
      </ul>
    </div>

    <div class="summary-section">
      <strong>Biggest Increases</strong>
      <ul>
        ${summary.intent_increases
          .map((i) => `<li>${i.intent}: +${i.delta}</li>`)
          .join('')}
      </ul>
    </div>

    <div class="summary-section">
      <strong>Missing Approvals</strong>
      <ul>
        ${summary.intents_missing_approval
          .map((i) => `<li>${i.intent}</li>`)
          .join('')}
      </ul>
    </div>

    <p class="muted">
      Last updated: ${new Date(summary.generated_at).toLocaleDateString()}
    </p>
  `;
}
document
  .getElementById('weekly-summary-toggle')
  ?.addEventListener('click', async () => {
    const body = document.getElementById('weekly-summary-body');
    body.classList.toggle('hidden');

    if (!body.dataset.loaded) {
      const summary = await fetchWeeklySummary();
      renderWeeklySummary(summary);
      body.dataset.loaded = 'true';
    }
  });
function renderExecutiveSummary(signals) {
  if (!signals) return;

  // Draft Outcome
  document.getElementById('exec-draft-outcome').textContent =
    signals.resolutionLikely ? 'Likely resolved' : 'Follow-up expected';

  // Recommended Action
  document.getElementById('exec-recommended-action').textContent =
    signals.missingInfo
      ? 'Request missing information'
      : 'Send draft as written';

  // Auto-Send
  document.getElementById('exec-auto-send-status').textContent =
    signals.autoSendEligible
      ? 'Eligible (manual review allowed)'
      : 'Not eligible';

  // Primary Risk
  document.getElementById('exec-primary-risk').textContent =
    signals.ambiguityDetected
      ? 'Ambiguous customer intent'
      : signals.safetyRisk
        ? 'Policy / safety risk'
        : 'None detected';

  // Notes (short, human-readable)
  document.getElementById('exec-notes').textContent =
    signals.notes || 'Based on current ticket signals';
}
// Add this NEW function (does not modify existing functions)

function renderDecisionExplanation(explanation) {
  /**
   * Render the decision explanation block.
   * Pure presentation - no actions, no mutations.
   */

  const container = document.getElementById('decision-explanation-container');
  if (!container || !explanation) return;

  container.innerHTML = `
    <div class="explanation-row">
      <span class="explanation-label">Why This Intent:</span>
      <span class="explanation-value">${escapeHtml(explanation.why_this_intent)}</span>
    </div>
    
    <div class="explanation-row">
      <span class="explanation-label">Auto-Send Decision:</span>
      <span class="explanation-value">${escapeHtml(explanation.why_auto_send_allowed_or_blocked)}</span>
    </div>
    
    <div class="explanation-row">
      <span class="explanation-label">Confidence:</span>
      <span class="explanation-value">
        ${explanation.confidence_band.toUpperCase()} — ${escapeHtml(explanation.confidence_description)}
      </span>
    </div>
    
    <div class="explanation-row">
      <span class="explanation-label">Safety Mode:</span>
      <span class="explanation-value">${escapeHtml(explanation.safety_explanation)}</span>
    </div>
    
    ${
      explanation.missing_information.length > 0
        ? `
      <div class="explanation-row">
        <span class="explanation-label">Missing Info:</span>
        <span class="explanation-value">${explanation.missing_information.join(', ')}</span>
      </div>
    `
        : ''
    }
    
    <div class="explanation-signals">
      <span class="explanation-label">Signals Used:</span>
      ${explanation.key_signals_used
        .map(
          (signal) => `<span class="signal-badge">${escapeHtml(signal)}</span>`
        )
        .join('')}
    </div>
  `;

  container.classList.remove('hidden');
}

// In the existing handleDraftResponse() function, ADD this call:

function handleDraftResponse(data) {
  // ... existing code ...

  // NEW: Render decision explanation if present
  if (data.decision_explanation) {
    renderDecisionExplanation(data.decision_explanation);
  }

  // ... rest of existing code ...
}

// Add helper function if not already present:
function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
// -------------------------------------
// Initialize Sidecar (ONLY ONCE)
// -------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  console.log('Sidecar JS loaded');

  // Initialize sidecar
  window.aiSidecar = new AISidecar();

  // Auto-run ONLY when query params exist
  if (typeof window.aiSidecar.autoGenerateFromQueryParamsOnce === 'function') {
    setTimeout(() => {
      window.aiSidecar.autoGenerateFromQueryParamsOnce();
    }, 200);
  }
});
