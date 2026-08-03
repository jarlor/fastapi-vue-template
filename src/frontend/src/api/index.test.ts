import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { createMock, apiGet, apiPost, interceptorUse } = vi.hoisted(() => ({
  createMock: vi.fn(),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  interceptorUse: vi.fn(),
}));

vi.mock("axios", () => ({ default: { create: createMock } }));

function queueClients() {
  createMock.mockReset().mockImplementation(() => ({
    get: apiGet,
    post: apiPost,
    interceptors: { response: { use: interceptorUse } },
  }));
}

describe("api client", () => {
  beforeEach(() => {
    vi.resetModules();
    queueClients();
    apiGet.mockReset();
    apiPost.mockReset();
    interceptorUse.mockClear();
  });

  it("uses one versioned client", async () => {
    await import("./index");

    expect(axios.create).toHaveBeenCalledTimes(1);
    expect(axios.create).toHaveBeenCalledWith(
      expect.objectContaining({ baseURL: "/api/v1" }),
    );
  });

  it("routes task reads and writes through the API layer", async () => {
    apiGet.mockResolvedValue({ data: { success: true, data: [] } });
    apiPost.mockResolvedValue({ data: { success: true } });
    const { createTask, listTasks } = await import("./index");

    await listTasks();
    await createTask({ title: "Keep the oracle independent" });

    expect(apiGet).toHaveBeenCalledWith("/tasks");
    expect(apiPost).toHaveBeenCalledWith("/tasks", {
      title: "Keep the oracle independent",
    });
  });
});
