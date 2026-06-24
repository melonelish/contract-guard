import { create } from "zustand";

import { apiClient } from "../api/client";
import type { ApiResponse, Contract, ContractDetail } from "../api/types";

interface ContractState {
  items: Contract[];
  selected: ContractDetail | null;
  loading: boolean;
  uploadLoading: boolean;
  error: string | null;
  fetchContracts: () => Promise<void>;
  fetchContractDetail: (id: string) => Promise<void>;
  uploadContract: (file: File, title?: string) => Promise<string>;
  clearError: () => void;
}

export const useContractStore = create<ContractState>((set, get) => ({
  items: [],
  selected: null,
  loading: false,
  uploadLoading: false,
  error: null,
  fetchContracts: async () => {
    set({ loading: true });
    try {
      const response = await apiClient.get<ApiResponse<{ items: Contract[] }>>("/contracts");
      set({ items: response.data.data.items, loading: false });
    } catch (_error) {
      set({ loading: false });
      throw _error;
    }
  },
  fetchContractDetail: async (id) => {
    set({ loading: true, error: null });
    try {
      const response = await apiClient.get<ApiResponse<ContractDetail>>(`/contracts/${id}`);
      set({ selected: response.data.data, loading: false, error: null });
    } catch (_error) {
      const axiosError = _error as { code?: string; message?: string };
      let errorMsg = '加载合同详情失败';

      if (axiosError.code === 'ERR_NETWORK' || axiosError.message?.includes('Network Error')) {
        errorMsg = '后端服务未启动或网络连接失败';
      }

      set({ loading: false, error: errorMsg, selected: null });
      throw _error;
    }
  },
  uploadContract: async (file, title) => {
    set({ uploadLoading: true });
    const formData = new FormData();
    formData.append("file", file);
    if (title) {
      formData.append("title", title);
    }
    try {
      const response = await apiClient.post<ApiResponse<Contract>>("/contracts/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      set({
        items: [response.data.data, ...get().items],
        uploadLoading: false,
      });
      return response.data.data.id;
    } catch (_error) {
      set({ uploadLoading: false });
      throw _error;
    }
  },
  clearError: () => set({ error: null }),
}));
