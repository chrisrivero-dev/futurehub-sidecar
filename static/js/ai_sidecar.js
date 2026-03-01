// static/js/ai_sidecar.js
// v2.0 — Auto-run on ticket detection, single "Insert into CRM" action

// -----------------------------------------------------------
// State lock: ensure auto-run fires only once per ticket URL
// -----------------------------------------------------------
let _lastAutoRunTicketKey = null;

window.addEventListener('message', (event) => {
  if (!event.data || event.data.type !== 'TICKET_DATA') return;

  const ticket = event.data.ticket;
  console.log('[sidecar] Received TICKET_DATA:', ticket);

  const subject = document.getElementById('subject');
  const latest = document.getElementById('latest-message');
  const customerName = document.getElementById('customer-name');

  if (subject) subject.value = ticket.subject || '';
  if (latest) {
    latest.value = ticket.description_text || ticket.description || '';
  }
  if (customerName && ticket.customer_name) {
    customerName.value = ticket.customer_name;
  }

  // Store ticket id and domain for review mode and draft payload
  if (window.aiSidecar) {
    window.aiSidecar._currentTicketId = ticket.id || null;
    // Extract domain from event origin (e.g. "https://company.freshdesk.com")
    try {
      window.aiSidecar._freshdeskDomain = event.origin
        ? new URL(event.origin).hostname
        : null;
    } catch (_e) {
      window.aiSidecar._freshdeskDomain = null;
    }
    if (typeof window.aiSidecar._showReviewButton === 'function') {
      window.aiSidecar._showReviewButton();
    }
  }

  // Auto-run draft pipeline once per unique ticket
  const ticketKey = `${ticket.id || ''}_${ticket.subject || ''}`;
  if (window.aiSidecar && ticketKey !== _lastAutoRunTicketKey) {
    _lastAutoRunTicketKey = ticketKey;
    window.aiSidecar.autoRunDraft();
  }
}); // ✅ CLOSES window.addEventListener('message', ...)

// -----------------------------------------------------------
// Helper text inserted by Suggested Actions
// -----------------------------------------------------------
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

// -----------------------------------------------------------
// Intent -> Recommended canned response
// -----------------------------------------------------------
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
    this.regenerateBtn = document.getElementById('regenerate-btn');
    this.insertCrmBtn = document.getElementById('insert-crm-btn');
    this.resetBtn = document.getElementById('reset-btn');

    this.draftTextarea =
      document.getElementById('draft-text') ||
      document.getElementById('draft-message-box');

    this.cannedBtn = document.getElementById('canned-dropdown-btn');
    this.cannedMenu = document.getElementById('canned-dropdown-menu');

    this.recommendedCannedTitle = null;
    this.cannedResponses = [];
    this.autoSendEligible = false;

    // Track current strategy and variable state
    this._currentStrategy = null;
    this._variableVerification = null;
    this._isAutoRunning = false;
    this._freshdeskDomain = null;

    // Lifecycle state
    this._currentTicketId = null;
    this._inReviewMode = false;

    this.init();
    this.bindCollapseToggle();
    this.bindResetButton();
    this.loadCannedResponses();
    this.initReviewMode();
    this.loadAnalyticsSummary();
  }

  initReviewMode() {
    // DO NOT reset _currentTicketId here
    this._inReviewMode = false;

    const header = document.querySelector('.header-controls');
    if (!header) return;

    const btn = document.createElement('button');
    btn.id = 'review-mode-btn';
    btn.innerText = 'Review';
    btn.style.display = 'none';
    btn.style.marginLeft = '8px';
    btn.classList.add('secondary-btn');

    btn.addEventListener('click', () => {
      if (!this._currentTicketId) return;
      this._enterReviewMode();
    });

    header.appendChild(btn);
    this._reviewBtn = btn;

    const container = document.createElement('div');
    container.id = 'review-mode-container';
    container.style.display = 'none';
    this.panel.appendChild(container);
  }

  _showReviewButton() {
    if (this._reviewBtn && this._currentTicketId) {
      this._reviewBtn.style.display = 'inline-block';
    }
  }

  async _enterReviewMode() {
    if (this._inReviewMode) return;

    this._inReviewMode = true;

    document
      .querySelector('.sidecar-collapsible')
      ?.style.setProperty('display', 'none');
    document
      .getElementById('response-container')
      ?.style.setProperty('display', 'none');

    const container = document.getElementById('review-mode-container');
    if (!container) return;

    container.style.display = 'block';
    container.innerHTML = 'Loading review data...';

    try {
      const res = await fetch(
        `/api/v1/tickets/${this._currentTicketId}/review`
      );

      if (!res.ok) {
        throw new Error(`Review fetch failed: ${res.status}`);
      }

      const data = await res.json();
      this._renderReviewContent(data);
    } catch (err) {
      console.error('Review load error:', err);
      container.innerHTML = 'Failed to load review data.';
    }
  }

  _renderReviewContent(data) {
    const container = document.getElementById('review-mode-container');
    if (!container) return;

    // existing render logic continues...
  }
}

    const d = data.draft_summary || {};
    const l = data.lifecycle || {};

    container.innerHTML = `
    <div class="section-card">
      <div class="section-header">
        <h2 class="section-title">Ticket Review</h2>
      </div>
      <div class="section-body">
        <p><strong>Intent:</strong> ${d.intent || '—'}</p>
        <p><strong>Confidence:</strong> ${d.confidence ?? '—'}</p>
        <p><strong>Risk:</strong> ${d.risk_category || '—'}</p>
      </div>
    </div>

    <div class="section-card">
      <div class="section-header">
        <h2 class="section-title">Lifecycle Signals</h2>
      </div>
      <div class="section-body">
        <p><strong>Outbound Replies:</strong> ${l.outbound_count || 0}</p>
        <p><strong>Inbound Replies:</strong> ${l.inbound_count || 0}</p>
        <p><strong>Edited:</strong> ${l.edited_count > 0 ? 'Yes' : 'No'}</p>
        <p><strong>Follow-up:</strong> ${l.followup_detected ? 'Yes' : 'No'}</p>
        <p><strong>Reopened:</strong> ${l.reopened ? 'Yes' : 'No'}</p>
        <br/>
        <button id="review-back-btn" class="secondary-btn">Back to Processing</button>
      </div>
    </div>
  `;

    const backBtn = document.getElementById('review-back-btn');
    if (backBtn) {
      backBtn.addEventListener('click', () => {
        this._exitReviewMode();
      });
    }

    // Generate Support Asset Button
    const generateBtn = document.createElement('button');
    generateBtn.id = 'generate-support-asset-btn';
    generateBtn.className = 'primary-btn';
    generateBtn.style.marginTop = '16px';
    generateBtn.textContent = 'Generate Support Asset';

    generateBtn.addEventListener('click', async () => {
      try {
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';

        const response = await fetch(
          '/api/v1/support-assets/generate-from-text',
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              subject: data.subject || '',
              original_message: data.original_message || '',
              final_reply: data.final_reply || '',
              intent: d.intent || null,
              confidence: d.confidence || null,
            }),
          }
        );

        const result = await response.json();

        if (!result.success) {
          throw new Error('Generation failed');
        }

        let assetContainer = document.getElementById('support-asset-output');
        if (!assetContainer) {
          assetContainer = document.createElement('pre');
          assetContainer.id = 'support-asset-output';
          assetContainer.style.marginTop = '20px';
          assetContainer.style.whiteSpace = 'pre-wrap';
          container.appendChild(assetContainer);
        }

        assetContainer.textContent = result.asset;
      } catch (err) {
        console.error('Support asset error:', err);
        alert('Support asset generation failed.');
      } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Support Asset';
      }
    });

    container.appendChild(generateBtn);
  }

  _exitReviewMode() {
    this._inReviewMode = false;

    const collapsible = document.querySelector('.sidecar-collapsible');
    if (collapsible) {
      collapsible.style.display = 'block';
    }

    const response = document.getElementById('response-container');
    if (response) {
      response.style.display = 'block';
    }

    const container = document.getElementById('review-mode-container');
    if (container) {
      container.style.display = 'none';
    }
  }

  // -----------------------------
  // Load review data after draft completes
  // -----------------------------
  async loadReviewData(ticketId) {
    if (!ticketId) return;

    try {
      const res = await fetch(`/api/v1/tickets/${ticketId}/review`);
      if (!res.ok) return;

      const data = await res.json();
      if (!data.success) return;

      this._renderReviewPanel(data);
      this._showReviewButton();
    } catch (err) {
      console.warn('[sidecar] Review data load failed:', err);
    }
  }

  _renderReviewPanel(data) {
    let panel = document.getElementById('review-data-panel');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'review-data-panel';
      panel.className = 'section-card';
      const responseContainer = document.getElementById('response-container');
      if (responseContainer) {
        responseContainer.appendChild(panel);
      } else {
        return;
      }
    }

    const d = data.draft_summary || {};
    const l = data.lifecycle || {};
    const kbs = data.kb_recommendations || [];
    const subject = data.subject || '';
    const originalMsg = data.original_message || '';
    const finalReply = data.final_reply || '';

    let kbHtml = '';
    if (kbs.length > 0) {
      kbHtml = `
        <div style="margin-top:10px;">
          <strong>KB Recommendations:</strong>
          <ul style="margin:6px 0 0 0;padding-left:18px;">
            ${kbs.map(kb => {
              const url = kb.url || kb.article_url || '#';
              const title = kb.title || `Article #${kb.id || ''}`;
              return `<li><a href="${url}" target="_blank" rel="noopener" class="kb-link" data-id="${kb.id || ''}">${title}</a></li>`;
            }).join('')}
          </ul>
        </div>`;
    }

    let contextHtml = '';
    if (subject || originalMsg || finalReply) {
      contextHtml = `
        <div style="margin-top:10px;">
          <strong>Ticket Context:</strong>
          ${subject ? `<p style="margin:4px 0;"><em>Subject:</em> ${subject}</p>` : ''}
          ${originalMsg ? `<p style="margin:4px 0;"><em>Customer Message:</em> ${originalMsg.length > 200 ? originalMsg.slice(0, 200) + '...' : originalMsg}</p>` : ''}
          ${finalReply ? `<p style="margin:4px 0;"><em>Agent Reply:</em> ${finalReply.length > 200 ? finalReply.slice(0, 200) + '...' : finalReply}</p>` : ''}
        </div>`;
    }

    panel.innerHTML = `
      <div class="section-header">
        <h2 class="section-title">Review Intelligence</h2>
      </div>
      <div class="section-body">
        <p><strong>Intent:</strong> ${d.intent || '—'}
           <strong style="margin-left:12px;">Risk:</strong> ${d.risk_category || '—'}
           <strong style="margin-left:12px;">Confidence:</strong> ${d.confidence != null ? Math.round(d.confidence * 100) + '%' : '—'}</p>
        <p><strong>Outbound:</strong> ${l.outbound_count || 0}
           <strong style="margin-left:12px;">Inbound:</strong> ${l.inbound_count || 0}
           <strong style="margin-left:12px;">Edited:</strong> ${l.edited_count > 0 ? 'Yes' : 'No'}
           <strong style="margin-left:12px;">Follow-up:</strong> ${l.followup_detected ? 'Yes' : 'No'}</p>
        ${contextHtml}
        ${kbHtml}
      </div>
    `;
  }

  // -----------------------------
  // Analytics Summary
  // -----------------------------
  async loadAnalyticsSummary() {
    try {
      const res = await fetch('/api/v1/analytics/weekly');
      const data = await res.json();

      if (!data.success) return;

      const totalEl = document.getElementById('analytics-total');
      const autoEl = document.getElementById('analytics-auto');
      const intentEl = document.getElementById('analytics-intent');
      const riskEl = document.getElementById('analytics-risk');

      if (totalEl) totalEl.innerText = data.total_tickets;
      if (autoEl) autoEl.innerText = data.automation_rate;

      if (intentEl) {
        intentEl.innerText = data.top_intents?.[0]?.intent || '—';
      }

      if (riskEl) {
        riskEl.innerText = Object.entries(data.risk_distribution)
          .map(([k, v]) => `${k}: ${v}`)
          .join(' | ');
      }
    } catch (err) {
      console.error('[sidecar] analytics load failed', err);
    }
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
      this._clearMissingVariableChips();
      this._setInsertCrmEnabled(false);
      _lastAutoRunTicketKey = null; // allow re-run on next ticket
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
    // Form submission triggers regenerate (no auto-submit)
    if (this.form) {
      this.form.addEventListener('submit', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.generateDraft();
        return false;
      });
    }

    // Regenerate button
    if (this.regenerateBtn) {
      this.regenerateBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.generateDraft();
      });
    }

    // Manual Process Ticket button (standalone fallback)
    this.processTicketBtn = document.getElementById('process-ticket-btn');
    if (this.processTicketBtn) {
      this.processTicketBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.processTicket();
      });
    }

    // Insert into CRM button
    if (this.insertCrmBtn) {
      this.insertCrmBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.insertIntoCrm();
      });
    }

    // Copy draft
    const copyBtn = document.getElementById('copy-draft-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => this.copyDraft());
    }

    // Collapsible sections
    this.initCollapsibles();

    // Canned Responses dropdown open/close
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
  // Auto-Run Draft (on ticket detection)
  // -----------------------------
  autoRunDraft() {
    if (this._isAutoRunning) return;

    const subject = document.getElementById('subject');
    const latest = document.getElementById('latest-message');

    if (!subject?.value?.trim() || !latest?.value?.trim()) {
      console.log('[sidecar] Auto-run skipped: missing ticket data');
      return;
    }

    console.log('[sidecar] Auto-running draft pipeline');
    this._isAutoRunning = true;
    this.generateDraft().finally(() => {
      this._isAutoRunning = false;
    });
  }

  // -----------------------------
  // Manual Process Ticket (standalone fallback)
  // -----------------------------
  processTicket() {
    const subject = document.getElementById('subject')?.value?.trim();
    const latestMessage = document
      .getElementById('latest-message')
      ?.value?.trim();
    const customerName = document
      .getElementById('customer-name')
      ?.value?.trim();

    if (!subject || !latestMessage) {
      this.showToast('Subject and Latest Message are required', 'error');
      return;
    }

    // Update status indicator
    const statusEl = document.getElementById('auto-run-status');
    if (statusEl) {
      statusEl.textContent = 'Processing ticket...';
      statusEl.className = 'auto-run-status status-loading';
    }

    this.generateDraft();
  }

  // -----------------------------
  // Insert into CRM
  // -----------------------------
  insertIntoCrm() {
    if (!this.draftTextarea) return;

    const text = this.draftTextarea.value || '';
    if (!text.trim()) {
      this.showToast('No draft to insert', 'warning');
      return;
    }

    // Check variable verification
    if (
      this._variableVerification &&
      this._variableVerification.has_required_missing
    ) {
      this.showToast('Cannot insert: missing required variables', 'error');
      return;
    }

    // Phase 3.5 — Capture edit diff before sending (non-blocking)
    if (typeof window.DraftEditTracker !== 'undefined') {
      try {
        var editMeta = this._collectEditReason();
        window.DraftEditTracker.processSendAction(text, editMeta);
      } catch (_e) {
        /* never delay Send */
      }
    }
  // Mailbox transport — no postMessage
  window.__SIDECAR_DRAFT__ = text;
  window.__SIDECAR_DRAFT_TS__ = Date.now();
  window.__SIDECAR_STRATEGY__ = this._currentStrategy;

  this.showToast('Draft ready for injection');

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
  // Draft generation (called by auto-run and regenerate)
  // -----------------------------
  async generateDraft() {
    if (!this.form) return;

    const formData = new FormData(this.form);

    const ticketIdFromQuery = Number(
      new URLSearchParams(window.location.search).get('ticket_id')
    );
    const ticketIdFromPath = Number(window.location.pathname.split('/').pop());
    const freshdeskTicketId =
      Number.isFinite(ticketIdFromQuery) && ticketIdFromQuery
        ? ticketIdFromQuery
        : Number.isFinite(ticketIdFromPath) && ticketIdFromPath
          ? ticketIdFromPath
          : null;

    const payload = {
      subject: formData.get('subject'),
      latest_message: formData.get('latest_message'),
      conversation_history: [],
      customer_name: formData.get('customer_name') || undefined,

      // ✅ REQUIRED FOR REVIEW HYDRATION
      freshdesk_ticket_id: freshdeskTicketId,
      freshdesk_domain: window.location.hostname,
    };

    // Show loading state
    const statusEl = document.getElementById('auto-run-status');
    if (statusEl) {
      statusEl.textContent = 'Preparing draft...';
      statusEl.className = 'auto-run-status status-loading';
    }

    if (this.regenerateBtn) {
      this.regenerateBtn.disabled = true;
      this.regenerateBtn.textContent = 'Regenerating...';
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
      // ---------------------------
      // CASE INTELLIGENCE UI UPDATE
      // ---------------------------

      const pill = document.getElementById('status-pill');
      const summary = document.getElementById('smart-summary');
      const suggested = document.getElementById('suggested-action');
      const trend = document.getElementById('trend-info');

      if (pill && summary && suggested && trend) {
        const risk = data.governance?.risk_category || 'low';
        const intent = data.intent_classification?.primary_intent || 'unknown';
        const confidence = data.intent_classification?.confidence?.overall || 0;

        pill.className = 'status-pill ' + risk;
        pill.textContent = `${risk.toUpperCase()} Risk | ${intent.replace('_', ' ')}`;

        summary.textContent =
          `Customer issue: ${intent.replace('_', ' ')}. ` +
          `Confidence: ${Math.round(confidence * 100)}%.`;

        if (intent === 'shipping_status') {
          suggested.textContent = 'Check carrier API for delay codes';
        } else if (intent === 'unknown_vague') {
          suggested.textContent = 'Ask for Order # or Device Model';
        } else if (intent === 'setup_help') {
          suggested.textContent = 'Confirm network + apollo.local access';
        } else {
          suggested.textContent = 'Review draft before sending';
        }

        trend.textContent = 'Trend data loading...';
      }

      if (!response.ok) {
        throw new Error(
          (data && data.error && data.error.message) ||
            'Failed to generate draft'
        );
      }

      console.log('[sidecar] Draft response:', data);
      this.renderResponse(data);

      // Auto-load review data after successful draft
      if (this._currentTicketId) {
        this.loadReviewData(this._currentTicketId);
      }
    } catch (error) {
      console.error('Draft error:', error);
      this.showToast(
        (error && error.message) || 'Failed to generate draft',
        'error'
      );

      if (statusEl) {
        statusEl.textContent = 'Draft failed — use Regenerate to retry';
        statusEl.className = 'auto-run-status status-error';
      }
    } finally {
      if (this.regenerateBtn) {
        this.regenerateBtn.disabled = false;
        this.regenerateBtn.textContent = 'Regenerate';
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

    // Store strategy and verification state
    this._currentStrategy = data?.strategy?.selected || null;
    this._variableVerification = data?.variable_verification || null;

    // ----------------------------
    // Strategy badge
    // ----------------------------
    this.renderStrategy(data?.strategy);

    // ----------------------------
    // Auto-run status
    // ----------------------------
    const statusEl = document.getElementById('auto-run-status');
    if (statusEl) {
      const hasRequiredMissing =
        data?.variable_verification?.has_required_missing;
      if (hasRequiredMissing) {
        statusEl.textContent = 'Missing data — review required fields below';
        statusEl.className = 'auto-run-status status-warning';
      } else {
        statusEl.textContent = 'Draft ready';
        statusEl.className = 'auto-run-status status-ready';
      }
    }

    // ----------------------------
    // Auto-send visibility
    // ----------------------------
    if (data?.auto_send === true) {
      this.showAutoSendCard({
        reason: data.auto_send_reason || 'Eligible for auto-send',
      });
    } else {
      this.hideAutoSendCard();
    }

    // Show cards
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
      console.warn('[sidecar] No draft returned by backend', data);
      this.showToast(
        data?.reason || 'No draft was generated for this request',
        'warning'
      );
    }

    // 5. Missing variable chips
    this.renderMissingVariables(data?.variable_verification);

    // 6. Enable/disable Insert into CRM
    const canInsert =
      data?.draft?.response_text &&
      !data?.variable_verification?.has_required_missing;
    this._setInsertCrmEnabled(!!canInsert);

    // 7. Follow-up Questions
    const followups =
      data && data.agent_guidance
        ? data.agent_guidance.suggested_followups
        : null;
    this.renderFollowupQuestions(followups);

    // 8. Canned response recommendation
    const primaryIntent =
      data && data.intent_classification
        ? data.intent_classification.primary_intent
        : null;
    this.recommendedCannedTitle =
      this.resolveRecommendedCannedTitle(primaryIntent);
    this.renderCannedResponses();

    // 9. Conversation Context
    this.renderConversationContext();

    // 10. Phase 3.5 — Store ephemeral draft + emit draft_presented
    if (
      typeof window.DraftEditTracker !== 'undefined' &&
      data?.draft?.response_text
    ) {
      try {
        var draftId = window.DraftEditTracker.storeDraft({
          trace_id: data.trace_id || null,
          draft_text: data.draft.response_text,
        });
        this._currentDraftId = draftId;
        this._currentTraceId = data.trace_id || null;

        window.DraftEditTracker.emitDraftPresented({
          trace_id: data.trace_id || null,
          ticket_id: data.ticket_id || null,
          intent: data.intent_classification?.primary_intent || null,
          confidence: data.intent_classification?.confidence?.overall || null,
          latency_ms: data.processing_time_ms || null,
          tokens: data.tokens_used || null,
          cost: data.cost || null,
        });
      } catch (_e) {
        /* non-blocking */
      }
    }

    // Scroll to top
    if (this.responseContainer && this.responseContainer.scrollIntoView) {
      this.responseContainer.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  }

  // -----------------------------
  // Strategy display
  // -----------------------------
  renderStrategy(strategy) {
    const badge = document.getElementById('strategy-badge');
    if (!badge || !strategy) return;

    const labels = {
      AUTO_TEMPLATE: 'Auto Template',
      PROACTIVE_DRAFT: 'Proactive Draft',
      ADVISORY_ONLY: 'Advisory Only',
      SCAFFOLD: 'Scaffold',
    };

    const classes = {
      AUTO_TEMPLATE: 'badge-success',
      PROACTIVE_DRAFT: 'badge-success',
      ADVISORY_ONLY: 'badge-warning',
      SCAFFOLD: 'badge-danger',
    };

    badge.textContent = labels[strategy.selected] || strategy.selected;
    badge.className = `badge strategy-badge ${classes[strategy.selected] || 'badge-neutral'}`;

    const reasonEl = document.getElementById('strategy-reason');
    if (reasonEl) {
      reasonEl.textContent = strategy.reason || '';
    }
  }

  // -----------------------------
  // Missing Variable Chips
  // -----------------------------
  renderMissingVariables(verification) {
    const container = document.getElementById('missing-variables-container');
    if (!container) return;

    this._clearMissingVariableChips();

    if (
      !verification ||
      !Array.isArray(verification.missing) ||
      verification.missing.length === 0
    ) {
      container.classList.add('hidden');
      return;
    }

    container.classList.remove('hidden');

    const chipList = document.getElementById('missing-variable-chips');
    if (!chipList) return;

    verification.missing.forEach((item) => {
      const chip = document.createElement('div');
      chip.className = `variable-chip ${item.required ? 'variable-chip-required' : 'variable-chip-optional'}`;
      chip.innerHTML = `
        <span class="variable-chip-label">${escapeHtml(item.label || item.key)}</span>
        ${item.required ? '<span class="variable-chip-badge">Required</span>' : '<span class="variable-chip-badge optional">Optional</span>'}
      `;
      chipList.appendChild(chip);
    });
  }

  _clearMissingVariableChips() {
    const chipList = document.getElementById('missing-variable-chips');
    if (chipList) chipList.innerHTML = '';
  }

  // -----------------------------
  // Insert CRM button enable/disable
  // -----------------------------
  _setInsertCrmEnabled(enabled) {
    if (!this.insertCrmBtn) return;

    this.insertCrmBtn.disabled = !enabled;

    if (enabled) {
      this.insertCrmBtn.classList.remove('btn-disabled');
    } else {
      this.insertCrmBtn.classList.add('btn-disabled');
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

    const confidence =
      typeof input.confidence === 'number'
        ? input.confidence
        : input.confidence?.overall;

    if (typeof confidence !== 'number') return;

    const safety =
      input.safety_mode ?? input.confidence?.safety ?? 'acceptable';

    const ambiguity = input.ambiguity ?? input.confidence?.ambiguity ?? 'none';

    const confidencePctEl = document.getElementById('confidence-percentage');
    const confidenceLabelEl = document.getElementById('confidence-label');
    const safetyEl = document.getElementById('safety-mode');
    const ambiguityEl = document.getElementById('ambiguity-status');

    if (!confidencePctEl || !confidenceLabelEl) return;

    const pct = Math.round(confidence * 100);
    confidencePctEl.textContent = `${pct}%`;

    confidenceLabelEl.textContent =
      pct >= 85 ? 'HIGH' : pct >= 65 ? 'MEDIUM' : 'LOW';

    confidenceLabelEl.className = `metric-badge ${
      pct >= 85 ? 'badge-success' : pct >= 65 ? 'badge-warning' : 'badge-danger'
    }`;

    if (safetyEl) {
      safetyEl.textContent = safety.toUpperCase();
      safetyEl.className = `metric-badge ${
        safety === 'safe' || safety === 'acceptable'
          ? 'badge-success'
          : 'badge-danger'
      }`;
    }

    if (ambiguityEl) {
      ambiguityEl.textContent = ambiguity.toUpperCase();
      ambiguityEl.className = `metric-badge ${
        ambiguity === 'none' ? 'badge-success' : 'badge-warning'
      }`;
    }

    const execContainer = document.getElementById('executive-summary');

    if (execContainer && typeof window.renderExecutiveSummary === 'function') {
      window.renderExecutiveSummary({
        resolutionLikely: confidence >= 0.7,
        missingInfo: input.missing_info_detected === true,
        autoSendEligible: this.autoSendEligible === true,
        ambiguityDetected: ambiguity !== 'none',
        safetyRisk: safety !== 'safe' && safety !== 'acceptable',
        notes: input.notes || '',
      });
    }
  } // ← THIS BRACE IS MISSING IN YOUR FILE

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
    const textarea = this.draftTextarea;
    if (!textarea) {
      console.warn('renderDraft: textarea not found');
      return;
    }

    let text = '';

    if (draft && typeof draft.response_text === 'string') {
      text = draft.response_text;
    } else if (
      draft &&
      typeof draft.response_text === 'object' &&
      typeof draft.response_text.response_text === 'string'
    ) {
      text = draft.response_text.response_text;
    } else if (
      draft &&
      typeof draft.response_text === 'object' &&
      typeof draft.response_text.text === 'string'
    ) {
      text = draft.response_text.text;
    } else {
      console.error('[sidecar] renderDraft: invalid draft payload', draft);
      textarea.value = '';
      return;
    }

    textarea.value = text;

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

    if (!Array.isArray(followups) || followups.length === 0) {
      if (section) section.style.display = 'none';
      return;
    }

    if (section) section.style.display = 'block';

    followups.forEach((f, index) => {
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

      item.title = text;

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

  // Phase 3.5 — Collect edit reason from the UI selector
  _collectEditReason() {
    var reasonSelect = document.getElementById('edit-reason-code');
    var noteInput = document.getElementById('edit-freeform-note');
    return {
      reason_code: reasonSelect ? reasonSelect.value : 'unspecified',
      freeform_note: noteInput ? noteInput.value.trim() : '',
    };
  }

  renderConversationContext() {
    const messagesContainer = document.getElementById('conversation-messages');
    if (!messagesContainer) return;

    messagesContainer.innerHTML =
      '<p class="help-text">No conversation history in this request</p>';
  }

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

    this.hideAutoSendCard();
    this._clearMissingVariableChips();
    this._setInsertCrmEnabled(false);
    _lastAutoRunTicketKey = null;

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
// Follow-up questions toggle
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

// Canned Responses Dropdown — click-away close
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

const RALPH_WEEKLY_SUMMARY_URL = '/api/v1/analytics/weekly';

let cachedWeeklySummary = null;
let lastWeeklyFetch = 0;
const WEEKLY_CACHE_MS = 6 * 60 * 60 * 1000;

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

  if (!summary || !summary.total_tickets) {
    body.innerHTML = `<p class="muted">No ticket data for the past 7 days.</p>`;
    return;
  }

  const topIntents = (summary.top_intents || []).slice(0, 3);
  const risk = summary.risk_distribution || {};
  const automationPct = Math.round((summary.automation_rate || 0) * 100);

  body.innerHTML = `
    <div class="summary-section">
      <strong>Tickets (7 days)</strong>
      <p>${summary.total_tickets}</p>
    </div>

    <div class="summary-section">
      <strong>Automation Rate</strong>
      <p>${automationPct}% auto-sent</p>
    </div>

    <div class="summary-section">
      <strong>Top Intents</strong>
      ${
        topIntents.length
          ? '<ul>' +
            topIntents
              .map((i) => `<li>${escapeHtml(i.intent)} (${i.count})</li>`)
              .join('') +
            '</ul>'
          : '<p class="muted">None</p>'
      }
    </div>

    <div class="summary-section">
      <strong>Risk Distribution</strong>
      <ul>
        <li>Low: ${Math.round((risk.low || 0) * 100)}%</li>
        <li>Medium: ${Math.round((risk.medium || 0) * 100)}%</li>
        <li>High: ${Math.round((risk.high || 0) * 100)}%</li>
      </ul>
    </div>

    ${
      summary.generated_at
        ? `<p class="muted">Updated: ${new Date(summary.generated_at).toLocaleDateString()}</p>`
        : ''
    }
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

  document.getElementById('exec-draft-outcome').textContent =
    signals.resolutionLikely ? 'Likely resolved' : 'Follow-up expected';

  document.getElementById('exec-recommended-action').textContent =
    signals.missingInfo
      ? 'Request missing information'
      : 'Send draft as written';

  document.getElementById('exec-auto-send-status').textContent =
    signals.autoSendEligible
      ? 'Eligible (manual review allowed)'
      : 'Not eligible';

  document.getElementById('exec-primary-risk').textContent =
    signals.ambiguityDetected
      ? 'Ambiguous customer intent'
      : signals.safetyRisk
        ? 'Policy / safety risk'
        : 'None detected';

  document.getElementById('exec-notes').textContent =
    signals.notes || 'Based on current ticket signals';
}

function renderDecisionExplanation(explanation) {
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

function handleDraftResponse(data) {
  if (data.decision_explanation) {
    renderDecisionExplanation(data.decision_explanation);
  }
}

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
  console.log('[sidecar] JS loaded — v2.0 auto-run mode');

  window.aiSidecar = new AISidecar();

  if (window.aiSidecar.loadAnalyticsSummary) {
    window.aiSidecar.loadAnalyticsSummary();
  }
});
