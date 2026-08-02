import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/tasks",
  },
  {
    path: "/tasks",
    name: "Tasks",
    component: () => import("@/pages/TasksPage.vue"),
  },
  // Add more routes here
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Add auth guard here when implementing authentication

export default router;
