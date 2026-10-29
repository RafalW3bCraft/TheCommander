import { useEffect, useRef } from "react";
import { ApiError } from "./api";

const FALLBACK_MS = 5_000;
const MIN_REFRESH_MS = 1_000;
const MAX_RECONNECT_MS = 30_000;

/** Run notifications invalidate ordinary typed detail reads; they never replace them. */
export function useRunEvents(
  runId: string | null,
  refresh: () => Promise<void>,
  onError: (error: Error) => void,
) {
  const callbacks = useRef({ refresh, onError });
  useEffect(() => {
    callbacks.current = { refresh, onError };
  }, [refresh, onError]);

  useEffect(() => {
    if (!runId) return;
    let disposed = false;
    let blocked = false;
    let terminal = false;
    let source: EventSource | null = null;
    let cursor = "0";
    let reconnectDelay = 1_000;
    let lastRefresh = 0;
    let pending: Promise<boolean> | null = null;
    let refreshTimer: number | undefined;
    let reconnectTimer: number | undefined;
    let fallbackTimer: number | undefined;
    let dirty = false;
    // Capture the callback for this run; never run the next selection's callback
    // from an in-flight completion belonging to this subscription.
    const readDetail = refresh;

    const closeSource = () => {
      source?.close();
      source = null;
    };
    const stop = () => {
      blocked = true;
      closeSource();
      window.clearTimeout(refreshTimer);
      window.clearTimeout(reconnectTimer);
      window.clearTimeout(fallbackTimer);
    };
    const report = (error: unknown) => {
      if (disposed || blocked) return;
      const failure =
        error instanceof Error ? error : new Error("Run updates unavailable");
      if (
        failure instanceof ApiError &&
        [401, 403, 404].includes(failure.status)
      )
        stop();
      callbacks.current.onError(failure);
    };

    const read = (): Promise<boolean> => {
      if (disposed || blocked) return Promise.resolve(false);
      if (pending) return pending;
      lastRefresh = Date.now();
      pending = readDetail()
        .then(() => !disposed && !blocked)
        .catch((error: unknown) => {
          report(error);
          return false;
        })
        .finally(() => {
          pending = null;
          if (dirty && !disposed && !blocked) {
            dirty = false;
            invalidate();
          }
        });
      return pending;
    };
    // Coalesce bursts, including events received while a detail read is held.
    const invalidate = () => {
      if (disposed || blocked) return;
      if (pending) {
        dirty = true;
        return;
      }
      if (refreshTimer !== undefined) return;
      refreshTimer = window.setTimeout(
        () => {
          refreshTimer = undefined;
          void read();
        },
        Math.max(0, MIN_REFRESH_MS - (Date.now() - lastRefresh)),
      );
    };
    const scheduleFallback = () => {
      if (disposed || blocked) return;
      fallbackTimer = window.setTimeout(() => {
        void read().finally(scheduleFallback);
      }, FALLBACK_MS);
    };
    const scheduleReconnect = () => {
      closeSource(); // Disable EventSource's implicit retry loop, including on 401.
      if (disposed || blocked || terminal || reconnectTimer !== undefined)
        return;
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = undefined;
        // EventSource does not expose HTTP errors. An authenticated status read
        // distinguishes expired access before another streaming request is made.
        void read().then((allowed) => {
          if (disposed || blocked || terminal) return;
          if (allowed) connect();
          else scheduleReconnect();
        });
      }, reconnectDelay);
      reconnectDelay = Math.min(MAX_RECONNECT_MS, reconnectDelay * 2);
    };
    const connect = () => {
      if (disposed || blocked || terminal || !window.EventSource) return;
      const connection = new EventSource(
        `/api/runs/${encodeURIComponent(runId)}/events?after=${encodeURIComponent(cursor)}`,
        { withCredentials: true },
      );
      source = connection;
      connection.onopen = () => {
        reconnectDelay = 1_000;
      };
      connection.addEventListener(
        "run_event",
        (event: MessageEvent<string>) => {
          if (disposed || blocked || connection !== source) return;
          // Preserve bigint IDs as strings; do not round through Number.
          if (/^\d{1,19}$/.test(event.lastEventId)) cursor = event.lastEventId;
          invalidate();
        },
      );
      connection.addEventListener("status", invalidate);
      connection.addEventListener("end", (event: MessageEvent<string>) => {
        if (disposed || blocked || connection !== source) return;
        try {
          const payload: unknown = JSON.parse(event.data);
          terminal =
            typeof payload === "object" &&
            payload !== null &&
            "reason" in payload &&
            payload.reason === "terminal";
        } catch {
          // A malformed notification still falls back to authoritative GET.
        }
        invalidate();
        if (terminal) closeSource();
        else scheduleReconnect();
      });
      connection.addEventListener("session_expired", () => {
        if (disposed || blocked || connection !== source) return;
        report(new ApiError("Sign in to continue", 401));
        window.dispatchEvent(new Event("commander-session-expired"));
      });
      connection.addEventListener("access_lost", () => {
        if (disposed || blocked || connection !== source) return;
        report(new ApiError("Run is no longer available", 404));
      });
      connection.onerror = () => {
        if (connection === source) scheduleReconnect();
      };
    };

    void read().then((allowed) => {
      if (disposed || blocked) return;
      if (allowed) connect();
      else scheduleReconnect();
      scheduleFallback();
    });
    return () => {
      disposed = true;
      stop();
    };
    // Refresh identity is deliberately captured per run, not per render.
    // Callers keep stale-result guards shared with their manual action reads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);
}
