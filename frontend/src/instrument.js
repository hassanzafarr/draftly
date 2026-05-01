import * as Sentry from "@sentry/react";

const dsn = import.meta.env.VITE_SENTRY_DSN;

if (dsn) {
  const apiUrl = import.meta.env.VITE_API_URL;
  const traceTargets = [/^\//];

  if (apiUrl) {
    try {
      traceTargets.push(new URL(apiUrl).origin);
    } catch {
      // Ignore invalid local config; Sentry can still capture app errors.
    }
  }

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? 0),
    tracePropagationTargets: traceTargets,
    replaysSessionSampleRate: Number(
      import.meta.env.VITE_SENTRY_REPLAYS_SESSION_SAMPLE_RATE ?? 0
    ),
    replaysOnErrorSampleRate: Number(
      import.meta.env.VITE_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE ?? 1
    ),
  });
}
