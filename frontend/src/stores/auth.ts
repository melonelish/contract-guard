import { create } from "zustand";
import { persist } from "zustand/middleware";

import { apiClient } from "../api/client";
import type { ApiResponse, AuthPayload, User } from "../api/types";

interface LoginInput {
  email: string;
  password: string;
}

interface RegisterInput extends LoginInput {
  name?: string;
  tenant_name: string;
}

interface AuthState {
  token: string | null;
  currentUser: User | null;
  loading: boolean;
  error: string | null;
  login: (input: LoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
  hydrateCurrentUser: () => Promise<void>;
}

function applyAuth(payload: AuthPayload, set: (state: Partial<AuthState>) => void) {
  set({
    token: payload.access_token,
    currentUser: payload.user,
    loading: false,
    error: null,
  });
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      currentUser: null,
      loading: false,
      error: null,
      login: async (input) => {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.post<ApiResponse<AuthPayload>>("/auth/login", input);
          applyAuth(response.data.data, set);
        } catch (error) {
          set({ loading: false, error: "登录失败，请检查邮箱和密码。" });
          throw error;
        }
      },
      register: async (input) => {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.post<ApiResponse<AuthPayload>>("/auth/register", input);
          applyAuth(response.data.data, set);
        } catch (error) {
          set({ loading: false, error: "注册失败，请更换邮箱后重试。" });
          throw error;
        }
      },
      logout: () => set({ token: null, currentUser: null, error: null }),
      hydrateCurrentUser: async () => {
        if (!useAuthStore.getState().token) {
          return;
        }
        try {
          const response = await apiClient.get<ApiResponse<User>>("/auth/me");
          set({ currentUser: response.data.data });
        } catch (_error) {
          set({ token: null, currentUser: null });
        }
      },
    }),
    {
      name: "contractguard-auth",
      partialize: (state) => ({
        token: state.token,
        currentUser: state.currentUser,
      }),
    },
  ),
);
