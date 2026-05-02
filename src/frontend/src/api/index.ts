import axios, { type AxiosInstance } from "axios";
import type { components } from "./generated/openapi";

export type HealthResponse = components["schemas"]["APIResponse_HealthStatus_"];

const api: AxiosInstance = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// Add auth interceptor here when your project implements authentication

// ---------------------------------------------------------------------------
// Response interceptor: simple error logging
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------
export function getHealth() {
  return api.get<HealthResponse>("/health");
}

// Add more endpoint functions here

export default api;
