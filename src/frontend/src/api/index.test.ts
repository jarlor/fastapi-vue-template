import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { createMock, apiGet, interceptorUse } = vi.hoisted(() => ({
  createMock: vi.fn(),
  apiGet: vi.fn(),
  interceptorUse: vi.fn(),
}));

vi.mock("axios", () => {
  return {
    default: { create: createMock },
  };
});

function queueClients() {
  createMock
    .mockReset()
    .mockImplementation(() => ({
      get: apiGet,
      interceptors: { response: { use: interceptorUse } },
    }));
}

describe("api client", () => {
  beforeEach(() => {
    vi.resetModules();
    queueClients();
    apiGet.mockReset();
    interceptorUse.mockClear();
  });

  it("routes health checks through the versioned API client", async () => {
    apiGet.mockResolvedValue({ data: { success: true } });

    const { getHealth } = await import("./index");

    await getHealth();

    expect(apiGet).toHaveBeenCalledWith("/health");
  });

  it("creates a single v1 API client", async () => {
    await import("./index");

    expect(axios.create).toHaveBeenCalledTimes(1);
    expect(axios.create).toHaveBeenCalledWith(
      expect.objectContaining({ baseURL: "/api/v1" }),
    );
  });
});
