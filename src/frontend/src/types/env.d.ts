/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly APP_FRONTEND_PORT: string;
  readonly APP_BACKEND_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<object, object, unknown>;
  export default component;
}
