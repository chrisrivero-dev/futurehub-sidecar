// static/js/api_client.js
// API client for FutureHub ticket operations
// Day 2: Fetch and send utilities only

class APIClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
    this.headers = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
  }

  /**
   * Generic request handler
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      ...options,
      headers: {
        ...this.headers,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ error: "Unknown error" }));
        throw new Error(error.error || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  /**
   * Fetch single ticket
   */
  async getTicket(ticketId) {
    return this.request(`/api/tickets/${ticketId}`, {
      method: "GET",
    });
  }

  /**
   * Fetch ticket list
   */
  async getTickets(filters = {}) {
    const params = new URLSearchParams(filters);
    const query = params.toString() ? `?${params.toString()}` : "";

    return this.request(`/api/tickets${query}`, {
      method: "GET",
    });
  }

  /**
   * Send reply to ticket
   */
  async sendReply(ticketId, replyData) {
    return this.request(`/api/tickets/${ticketId}/reply`, {
      method: "POST",
      body: JSON.stringify(replyData),
    });
  }

  /**
   * Update ticket status
   */
  async updateTicketStatus(ticketId, status) {
    return this.request(`/api/tickets/${ticketId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  }

  /**
   * Fetch sidecar status for ticket
   */
  async getSidecarStatus(ticketId) {
    return this.request(`/api/tickets/${ticketId}/sidecar/status`, {
      method: "GET",
    });
  }

  /**
   * Trigger sidecar analysis (future use)
   */
  async triggerAnalysis(ticketId) {
    return this.request(`/api/tickets/${ticketId}/analyze`, {
      method: "POST",
    });
  }
}

// Create singleton instance
const apiClient = new APIClient();

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = APIClient;
}
