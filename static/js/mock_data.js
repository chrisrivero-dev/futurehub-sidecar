// static/js/mock_data.js
// Mock sidecar responses for frontend development
// Day 2: Test data for UI development without backend

const MOCK_SIDECAR_RESPONSES = {
  // Successful analysis - shipping question
  shipping_success: {
    success: true,
    data: {
      intent: "shipping_status",
      confidence: 0.92,
      analysis: {
        summary: "Customer asking about order delivery status",
        key_entities: ["order number", "shipping", "delivery date"],
        sentiment: "neutral",
        urgency: "medium",
      },
      suggestions: [
        {
          type: "canned_response",
          title: "Check Order Status",
          preview: "I can help you check your order status...",
          confidence: 0.95,
        },
        {
          type: "similar_ticket",
          ticket_id: 123,
          title: "Similar shipping inquiry",
          confidence: 0.88,
        },
      ],
      conversation_id: "conv_mock_001",
    },
    status_code: 200,
    duration_ms: 450,
  },

  // Successful analysis - technical issue
  technical_success: {
    success: true,
    data: {
      intent: "not_hashing",
      confidence: 0.87,
      analysis: {
        summary: "Apollo II device not producing hashrate",
        key_entities: ["hashrate", "Apollo II", "mining stopped"],
        sentiment: "frustrated",
        urgency: "high",
      },
      suggestions: [
        {
          type: "diagnostic_steps",
          title: "Hashrate Troubleshooting",
          preview: "Let's check a few things about your setup...",
          confidence: 0.9,
        },
        {
          type: "escalate",
          title: "Escalate to Technical Team",
          reason: "Requires log analysis",
          confidence: 0.75,
        },
      ],
      conversation_id: "conv_mock_002",
    },
    status_code: 200,
    duration_ms: 680,
  },

  // Timeout
  timeout: {
    success: false,
    data: null,
    error: "Request timed out after 10s",
    status_code: null,
    duration_ms: 10000,
    timed_out: true,
  },

  // Connection error
  connection_error: {
    success: false,
    data: null,
    error: "Connection failed: Service unavailable",
    status_code: null,
    duration_ms: 150,
    timed_out: false,
  },

  // Server error
  server_error: {
    success: false,
    data: null,
    error: "HTTP 500: Internal server error",
    status_code: 500,
    duration_ms: 320,
    timed_out: false,
  },

  // Low confidence
  low_confidence: {
    success: true,
    data: {
      intent: "general_question",
      confidence: 0.62,
      analysis: {
        summary: "Question unclear - multiple possible intents",
        key_entities: [],
        sentiment: "neutral",
        urgency: "low",
      },
      suggestions: [
        {
          type: "ask_clarification",
          title: "Request More Details",
          preview: "Could you provide more information about...",
          confidence: 0.7,
        },
      ],
      conversation_id: "conv_mock_003",
    },
    status_code: 200,
    duration_ms: 420,
  },
};

// Mock ticket data for testing
const MOCK_TICKETS = {
  shipping_ticket: {
    id: 1001,
    subject: "Where is my order?",
    status: "open",
    priority: "medium",
    customer_email: "customer@example.com",
    ai_assistant_enabled: true,
    sidecar_status: "idle",
  },

  technical_ticket: {
    id: 1002,
    subject: "Apollo II not hashing",
    status: "open",
    priority: "high",
    customer_email: "miner@example.com",
    ai_assistant_enabled: true,
    sidecar_status: "idle",
  },
};

// Helper to simulate async sidecar call with delay
function mockSidecarRequest(responseType = "shipping_success", delayMs = 500) {
  return new Promise((resolve) => {
    setTimeout(() => {
      const response = MOCK_SIDECAR_RESPONSES[responseType];
      resolve(response);
    }, delayMs);
  });
}

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    MOCK_SIDECAR_RESPONSES,
    MOCK_TICKETS,
    mockSidecarRequest,
  };
}
