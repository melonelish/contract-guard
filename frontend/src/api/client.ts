import axios from "axios";

import { useAuthStore } from "../stores/auth";

const apiBaseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: `${apiBaseUrl}/api/v1`,
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Draft API
export const draftApi = {
  get: async (contractId: string) => {
    const response = await apiClient.get(`/contracts/${contractId}/draft`);
    return response.data;
  },
  save: async (contractId: string, content: string) => {
    const response = await apiClient.post(`/contracts/${contractId}/draft`, {
      content,
    });
    return response.data;
  },
};
