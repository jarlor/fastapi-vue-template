import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { authLogin as apiLogin, authMe, authLogout as apiLogout } from "@/api";
import type { UserInfo } from "@/api";
import {
  saveAuthSession,
  clearAuthSession,
  getAccessToken,
  getSavedUser,
  saveUser,
} from "@/utils/auth";

export const useAuthStore = defineStore("auth", () => {
  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------
  const user = ref<UserInfo | null>(getSavedUser<UserInfo>());
  const token = ref<string | null>(getAccessToken());

  // -------------------------------------------------------------------------
  // Getters
  // -------------------------------------------------------------------------
  const isAuthenticated = computed(() => !!token.value);

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------
  async function login(account: string, passwordSha: string): Promise<void> {
    const { data } = await apiLogin(account, passwordSha);
    saveAuthSession(data);
    token.value = data.access_token;
    await fetchUser();
  }

  async function fetchUser(): Promise<void> {
    try {
      const { data } = await authMe();
      user.value = data;
      saveUser(data);
    } catch {
      user.value = null;
    }
  }

  function logout(): void {
    apiLogout().catch(() => {
      /* best effort */
    });
    clearAuthSession();
    user.value = null;
    token.value = null;
  }

  return {
    user,
    token,
    isAuthenticated,
    login,
    fetchUser,
    logout,
  };
});
