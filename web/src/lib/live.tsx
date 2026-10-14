"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { mutate } from "swr";
import { WS_URL } from "./api";
import type { CameraStatus, RollEvent } from "./types";

type Listener = (ev: RollEvent) => void;

interface LiveState {
  connected: boolean;
  generation: number;
  camera: CameraStatus | null;
  latest: RollEvent[];
  subscribe: (fn: Listener) => () => void;
}

const LiveContext = createContext<LiveState | null>(null);

const KEYS_BY_KIND: Record<string, (key: string) => boolean> = {
  attendance: (k) => k.startsWith("/sessions") || k.startsWith("/stats") || k.startsWith("/events"),
  alert: (k) => k.startsWith("/alerts") || k.startsWith("/stats") || k.startsWith("/events"),
  system: (k) => k.startsWith("/sessions") || k.startsWith("/stats") || k.startsWith("/events") || k.startsWith("/students"),
};

export function LiveProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [generation, setGeneration] = useState(0);
  const [camera, setCamera] = useState<CameraStatus | null>(null);
  const [latest, setLatest] = useState<RollEvent[]>([]);
  const listeners = useRef(new Set<Listener>());

  const subscribe = useCallback((fn: Listener) => {
    listeners.current.add(fn);
    return () => {
      listeners.current.delete(fn);
    };
  }, []);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    const connect = () => {
      socket = new WebSocket(WS_URL);
      socket.onopen = () => {
        setConnected(true);
        setGeneration((g) => g + 1);
        mutate(() => true);
      };
      socket.onmessage = (msg) => {
        const { channel, data } = JSON.parse(msg.data);
        if (channel === "live") {
          setCamera(data as CameraStatus);
        } else if (channel === "event") {
          const ev = data as RollEvent;
          setLatest((prev) => [ev, ...prev].slice(0, 60));
          listeners.current.forEach((fn) => fn(ev));
          const match = KEYS_BY_KIND[ev.kind];
          if (match) mutate((key) => typeof key === "string" && match(key));
        }
      };
      socket.onclose = () => {
        setConnected(false);
        setCamera(null);
        if (!closed) timer = setTimeout(connect, 2000);
      };
      socket.onerror = () => socket?.close();
    };
    connect();
    return () => {
      closed = true;
      if (timer) clearTimeout(timer);
      socket?.close();
    };
  }, []);

  return <LiveContext.Provider value={{ connected, generation, camera, latest, subscribe }}>{children}</LiveContext.Provider>;
}

export function useLive(): LiveState {
  const ctx = useContext(LiveContext);
  if (!ctx) throw new Error("useLive outside LiveProvider");
  return ctx;
}
