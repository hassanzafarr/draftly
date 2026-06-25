// Server-Sent Events client for generation/ingestion status.
//
// Native EventSource cannot send the Authorization header, so streams are read
// with fetch + ReadableStream. Each watcher tries SSE first and silently falls
// back to the old interval polling if the stream cannot be established (proxy
// strips streaming, fetch unsupported, repeated network failures), so SSE is a
// pure enhancement — behavior degrades to exactly what shipped before.
import api, { baseURL } from "./client";

const MAX_SSE_ATTEMPTS = 3;

// Parse one SSE frame (lines between blank-line separators).
function parseFrame(frame) {
  let event = "message";
  const dataLines = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith(":")) continue; // heartbeat comment
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return null;
  try {
    return { event, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    return null;
  }
}

// Open one SSE connection and invoke onEvent per frame. Resolves when the
// server closes the stream; rejects on network/HTTP errors.
export async function openEventStream(path, { onEvent, signal }) {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${baseURL}${path}`, {
    headers: {
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`SSE request failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const parsed = parseFrame(buffer.slice(0, sep));
      buffer = buffer.slice(sep + 2);
      if (parsed) onEvent(parsed);
    }
  }
}

// Generic watcher: SSE with reconnect-on-timeout, falling back to polling.
//
//   eventsPath   SSE endpoint (relative to /api)
//   onStatus     called with each `status` event payload
//   fetchFinal   called once the stream reports done/gone (and for each poll
//                tick in fallback mode); must return the polled resource
//   isDone       given fetchFinal's result, is the work finished?
//   onDone       called once with the final fetchFinal result
//   onError      called when even polling fails
//   pollMs       fallback polling interval
//
// Returns a cancel function.
function watchStream({ eventsPath, onStatus, fetchFinal, isDone, onDone, onError, pollMs }) {
  const controller = new AbortController();
  let cancelled = false;
  let pollTimer = null;

  const stop = () => {
    cancelled = true;
    controller.abort();
    if (pollTimer) clearInterval(pollTimer);
  };

  const finish = async () => {
    try {
      const data = await fetchFinal();
      if (!cancelled) onDone(data);
    } catch (err) {
      if (!cancelled) onError?.(err);
    }
  };

  const startPolling = () => {
    pollTimer = setInterval(async () => {
      try {
        const data = await fetchFinal();
        if (cancelled) return;
        if (isDone(data)) {
          clearInterval(pollTimer);
          onDone(data);
        } else {
          onStatus?.(data);
        }
      } catch (err) {
        if (cancelled) return;
        clearInterval(pollTimer);
        onError?.(err);
      }
    }, pollMs);
  };

  (async () => {
    let failures = 0;
    while (!cancelled) {
      let outcome = "timeout";
      const startedAt = Date.now();
      try {
        await openEventStream(eventsPath, {
          signal: controller.signal,
          onEvent: ({ event, data }) => {
            if (event === "status") onStatus?.(data);
            else if (event === "done" || event === "gone") outcome = "done";
            else if (event === "timeout") outcome = "timeout";
          },
        });
        // A stream that dies instantly without finishing is a broken transport
        // (buffering proxy, misbehaving middleware) — treat like a failure so
        // we don't hot-loop reconnects and eventually fall back to polling.
        if (outcome !== "done" && Date.now() - startedAt < 1000) {
          throw new Error("SSE stream closed immediately");
        }
        failures = 0;
      } catch {
        if (cancelled) return;
        failures += 1;
        if (failures >= MAX_SSE_ATTEMPTS) {
          startPolling();
          return;
        }
        continue;
      }
      if (cancelled) return;
      if (outcome === "done") {
        await finish();
        return;
      }
      // timeout — server capped the stream while work is in flight; reconnect.
    }
  })();

  return stop;
}

// Watch one proposal until it leaves "generating".
// onStatus receives {status, status_stage, stage_meta, error_message} partials
// (or the full proposal in polling fallback); onDone receives the full proposal.
export function watchProposal(id, { onStatus, onDone, onError }) {
  return watchStream({
    eventsPath: `/proposals/${id}/events/`,
    onStatus,
    fetchFinal: async () => (await api.get(`/proposals/${id}/`)).data,
    isDone: (proposal) => proposal.status !== "generating",
    onDone,
    onError,
    pollMs: 3000,
  });
}

// Watch the org's documents until none are pending/processing.
// onStatus receives [{id, status, chunk_count, error_message}] partial rows
// (or full document objects in polling fallback); onDone receives the full list.
export function watchDocuments({ onStatus, onDone, onError }) {
  return watchStream({
    eventsPath: `/documents/events/`,
    onStatus: (data) => onStatus?.(data.documents ?? data),
    fetchFinal: async () => {
      const { data } = await api.get("/documents/");
      return data.results || data;
    },
    isDone: (docs) => !docs.some((d) => d.status === "pending" || d.status === "processing"),
    onDone,
    onError,
    pollMs: 5000,
  });
}
