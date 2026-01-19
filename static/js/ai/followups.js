const FOLLOWUP_POOLS = {
  shipping_status: [
    "Do you have your order number handy?",
    "Was this a recent order or an older one?",
    "Did you receive a shipping confirmation email?",
    "Are you located in the US or internationally?",
    "About when did you place the order?",
  ],
  setup_help: [
    "Which Apollo model are you setting up?",
    "Are you able to access the dashboard at all?",
    "Are you using Wi-Fi or Ethernet?",
    "What step are you currently stuck on?",
    "Is the device powered on and showing lights?",
  ],
  not_hashing: [
    "Did this device ever hash correctly before?",
    "What hash rate are you seeing right now?",
    "When did the hashing issue start?",
    "Have you made any recent changes?",
    "Are you seeing any error messages?",
  ],
  connectivity_issue: [
    "Are you able to access the dashboard at all?",
    "Are you connecting from the same network?",
    "Are you using Wi-Fi or Ethernet?",
    "Does the device appear online right now?",
    "Did this connection work previously?",
  ],
  firmware_issue: [
    "What firmware version is the device currently running?",
    "Did this issue start after a recent update?",
    "Were you able to complete the update successfully?",
    "Is the device booting normally right now?",
    "Have you updated this device before?",
  ],
};

const FALLBACK_TEXT = "Let me know what you'd like help with next.";

function getFollowupPool(intent) {
  return FOLLOWUP_POOLS[intent] || [];
}

function filterFollowups(draftText, candidates) {
  if (!draftText || !candidates || candidates.length === 0) {
    return [];
  }

  const draftLower = draftText.toLowerCase();
  const seen = new Set();
  const filtered = [];

  for (const question of candidates) {
    const qLower = question.toLowerCase();

    if (seen.has(qLower)) {
      continue;
    }

    if (draftLower.includes(qLower)) {
      continue;
    }

    seen.add(qLower);
    filtered.push(question);
  }

  return filtered;
}

function shouldCallLLM(state) {
  const {
    candidateCount,
    autoSendTriggered,
    intentConfidence,
    followupsAlreadyShown,
  } = state;

  if (candidateCount === 0) return false;
  if (candidateCount <= 3) return false;
  if (autoSendTriggered) return false;
  if (intentConfidence < 0.35) return false;
  if (followupsAlreadyShown) return false;

  return true;
}

function rankFollowupsLLM(draftText, candidates, llmRankFn) {
  if (!candidates || candidates.length === 0) {
    return [];
  }

  if (candidates.length <= 3) {
    return candidates.slice(0, 3);
  }

  if (!llmRankFn) {
    return candidates.slice(0, 3);
  }

  const ranked = llmRankFn(draftText, candidates);

  if (!ranked || !Array.isArray(ranked)) {
    return candidates.slice(0, 3);
  }

  return ranked.slice(0, 3);
}

function buildFollowups(state, llmRankFn) {
  const {
    autoSendTriggered,
    primaryIntent,
    intentConfidence,
    draftText,
    followupsAlreadyShown,
  } = state;

  if (autoSendTriggered) {
    return null;
  }

  if (!primaryIntent) {
    return { type: "fallback", text: FALLBACK_TEXT };
  }

  const pool = getFollowupPool(primaryIntent);

  if (pool.length === 0) {
    return { type: "fallback", text: FALLBACK_TEXT };
  }

  const filtered = filterFollowups(draftText, pool);

  if (filtered.length === 0) {
    return { type: "fallback", text: FALLBACK_TEXT };
  }

  const llmState = {
    candidateCount: filtered.length,
    autoSendTriggered: autoSendTriggered,
    intentConfidence: intentConfidence,
    followupsAlreadyShown: followupsAlreadyShown,
  };

  if (shouldCallLLM(llmState)) {
    const ranked = rankFollowupsLLM(draftText, filtered, llmRankFn);
    if (ranked.length === 0) {
      return { type: "fallback", text: FALLBACK_TEXT };
    }
    return { type: "questions", items: ranked };
  }

  const finalQuestions = filtered.slice(0, 3);

  if (finalQuestions.length === 0) {
    return { type: "fallback", text: FALLBACK_TEXT };
  }

  return { type: "questions", items: finalQuestions };
}
