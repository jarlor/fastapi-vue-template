import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";
import { getAccessToken, getRefreshToken, saveAuthSession, clearAuthSession } from "@/utils/auth";

const api: AxiosInstance = axios.create({
  baseURL: "/api/internal/v1",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// ---------------------------------------------------------------------------
// Request interceptor: attach Bearer token
// ---------------------------------------------------------------------------
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ---------------------------------------------------------------------------
// Response interceptor: handle 401 with token refresh
// ---------------------------------------------------------------------------
let isRefreshing = false;
let pendingRequests: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function onRefreshSuccess(newToken: string): void {
  pendingRequests.forEach(({ resolve }) => resolve(newToken));
  pendingRequests = [];
}

function onRefreshFailure(error: unknown): void {
  pendingRequests.forEach(({ reject }) => reject(error));
  pendingRequests = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearAuthSession();
      window.location.href = "/login";
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        pendingRequests.push({ resolve, reject });
      }).then((token) => {
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${token}`;
        }
        originalRequest._retry = true;
        return api(originalRequest);
      });
    }

    isRefreshing = true;
    originalRequest._retry = true;

    try {
      const { data } = await authRefresh(refreshToken);
      saveAuthSession(data);
      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
      }
      onRefreshSuccess(data.access_token);
      return api(originalRequest);
    } catch (refreshError) {
      onRefreshFailure(refreshError);
      clearAuthSession();
      window.location.href = "/login";
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
}

export interface UserInfo {
  id: string;
  account: string;
  display_name?: string;
  [key: string]: unknown;
}

export function authLogin(account: string, passwordSha: string) {
  return api.post<LoginResponse>("/auth/login", {
    account,
    password_sha: passwordSha,
  });
}

export function authRefresh(refreshToken: string) {
  return api.post<LoginResponse>("/auth/refresh", {
    refresh_token: refreshToken,
  });
}

export function authMe() {
  return api.get<UserInfo>("/auth/me");
}

export function authLogout() {
  return api.post("/auth/logout");
}

// ---------------------------------------------------------------------------
// Add more endpoint functions here
// ---------------------------------------------------------------------------
// export function getItems(params?: Record<string, unknown>) {
//   return api.get("/items", { params });
// }
// export function getItemById(id: string) {
//   return api.get(`/items/${id}`);
// }

export default api;
