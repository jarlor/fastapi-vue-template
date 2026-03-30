import axios, { type AxiosInstance } from "axios";

const api: AxiosInstance = axios.create({
  baseURL: "/api/internal/v1",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// Add auth interceptor here when implementing authentication

// ---------------------------------------------------------------------------
// Response interceptor: simple error logging
// ---------------------------------------------------------------------------
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("[API Error]", error.response?.status, error.message);
    return Promise.reject(error);
  },
);

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------
export function getHealth() {
  return api.get<{ status: string }>("/health");
}

// Add more endpoint functions here

export default api;
