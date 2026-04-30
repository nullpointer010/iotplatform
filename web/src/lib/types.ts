// Mirror of platform/api/app/schemas*.py — keep in sync by hand.

export type Category =
  | "sensor"
  | "actuator"
  | "gateway"
  | "plc"
  | "iotStation"
  | "endgun"
  | "weatherStation"
  | "other";

export type Protocol =
  | "mqtt"
  | "coap"
  | "http"
  | "modbus"
  | "bacnet"
  | "lorawan"
  | "plc"
  | "other";

export type DeviceState = "active" | "inactive" | "maintenance";

export interface Device {
  id: string;
  type: "Device";
  name?: string;
  category?: Category;
  controlledProperty?: string[];
  serialNumber?: string;
  serialNumberType?: string;
  supportedProtocol?: Protocol;
  location?: { latitude: number; longitude: number; site_area?: string | null };
  address?: Record<string, unknown>;
  manufacturerName?: string;
  modelName?: string;
  dateInstalled?: string;
  owner?: string[];
  firmwareVersion?: string;
  ipAddress?: string[];
  deviceState?: DeviceState;
  // MQTT
  mqttTopicRoot?: string;
  mqttClientId?: string;
  mqttQos?: number;
  dataTypes?: Record<string, unknown>;
  mqttSecurity?: Record<string, unknown>;
  // PLC
  plcIpAddress?: string;
  plcPort?: number;
  plcConnectionMethod?: string;
  plcCredentials?: Record<string, unknown>;
  plcReadFrequency?: number;
  plcTagsMapping?: Record<string, unknown>;
  // LoRaWAN
  loraAppEui?: string;
  loraDevEui?: string;
  loraAppKey?: string;
  loraNetworkServer?: string;
  loraPayloadDecoder?: string;
}

export type DeviceCreate = Omit<Device, "type"> & {
  name: string;
  category: Category;
  supportedProtocol: Protocol;
};

export type DeviceUpdate = Partial<Omit<Device, "id" | "type">>;

export interface TelemetryEntry {
  dateObserved: string;
  numValue: number;
  unitCode?: string | null;
}

export interface TelemetryResponse {
  deviceId: string;
  controlledProperty: string;
  entries: TelemetryEntry[];
}

export interface OperationType {
  id: string;
  name: string;
  description?: string | null;
  requires_component: boolean;
}

export interface OperationTypeCreate {
  name: string;
  description?: string | null;
  requires_component?: boolean;
}

export interface MaintenanceLog {
  id: string;
  device_id: string;
  operation_type_id: string;
  performed_by_id?: string | null;
  start_time: string;
  end_time?: string | null;
  component_path?: string | null;
  details_notes?: string | null;
  created_at: string;
}

export interface MaintenanceLogCreate {
  operation_type_id: string;
  performed_by_id?: string | null;
  start_time: string;
  end_time?: string | null;
  component_path?: string | null;
  details_notes?: string | null;
}

export interface DeviceManual {
  id: string;
  device_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_at: string;
  uploaded_by: string | null;
}

export interface SiteSummary {
  site_area: string;
  device_count: number;
  has_floorplan: boolean;
}

export interface Floorplan {
  site_area: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_at: string;
  uploaded_by: string | null;
}

export interface Placement {
  device_id: string;
  name: string | null;
  x_pct: number | null;
  y_pct: number | null;
}
