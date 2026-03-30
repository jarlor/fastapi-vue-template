<script setup lang="ts">
import { ref } from "vue";
import { Message } from "@arco-design/web-vue";
import { useAuth } from "@/composables/useAuth";

const { login } = useAuth();

const account = ref("");
const password = ref("");
const loading = ref(false);

async function handleSubmit() {
  if (!account.value || !password.value) {
    Message.warning("Please enter account and password");
    return;
  }

  loading.value = true;
  try {
    // Hash password with SHA-256 before sending
    const encoder = new TextEncoder();
    const data = encoder.encode(password.value);
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const passwordSha = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");

    await login(account.value, passwordSha);
    Message.success("Login successful");
  } catch (error: unknown) {
    const msg =
      error instanceof Error ? error.message : "Login failed. Please check your credentials.";
    Message.error(msg);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-wrapper">
    <div class="login-card">
      <div class="login-header">
        <h1 class="login-title">Welcome</h1>
        <p class="login-subtitle">Sign in to your account</p>
      </div>

      <a-form
        :model="{ account, password }"
        layout="vertical"
        @submit-success="handleSubmit"
      >
        <a-form-item field="account" label="Account" :rules="[{ required: true }]">
          <a-input
            v-model="account"
            placeholder="Enter your account"
            size="large"
            allow-clear
          />
        </a-form-item>

        <a-form-item field="password" label="Password" :rules="[{ required: true }]">
          <a-input-password
            v-model="password"
            placeholder="Enter your password"
            size="large"
            allow-clear
          />
        </a-form-item>

        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            long
            size="large"
            :loading="loading"
          >
            Sign In
          </a-button>
        </a-form-item>
      </a-form>
    </div>
  </div>
</template>

<style scoped>
.login-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--color-bg-1);
}

.login-card {
  width: 400px;
  padding: 40px;
  border-radius: 8px;
  background: var(--color-bg-2);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text-1);
  margin: 0 0 8px;
}

.login-subtitle {
  font-size: 14px;
  color: var(--color-text-3);
  margin: 0;
}
</style>
