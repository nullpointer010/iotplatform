import type {
  Device,
  DeviceCreate,
  DeviceUpdate,
  MaintenanceLog,
  MaintenanceLogCreate,
  OperationType,
  OperationTypeCreate,
  TelemetryResponse,
} from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const PREFIX = "/api/v1";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { json?: unknown },
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.json !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${BASE}${PREFIX}${path}`, {
    ...init,
    headers,
    body: init?.json !== undefined ? JSON.stringify(init.json) : init?.body,
  });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? safeJson(text) : undefined;
  if (!res.ok) {
    const message =
      (data && typeof data === "object" && "detail" in data
        ? formatDetail((data as { detail: unknown }).detail)
        : res.statusText) || `HTTP ${res.status}`;
    throw new ApiError(res.status, data, message);
  }
  return data as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        if (d && typeof d === "object" && "msg" in d) {
          const loc = "loc" in d && Array.isArray(d.loc) ? d.loc.join(".") : "";
          return loc ? `${loc}: ${d.msg}` : String(d.msg);
        }
        return JSON.stringify(d);
      })
      .join("; ");
  }
  return JSON.stringify(detail);
}

// ----- devices -----
export const api = {
  listDevices: (limit = 100, offset = 0) =>
    request<Device[]>(`/devices?limit=${limit}&offset=${offset}`),
  getDevice: (id: string) => request<Device>(`/devices/${encodeURIComponent(id)}`),
  createDevice: (body: DeviceCreate) =>
    request<Device>(`/devices`, { method: "POST", json: body }),
  updateDevice: (id: string, body: DeviceUpdate) =>
    request<Device>(`/devices/${encodeURIComponent(id)}`, {
      method: "PATCH",
      json: body,
    }),
  deleteDevice: (id: string) =>
    request<void>(`/devices/${encodeURIComponent(id)}`, { method: "DELETE" }),

  getTelemetry: (
    id: string,
    params: {
      controlledProperty: string;
      fromDate?: string;
      toDate?: string;
      lastN?: number;
      limit?: number;
    },
  ) => {
    const q = new URLSearchParams({
      controlledProperty: params.controlledProperty,
    });
    if (params.fromDate) q.set("fromDate", params.fromDate);
    if (params.toDate) q.set("toDate", params.toDate);
    if (params.lastN) q.set("lastN", String(params.lastN));
    if (params.limit) q.set("limit", String(params.limit));
    return request<TelemetryResponse>(
      `/devices/${encodeURIComponent(id)}/telemetry?${q.toString()}`,
    );
  },

  // ----- operation types -----
  listOperationTypes: () =>
    request<OperationType[]>(`/maintenance/operation-types`),
  createOperationType: (body: OperationTypeCreate) =>
    request<OperationType>(`/maintenance/operation-types`, {
      method: "POST",
      json: body,
    }),
  updateOperationType: (id: string, body: Partial<OperationTypeCreate>) =>
    request<OperationType>(
      `/maintenance/operation-types/${encodeURIComponent(id)}`,
      { method: "PATCH", json: body },
    ),
  deleteOperationType: (id: string) =>
    request<void>(
      `/maintenance/operation-types/${encodeURIComponent(id)}`,
      { method: "DELETE" },
    ),

  // ----- maintenance log -----
  listMaintenanceLog: (
    deviceId: string,
    params: { from_date?: string; to_date?: string; page?: number; page_size?: number } = {},
  ) => {
    const q = new URLSearchParams();
    if (params.from_date) q.set("from_date", params.from_date);
    if (params.to_date) q.set("to_date", params.to_date);
    if (params.page) q.set("page", String(params.page));
    if (params.page_size) q.set("page_size", String(params.page_size));
    const qs = q.toString();
    return request<MaintenanceLog[]>(
      `/devices/${encodeURIComponent(deviceId)}/maintenance/log${qs ? "?" + qs : ""}`,
    );
  },
  createMaintenanceLog: (deviceId: string, body: MaintenanceLogCreate) =>
    request<MaintenanceLog>(
      `/devices/${encodeURIComponent(deviceId)}/maintenance/log`,
      { method: "POST", json: body },
    ),
  deleteMaintenanceLog: (logId: string) =>
    request<void>(`/maintenance/log/${encodeURIComponent(logId)}`, {
      method: "DELETE",
    }),
};
