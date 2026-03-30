<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const menuItems = [
  { key: "/dashboard", label: "Dashboard", icon: "icon-dashboard" },
  // Add more menu items here
];

function onMenuSelect(key: string) {
  router.push(key);
}
</script>

<template>
  <a-layout class="app-layout">
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
          <span class="app-title">App</span>
          <div class="header-spacer" />
          <!-- Add user info and logout here when implementing authentication -->
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

.app-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-1);
}

.header-spacer {
  flex: 1;
}

.app-content {
  padding: 20px;
  background: var(--color-bg-1);
}
</style>
