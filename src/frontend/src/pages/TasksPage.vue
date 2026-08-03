<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";

import { createTask, listTasks, type Task } from "@/api";

const tasks = ref<Task[]>([]);
const form = reactive({ title: "" });
const loading = ref(false);
const error = ref("");

async function refreshTasks() {
  loading.value = true;
  error.value = "";
  try {
    const response = await listTasks();
    tasks.value = response.data.data ?? [];
  } catch {
    error.value = "Unable to load tasks. Is the API running?";
  } finally {
    loading.value = false;
  }
}

async function submitTask() {
  const normalized = form.title.trim();
  if (!normalized) return;

  loading.value = true;
  error.value = "";
  try {
    await createTask({ title: normalized });
    form.title = "";
    await refreshTasks();
  } catch {
    error.value = "Unable to create the task.";
    loading.value = false;
  }
}

onMounted(refreshTasks);
</script>

<template>
  <div class="dashboard">
    <a-page-header
      title="Reference task context"
      subtitle="A runnable architecture slice protected by API contracts and acceptance tests"
    />

    <a-card class="task-card" title="Tasks">
      <a-form :model="form" layout="inline" @submit="submitTask">
        <a-input
          v-model="form.title"
          :disabled="loading"
          placeholder="Add a task"
          allow-clear
        />
        <a-button html-type="submit" type="primary" :loading="loading">
          Create
        </a-button>
      </a-form>

      <a-alert v-if="error" type="error" class="feedback">{{ error }}</a-alert>

      <a-list :loading="loading" :data="tasks" class="task-list">
        <template #item="{ item }">
          <a-list-item>
            <a-checkbox :model-value="item.completed" disabled />
            <span>{{ item.title }}</span>
          </a-list-item>
        </template>
        <template #empty>
          <a-empty description="Create the first task to exercise the full stack" />
        </template>
      </a-list>
    </a-card>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 960px;
}

.task-card {
  margin-top: 8px;
}

.feedback,
.task-list {
  margin-top: 20px;
}
</style>
