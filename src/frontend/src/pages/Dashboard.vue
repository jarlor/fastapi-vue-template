<script setup lang="ts">
import { useAuth } from "@/composables/useAuth";

const { currentUser } = useAuth();
</script>

<template>
  <div class="dashboard">
    <a-page-header title="Dashboard" subtitle="Overview" />

    <a-card class="welcome-card">
      <template #title>
        Welcome{{ currentUser ? `, ${currentUser.display_name || currentUser.account}` : "" }}
      </template>
      <p class="welcome-text">
        This is your dashboard. Replace this content with your application's main view.
      </p>
    </a-card>

    <a-row :gutter="16" style="margin-top: 16px">
      <a-col :span="8">
        <a-card title="Placeholder A">
          <a-statistic title="Items" :value="0" />
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="Placeholder B">
          <a-statistic title="Tasks" :value="0" />
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="Placeholder C">
          <a-statistic title="Users" :value="0" />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 1200px;
}

.welcome-card {
  margin-top: 8px;
}

.welcome-text {
  color: var(--color-text-2);
  margin: 0;
}
</style>
