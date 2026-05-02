# Frontend Standards

Vue 3 + Vite + Arco Design Web Vue development standards.

## Enforced Baseline

Run the frontend source boundary gate before opening or updating a PR that touches frontend code:

```bash
uv run poe frontend-harness
```

`uv run poe harness` runs the same gate. The current deterministic baseline enforces:

- HTTP clients (`axios`, `fetch`, `XMLHttpRequest`) are only used under `src/frontend/src/api`.
- Vue components use `<script setup lang="ts">`.
- Vue component `<style>` blocks are scoped.
- Vue components stay at or below 300 lines.
- Static inline `style="..."` attributes are prohibited; use classes or dynamic `:style`.

## Project Structure

```
src/frontend/src/
  pages/          # Route views, 1:1 with routes, lazy-loaded
  components/     # Reusable UI components, grouped by feature subdirectory
  composables/    # Business logic hooks (useXxx)
  stores/         # Pinia stores (composition API)
  api/            # Axios wrapper, one export per endpoint
  utils/          # Pure utility functions (no Vue dependency)
  domain/         # Pure business logic (no Vue dependency)
  types/          # TypeScript type definitions
```

### Directory Responsibilities

- **pages/**: One file per route. Each page is lazy-loaded via `defineAsyncComponent` or dynamic `import()` in the router. Pages compose components and composables but contain minimal logic themselves.
- **components/**: Reusable UI elements grouped by feature (e.g., `components/model/ModelCard.vue`). Generic components live at the top level (e.g., `components/AppHeader.vue`).
- **composables/**: Encapsulate stateful logic that can be shared across components. Named `useXxx.ts`. May use Vue reactivity but should not render UI.
- **stores/**: Pinia stores for global state. One store per domain concern. Use composition API syntax exclusively.
- **api/**: Centralized API layer. All HTTP calls go through this directory. One function per endpoint.
- **utils/**: Pure functions with no Vue imports. Date formatting, string manipulation, validation helpers.
- **domain/**: Business rules and calculations with no framework dependency. Testable in isolation.
- **types/**: Shared TypeScript interfaces and type aliases. No runtime code.

Generated OpenAPI types live under `src/frontend/src/api/generated/`. Do not edit them by hand; refresh them from the backend contract with `uv run poe api-contracts-write`.

## Component Rules

### Script Setup Only

All components use `<script setup lang="ts">`. No Options API, no `defineComponent()`.

```vue
<script setup lang="ts">
interface Props {
  title: string
  count?: number
}

const props = withDefaults(defineProps<Props>(), {
  count: 0,
})

const emit = defineEmits<{
  update: [value: string]
  close: []
}>()
</script>
```

### Props and Emits

- Define props with a TypeScript interface passed to `defineProps<T>()`.
- Define emits with a TypeScript interface passed to `defineEmits<T>()`.
- Use `withDefaults()` for default values.

### Template Logic

No business logic in templates. If a template expression is more than a simple property access or ternary, move it to a computed property or composable.

```vue
<!-- Correct -->
<span>{{ formattedDate }}</span>

<!-- Wrong -->
<span>{{ new Date(item.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) }}</span>
```

### Component Size

Maximum 300 lines per `.vue` file. If a component exceeds this, extract sub-components or move logic to composables.

## State Management

### Pinia Composition API

All stores use the composition API pattern (setup function):

```typescript
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('auth_token'))
  const user = ref<User | null>(null)
  const isAuthenticated = computed(() => token.value !== null)

  function login(newToken: string, userData: User) {
    token.value = newToken
    user.value = userData
    localStorage.setItem('auth_token', newToken)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('auth_token')
  }

  return { token, user, isAuthenticated, login, logout }
})
```

### Persistence

- Auth tokens and user preferences: `localStorage`.
- No global reactive state outside Pinia. Do not use `reactive()` or `ref()` at module scope as a substitute for a store.

## API Communication

### Centralized API Layer

All API calls go through `src/api/index.ts` (or feature-specific files in `src/api/`). Components never import or call axios directly.

API functions should use generated OpenAPI schema types from `src/api/generated/openapi.ts` for request and response contracts when those schemas exist. The repository harness checks drift with `uv run poe api-contracts`.

```typescript
// api/models.ts
import api from './index'
import type { components } from './generated/openapi'

type Model = components['schemas']['Model']
type ModelListResponse = components['schemas']['APIResponse_ModelList_']

export function listModels(params: ModelListParams) {
  return api.get<ModelListResponse>('/models', { params })
}

export function updateModelStatus(id: string, status: string) {
  return api.patch<Model>(`/models/${id}/status`, { status })
}
```

### Token Refresh

The axios interceptor handles token refresh transparently. Components do not manage token lifecycle.

### WebSocket

For WebSocket connections, pass the auth token as a query parameter since browsers do not support custom headers on WebSocket handshakes:

```typescript
const ws = new WebSocket(`${wsBaseUrl}/ws?token=${token}`)
```

## Styling

### Arco Design

Use Arco Design components as the primary UI library. Do not recreate components that Arco provides (tables, forms, modals, notifications).

### CSS Variables

Use CSS custom properties for theme customization. Override Arco Design variables at the `:root` level for global theming.

### Scoped Styles

All component styles must be scoped:

```vue
<style scoped>
.model-card {
  padding: 16px;
}
</style>
```

### No Inline Styles

Avoid inline styles except for truly dynamic values (e.g., calculated widths, positions). Use classes for all static styling.

```vue
<!-- Acceptable: dynamic value -->
<div :style="{ width: `${progress}%` }">

<!-- Wrong: static styling inline -->
<div style="padding: 16px; color: red;">
```

## Testing

### Tools

- **Vitest** for unit tests.
- **Vue Test Utils** for component tests.

### What to Test

- **Composables**: Test independently from components. Call the composable, assert reactive state and return values.
- **Components**: Test user-visible behavior (renders correct text, emits correct events on interaction). Do not test internal implementation details.
- **API layer**: Mock HTTP responses, verify correct URLs and parameters are sent.
- **Domain logic**: Test as pure functions with no Vue dependency.

### Mocking

Mock API calls at the HTTP layer (e.g., mock axios), not at the implementation level. This keeps tests resilient to refactoring.

```typescript
import { vi } from 'vitest'
import api from '@/api'

vi.spyOn(api, 'get').mockResolvedValue({ data: { code: 0, success: true, data: mockModels, message: 'OK' } })
```
