<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuth } from "@/composables/useAuth";

const route = useRoute();
const router = useRouter();
const { isAuthenticated, currentUser, logout } = useAuth();

const showLayout = computed(() => route.name !== "Login");

const menuItems = [
  { key: "/dashboard", label: "Dashboard", icon: "icon-dashboard" },
  // Add more menu items here
];

function onMenuSelect(key: string) {
  router.push(key);
}
</script>

<template>
  <!-- Login page: no layout shell -->
  <router-view v-if="!showLayout" />

  <!-- Authenticated layout -->
  <a-layout v-else class="app-layout">
    <a-layout-sider class="app-sider" :width="220" collapsible>
      <div class="sider-logo">
        <span class="logo-text">App</span>
      </div>
      <a-menu
        :selected-keys="[route.path]"
        @menu-item-click="onMenuSelect"
      >
        <a-menu-item v-for="item in menuItems" :key="item.key">
          <template #icon><icon-apps /></template>
          {{ item.label }}
        </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header class="app-header">
        <div class="header-content">
          <div class="header-spacer" />
          <div class="header-actions">
            <span v-if="currentUser" class="user-info">
              {{ currentUser.display_name || currentUser.account }}
            </span>
            <a-button
              v-if="isAuthenticated"
              type="text"
              size="small"
              @click="logout"
            >
              Logout
            </a-button>
          </div>
        </div>
      </a-layout-header>

      <a-layout-content class="app-content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.app-sider {
  background: var(--color-bg-2);
}

.sider-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: var(--header-height, 60px);
  border-bottom: 1px solid var(--color-border);
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-1);
}

.app-header {
  height: var(--header-height, 60px);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-2);
  padding: 0 20px;
}

.header-content {
  display: flex;
  align-items: center;
  height: 100%;
}

.header-spacer {
  flex: 1;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-info {
  font-size: 14px;
  color: var(--color-text-2);
}

.app-content {
  padding: 20px;
  background: var(--color-bg-1);
}
</style>
