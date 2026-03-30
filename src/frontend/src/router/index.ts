import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { getAccessToken } from "@/utils/auth";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/pages/Login.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/",
    redirect: "/dashboard",
  },
  {
    path: "/dashboard",
    name: "Dashboard",
    component: () => import("@/pages/Dashboard.vue"),
    meta: { requiresAuth: true },
  },
  // Add more routes here
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  const token = getAccessToken();
  const requiresAuth = to.meta.requiresAuth !== false;

  if (requiresAuth && !token) {
    next({ name: "Login", query: { redirect: to.fullPath } });
  } else if (to.name === "Login" && token) {
    next({ path: "/dashboard" });
  } else {
    next();
  }
});

export default router;
