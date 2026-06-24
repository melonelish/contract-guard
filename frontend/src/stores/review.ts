import { create } from "zustand";

import { apiClient } from "../api/client";
import type {
  ApiResponse,
  Review,
  ReviewReport,
  WSEvent,
  WSTicket,
} from "../api/types";

interface ReviewState {
  current: ReviewReport | null;
  loading: boolean;
  loadError: string | null;
  triggerLoading: boolean;

  /** Phase 4: WebSocket connection state */
  wsConnected: boolean;
  wsError: string | null;

  /** Trigger a new review for a contract. Returns the review ID. */
  triggerReview: (contractId: string, useDraft?: boolean) => Promise<string>;

  /** Fetch full review report. */
  fetchReport: (reviewId: string) => Promise<void>;

  /** Poll review status (lightweight). Returns the review status. */
  pollStatus: (reviewId: string) => Promise<Review>;

  /**
   * Phase 4: Connect to WebSocket for real-time progress.
   * Returns cleanup function. onDisconnect is called when the WS drops
   * mid-session (not on clean complete/failed close).
   */
  connectReviewWS: (
    reviewId: string,
    onStage: (event: WSEvent & { event: "stage" }) => void,
    onComplete: (event: WSEvent & { event: "complete" }) => void,
    onFailed: (event: WSEvent & { event: "failed" }) => void,
    onDisconnect?: () => void,
  ) => () => void;

  /** Clear current report. */
  clear: () => void;
}

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function getWsBaseUrl(): string {
  // Convert http:// to ws:// and https:// to wss://
  return API_BASE_URL.replace(/^http/, "ws");
}

export const useReviewStore = create<ReviewState>((set, get) => ({
  current: null,
  loading: false,
  loadError: null,
  triggerLoading: false,
  wsConnected: false,
  wsError: null,

  triggerReview: async (contractId, useDraft = false) => {
    set({ triggerLoading: true });
    try {
      const url = `/contracts/${contractId}/review${useDraft ? '?use_draft=true' : ''}`;
      const response = await apiClient.post<ApiResponse<Review>>(url);
      set({ triggerLoading: false });
      return response.data.data.id;
    } catch (error) {
      set({ triggerLoading: false });
      throw error;
    }
  },

  fetchReport: async (reviewId) => {
    set({ loading: true, loadError: null });
    try {
      const response = await apiClient.get<ApiResponse<ReviewReport>>(
        `/reviews/${reviewId}`,
      );
      set({ current: response.data.data, loading: false, loadError: null });
    } catch (error: unknown) {
      let msg = "报告加载失败，请重试";
      if (error && typeof error === "object" && "response" in error) {
        const axiosErr = error as { response?: { status?: number } };
        const status = axiosErr.response?.status;
        if (status === 404) {
          msg = "报告不存在或已被删除";
        } else if (status === 500) {
          msg = "服务暂时不可用，请稍后重试";
        }
      }
      set({ loading: false, loadError: msg });
    }
  },

  pollStatus: async (reviewId) => {
    const response = await apiClient.get<ApiResponse<Review>>(
      `/reviews/${reviewId}/status`,
    );
    return response.data.data;
  },

  connectReviewWS: (reviewId, onStage, onComplete, onFailed, onDisconnect) => {
    let ws: WebSocket | null = null;
    let closed = false;
    let finishedNormally = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const cleanup = () => {
      closed = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (ws) {
        ws.close();
        ws = null;
      }
      set({ wsConnected: false });
    };

    const connect = async () => {
      if (closed) return;

      try {
        // Step 1: Request a ticket
        const token = localStorage.getItem("contractguard-auth");
        const tokenValue = token ? JSON.parse(token)?.state?.token : null;

        const ticketResponse = await apiClient.post<ApiResponse<WSTicket>>(
          `/reviews/ws/ticket?review_id=${reviewId}`,
        );
        const ticketData = ticketResponse.data.data;

        if (closed) return;

        // Step 2: Open WebSocket with ticket
        const wsUrl = `${getWsBaseUrl()}/ws/review/${reviewId}?ticket=${encodeURIComponent(ticketData.ticket)}`;
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          if (!closed) {
            set({ wsConnected: true, wsError: null });
          }
        };

        ws.onmessage = (event) => {
          if (closed) return;
          try {
            const data: WSEvent = JSON.parse(event.data);

            switch (data.event) {
              case "stage":
                onStage(data);
                break;
              case "complete":
                finishedNormally = true;
                onComplete(data);
                cleanup();
                break;
              case "failed":
                finishedNormally = true;
                onFailed(data);
                cleanup();
                break;
              case "ping":
                ws?.send("ping");
                break;
            }
          } catch {
            // Ignore parse errors
          }
        };

        ws.onerror = () => {
          if (!closed) {
            set({ wsError: "WebSocket connection error" });
            cleanup();
            // Phase 4.1: notify caller to fall back to polling
            if (!finishedNormally && onDisconnect) {
              onDisconnect();
            }
          }
        };

        ws.onclose = (event) => {
          if (!closed) {
            set({ wsConnected: false });
            // Any close that is NOT a clean terminal (1000 = normal,
            // 4001 = auth rejection) should trigger fallback to polling.
            // This includes 4002 (max duration timeout) and abnormal drops.
            if (!finishedNormally && event.code !== 1000 && event.code !== 4001) {
              set({ wsError: "WebSocket disconnected" });
              if (onDisconnect) {
                onDisconnect();
              }
            }
          }
        };
      } catch {
        // Ticket request failed — fall back to polling
        if (!closed) {
          set({ wsError: "Failed to get WebSocket ticket" });
          cleanup();
        }
      }
    };

    void connect();

    return cleanup;
  },

  clear: () => {
    set({ current: null, loadError: null, wsConnected: false, wsError: null });
  },
}));
