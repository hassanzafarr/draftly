import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { openEventStream, watchProposal } from "./sse";
import api from "./client";

function sseResponse(frames, { ok = true, status = 200 } = {}) {
  const encoder = new TextEncoder();
  const body = new ReadableStream({
    start(controller) {
      frames.forEach((frame) => controller.enqueue(encoder.encode(frame)));
      controller.close();
    },
  });
  return { ok, status, body };
}

beforeEach(() => {
  localStorage.setItem("access_token", "test-token");
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("openEventStream", () => {
  it("parses status/done frames and skips heartbeats", async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(
        sseResponse([
          'event: status\ndata: {"status": "generating", "status_stage": "drafting"}\n\n',
          ": keep-alive\n\n",
          "event: done\ndata: {}\n\n",
        ])
      );

    const events = [];
    await openEventStream("/proposals/abc/events/", {
      onEvent: (e) => events.push(e),
    });

    expect(events).toEqual([
      { event: "status", data: { status: "generating", status_stage: "drafting" } },
      { event: "done", data: {} },
    ]);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/proposals/abc/events/"),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      })
    );
  });

  it("handles frames split across network chunks", async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(
        sseResponse(['event: status\ndata: {"sta', 'tus": "draft"}\n\nevent: done\ndata: {}\n\n'])
      );

    const events = [];
    await openEventStream("/x/", { onEvent: (e) => events.push(e) });

    expect(events).toEqual([
      { event: "status", data: { status: "draft" } },
      { event: "done", data: {} },
    ]);
  });

  it("rejects on non-OK responses", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404, body: null });
    await expect(openEventStream("/x/", { onEvent: () => {} })).rejects.toThrow("404");
  });
});

describe("watchProposal", () => {
  it("relays status events and fetches the full proposal on done", async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(
        sseResponse([
          'event: status\ndata: {"status": "generating", "status_stage": "retrieving"}\n\n',
          "event: done\ndata: {}\n\n",
        ])
      );
    const full = { id: "abc", status: "draft", sections: { executive_summary: "Hi" } };
    const getSpy = vi.spyOn(api, "get").mockResolvedValue({ data: full });

    const statuses = [];
    const done = await new Promise((resolve, reject) => {
      watchProposal("abc", {
        onStatus: (s) => statuses.push(s),
        onDone: resolve,
        onError: reject,
      });
    });

    expect(statuses[0].status_stage).toBe("retrieving");
    expect(done).toEqual(full);
    expect(getSpy).toHaveBeenCalledWith("/proposals/abc/");
  });

  it("falls back to polling when the stream cannot be established", async () => {
    vi.useFakeTimers();
    global.fetch = vi.fn().mockRejectedValue(new Error("network down"));
    const full = { id: "abc", status: "draft", sections: {} };
    const getSpy = vi.spyOn(api, "get").mockResolvedValue({ data: full });

    const onDone = vi.fn();
    watchProposal("abc", { onStatus: () => {}, onDone, onError: () => {} });

    // Let the SSE attempts fail (3 attempts, all rejecting synchronously).
    await vi.advanceTimersByTimeAsync(10);
    // First poll tick.
    await vi.advanceTimersByTimeAsync(3000);

    expect(getSpy).toHaveBeenCalledWith("/proposals/abc/");
    expect(onDone).toHaveBeenCalledWith(full);
    vi.useRealTimers();
  });
});
