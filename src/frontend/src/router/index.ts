import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/dashboard",
  },
  {
    path: "/dashboard",
    name: "Dashboard",
    component: () => import("@/pages/Dashboard.vue"),
  },
  // Add more routes here
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Add auth guard here when implementing authentication

export default router;
