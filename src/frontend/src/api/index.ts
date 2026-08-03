import axios, { type AxiosInstance } from "axios";
import type { components } from "./generated/openapi";

export type HealthResponse = components["schemas"]["APIResponse_HealthStatus_"];
export type Task = components["schemas"]["TaskRead"];
export type CreateTaskInput = components["schemas"]["TaskCreate"];
export type TaskResponse = components["schemas"]["APIResponse_TaskRead_"];
export type TaskListResponse = components["schemas"]["APIResponse_list_TaskRead__"];

const api: AxiosInstance = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

function attachErrorLogging(client: AxiosInstance) {
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      console.error("[API Error]", error.response?.status, error.message);
      return Promise.reject(error);
    },
  );
}

attachErrorLogging(api);

export function getHealth() {
  return api.get<HealthResponse>("/health");
}

export function listTasks() {
  return api.get<TaskListResponse>("/tasks");
}

export function createTask(input: CreateTaskInput) {
  return api.post<TaskResponse>("/tasks", input);
}

export default api;
