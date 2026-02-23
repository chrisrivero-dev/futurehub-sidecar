// static/js/draft_edit_tracker.js
// Phase 3.5 — Client-side draft edit capture
// Computes diffs locally. Never sends full message bodies to backend.

(function () {
  'use strict';

  // ── Ephemeral draft store (in-memory only, never persisted) ──
  let _currentDraft = null;

  /**
   * Store a draft in memory when Sidecar generates one.
   * draft_text is held ephemerally for diff computation only.
   */
  function storeDraft(opts) {
    _currentDraft = {
      draft_id: opts.draft_id || _generateDraftId(),
      trace_id: opts.trace_id || null,
      draft_text: opts.draft_text || '',
      draft_length: (opts.draft_text || '').length,
      stored_at: Date.now(),
    };
    return _currentDraft.draft_id;
  }

  /** Retrieve the current ephemeral draft (or null). */
  function getCurrentDraft() {
    return _currentDraft;
  }

  /** Clear the ephemeral draft from memory. */
  function clearDraft() {
    _currentDraft = null;
  }

  // ── Levenshtein edit distance (char-level) ──────────────────
  // Optimised single-row DP — O(min(m,n)) space.
  function _editDistance(a, b) {
    if (a === b) return 0;
    if (!a.length) return b.length;
    if (!b.length) return a.length;

    // Ensure a is the shorter string for space efficiency
    if (a.length > b.length) {
      var tmp = a; a = b; b = tmp;
    }
    var la = a.length;
    var lb = b.length;
    var prev = new Array(la + 1);
    var curr = new Array(la + 1);
    for (var i = 0; i <= la; i++) prev[i] = i;

    for (var j = 1; j <= lb; j++) {
      curr[0] = j;
      for (var k = 1; k <= la; k++) {
        var cost = a[k - 1] === b[j - 1] ? 0 : 1;
        curr[k] = Math.min(
          prev[k] + 1,       // deletion
          curr[k - 1] + 1,   // insertion
          prev[k - 1] + cost  // substitution
        );
      }
      var swap = prev; prev = curr; curr = swap;
    }
    return prev[la];
  }

  /**
   * Compute diff metrics between original draft and final text.
   * All computation is local — no text leaves the browser.
   *
   * Returns: { edit_distance_chars, edit_ratio, added_chars, removed_chars }
   */
  function computeDiff(originalText, finalText) {
    var origLen = (originalText || '').length;
    var finalLen = (finalText || '').length;

    var editDist = _editDistance(originalText || '', finalText || '');
    var maxLen = Math.max(origLen, finalLen, 1);

    return {
      edit_distance_chars: editDist,
      edit_ratio: parseFloat((editDist / maxLen).toFixed(4)),
      added_chars: Math.max(0, finalLen - origLen),
      removed_chars: Math.max(0, origLen - finalLen),
    };
  }

  /**
   * Classify the edit outcome and return the appropriate event type.
   *   - edit_ratio < 0.05  → "draft_inserted"
   *   - edit_ratio >= 0.05 → "agent_edited"
   *   - draft not present  → "draft_discarded"
   */
  function classifyEdit(diffMetrics, draftWasPresent) {
    if (!draftWasPresent) return 'draft_discarded';
    if (diffMetrics.edit_ratio < 0.05) return 'draft_inserted';
    return 'agent_edited';
  }

  /**
   * Fire an audit event to the backend.
   * Non-blocking: uses sendBeacon where available, falls back to fire-and-forget fetch.
   * Never delays the Send action.
   */
  function _emitAuditEvent(eventType, payload) {
    var url = '/api/v1/feedback/audit-event';
    var body = JSON.stringify({ event_type: eventType, payload: payload });

    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }));
      } else {
        fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: body,
          keepalive: true,
        }).catch(function () { /* swallow */ });
      }
    } catch (e) {
      // Never block on audit failures
    }
  }

  /**
   * Emit draft_presented event.
   * Called immediately after Sidecar renders a draft.
   */
  function emitDraftPresented(opts) {
    _emitAuditEvent('draft_presented', {
      trace_id: opts.trace_id || null,
      ticket_id: opts.ticket_id || null,
      intent: opts.intent || null,
      confidence: opts.confidence || null,
      latency_ms: opts.latency_ms || null,
      tokens: opts.tokens || null,
      cost: opts.cost || null,
    });
  }

  /**
   * Process the Send action:
   * 1. Grab final editor text
   * 2. Compute diff against stored draft
   * 3. Emit audit event (non-blocking)
   * 4. Clear ephemeral draft
   *
   * @param {string} finalText - The final text from the editor
   * @param {object} [editMeta] - Optional: { reason_code, freeform_note }
   */
  function processSendAction(finalText, editMeta) {
    var draft = _currentDraft;
    var draftWasPresent = !!(draft && draft.draft_text);

    var diff = computeDiff(
      draftWasPresent ? draft.draft_text : '',
      finalText || ''
    );

    var eventType = classifyEdit(diff, draftWasPresent);

    var payload = {
      trace_id: draft ? draft.trace_id : null,
      draft_id: draft ? draft.draft_id : null,
      edit_distance_chars: diff.edit_distance_chars,
      edit_ratio: diff.edit_ratio,
      added_chars: diff.added_chars,
      removed_chars: diff.removed_chars,
    };

    if (eventType === 'agent_edited') {
      payload.reason_code = (editMeta && editMeta.reason_code) || 'unspecified';
      payload.freeform_note = (editMeta && editMeta.freeform_note) || '';
    }

    _emitAuditEvent(eventType, payload);

    // Clear ephemeral draft after send
    clearDraft();
  }

  // ── Tiny draft ID generator ─────────────────────────────────
  function _generateDraftId() {
    return 'dft_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8);
  }

  // ── Public API ──────────────────────────────────────────────
  window.DraftEditTracker = {
    storeDraft: storeDraft,
    getCurrentDraft: getCurrentDraft,
    clearDraft: clearDraft,
    computeDiff: computeDiff,
    classifyEdit: classifyEdit,
    emitDraftPresented: emitDraftPresented,
    processSendAction: processSendAction,
  };
})();
