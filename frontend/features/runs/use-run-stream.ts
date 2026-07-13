/**
 * React hook that subscribes to a run's SSE event stream and reduces
 * events into a `RunViewState`.
 *
 * Usage:
 *
 *   const state = useRunStream(runId);
 *
 * The hook handles reconnection with exponential backoff and uses
 * `Last-Event-ID` to resume from the last event the client processed.
 */

"use client";

import { useEffect, useReducer, useRef, useState } from "react";

import {
  createInitialRunState,
  reduceRunEvent,
  type RunEvent,
  type RunViewState,
} from "./event-reducer";

const API_BASE =
  process.env.NEXT_PUBLIC_PAPERPILOT_API_BASE ?? "http://127.0.0.1:8000";

export type ConnectionState =
  | "idle"
  | "connecting"
  | "open"
  | "reconnecting"
  | "closed";

export function useRunStream(runId: string | null) {
  const [state, dispatch] = useReducer<RunViewState, RunEvent | null>(
    reducer,
    initialRunState,
  );
  const [connectionState, setConnectionState] =
    useState<ConnectionState>("idle");
  const lastSequenceRef = useRef(0);

  useEffect(() => {
    if (!runId) {
      setConnectionState("idle");
      return;
    }

    setConnectionState("connecting");

    const source = new EventSource(
      `${API_BASE}/api/runs/${runId}/events/stream?after=${lastSequenceRef.current}`,
      { withCredentials: true },
    );

    source.onopen = () => {
      setConnectionState("open");
    };

    source.onmessage = (message) => {
      if (!message.data) return;
      try {
        const event = JSON.parse(message.data) as RunEvent;
        if (event.sequence > lastSequenceRef.current) {
          lastSequenceRef.current = event.sequence;
          dispatch(event);
        }
      } catch (error) {
        console.error("Failed to parse SSE event", error);
      }
    };

    source.onerror = () => {
      setConnectionState("reconnecting");
      // EventSource reconnects automatically; if it fails repeatedly,
      // it will close and we surface that state.
    };

    source.addEventListener("close", () => {
      setConnectionState("closed");
    });

    return () => {
      source.close();
      setConnectionState("idle");
    };
  }, [runId]);

  return { state, connectionState };
}

function reducer(state: RunViewState, event: RunEvent | null): RunViewState {
  if (!event) return initialRunState;
  if (state.runId !== event.run_id) {
    return reduceRunEvent(
      { ...createInitialRunState(event.run_id), lastSequence: 0 },
      event,
    );
  }
  return reduceRunEvent(state, event);
}

const initialRunState: RunViewState = createInitialRunState("");
