"use client";

import dynamic from "next/dynamic";
import type { DeviceMapProps } from "./device-map";

// Leaflet touches `window` at import time, so this component must be
// loaded only on the client. All other call sites import this wrapper.
export const DeviceMap = dynamic(() => import("./device-map"), {
  ssr: false,
  loading: () => (
    <div className="w-full animate-pulse rounded-lg border bg-muted" style={{ height: 280 }} />
  ),
});

export type { DeviceMapProps };
