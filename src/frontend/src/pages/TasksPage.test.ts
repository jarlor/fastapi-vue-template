// @vitest-environment happy-dom

import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TasksPage from "./TasksPage.vue";

const { createTaskMock, listTasksMock } = vi.hoisted(() => ({
  createTaskMock: vi.fn(),
  listTasksMock: vi.fn(),
}));

vi.mock("@/api", () => ({
  createTask: createTaskMock,
  listTasks: listTasksMock,
}));

const PassthroughStub = defineComponent({
  template: "<div><slot /></div>",
});

const FormStub = defineComponent({
  emits: ["submit"],
  template:
    '<form data-testid="task-form" @submit.prevent="$emit(\'submit\', { values: {}, errors: undefined }, $event)"><slot /></form>',
});

const InputStub = defineComponent({
  props: {
    modelValue: {
      type: String,
      default: "",
    },
  },
  emits: ["update:modelValue"],
  template: `
    <input
      data-testid="task-title"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
    />
  `,
});

const AlertStub = defineComponent({
  template: '<div role="alert"><slot /></div>',
});

const ListStub = defineComponent({
  props: {
    data: {
      type: Array,
      default: () => [],
    },
  },
  template: `
    <div>
      <template v-for="item in data" :key="item.id">
        <slot name="item" :item="item" />
      </template>
      <slot v-if="data.length === 0" name="empty" />
    </div>
  `,
});

function mountPage() {
  return mount(TasksPage, {
    global: {
      stubs: {
        "a-alert": AlertStub,
        "a-button": PassthroughStub,
        "a-card": PassthroughStub,
        "a-checkbox": true,
        "a-empty": true,
        "a-form": FormStub,
        "a-input": InputStub,
        "a-list": ListStub,
        "a-list-item": PassthroughStub,
        "a-page-header": true,
      },
    },
  });
}

function taskResponse(tasks: Array<{ id: string; title: string; completed: boolean }>) {
  return {
    data: {
      code: 0,
      success: true,
      data: tasks,
      message: "OK",
    },
  };
}

describe("TasksPage", () => {
  beforeEach(() => {
    createTaskMock.mockReset();
    listTasksMock.mockReset();
  });

  it("loads and renders tasks when mounted", async () => {
    listTasksMock.mockResolvedValue(
      taskResponse([{ id: "task-1", title: "Protect the boundary", completed: false }]),
    );

    const wrapper = mountPage();
    await flushPromises();

    expect(listTasksMock).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Protect the boundary");
  });

  it("creates a normalized task and refreshes the list", async () => {
    listTasksMock
      .mockResolvedValueOnce(taskResponse([]))
      .mockResolvedValueOnce(
        taskResponse([{ id: "task-2", title: "Review the slice", completed: false }]),
      );
    createTaskMock.mockResolvedValue(taskResponse([]));

    const wrapper = mountPage();
    await flushPromises();
    await wrapper.get('[data-testid="task-title"]').setValue("  Review the slice  ");
    await wrapper.get('[data-testid="task-form"]').trigger("submit");
    await flushPromises();

    expect(createTaskMock).toHaveBeenCalledWith({ title: "Review the slice" });
    expect(listTasksMock).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain("Review the slice");
    expect(wrapper.get<HTMLInputElement>('[data-testid="task-title"]').element.value).toBe("");
  });

  it("shows feedback when task creation fails", async () => {
    listTasksMock.mockResolvedValue(taskResponse([]));
    createTaskMock.mockRejectedValue(new Error("offline"));

    const wrapper = mountPage();
    await flushPromises();
    await wrapper.get('[data-testid="task-title"]').setValue("Ship safely");
    await wrapper.get('[data-testid="task-form"]').trigger("submit");
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toBe("Unable to create the task.");
  });
});
