import { computed } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

export function useAuth() {
  const store = useAuthStore();
  const router = useRouter();

  const isAuthenticated = computed(() => store.isAuthenticated);
  const currentUser = computed(() => store.user);

  async function login(account: string, passwordSha: string): Promise<void> {
    await store.login(account, passwordSha);
    await router.push("/dashboard");
  }

  function logout(): void {
    store.logout();
    router.push("/login");
  }

  return {
    isAuthenticated,
    currentUser,
    login,
    logout,
  };
}
