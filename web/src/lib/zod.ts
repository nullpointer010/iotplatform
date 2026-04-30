import { z } from "zod";

const CATEGORY = [
  "sensor",
  "actuator",
  "gateway",
  "plc",
  "iotStation",
  "endgun",
  "weatherStation",
  "other",
] as const;

const PROTOCOL = [
  "mqtt",
  "coap",
  "http",
  "modbus",
  "bacnet",
  "lorawan",
  "plc",
  "other",
] as const;

const STATE = ["active", "inactive", "maintenance"] as const;

const optionalNonEmpty = (s: z.ZodString) =>
  z.preprocess((v) => (v === "" || v === undefined ? undefined : v), s.optional());

const numericOptional = (s: z.ZodNumber) =>
  z.preprocess(
    (v) => (v === "" || v === undefined || v === null ? undefined : Number(v)),
    s.optional(),
  );

export const deviceFormSchema = z
  .object({
    name: z.string().min(1, "Name is required"),
    category: z.enum(CATEGORY),
    supportedProtocol: z.enum(PROTOCOL),
    serialNumber: optionalNonEmpty(z.string()),
    serialNumberType: optionalNonEmpty(z.string()),
    manufacturerName: optionalNonEmpty(z.string()),
    modelName: optionalNonEmpty(z.string()),
    firmwareVersion: optionalNonEmpty(z.string()),
    deviceState: z.enum(STATE).optional().or(z.literal("").transform(() => undefined)),
    controlledProperty: optionalNonEmpty(z.string()),
    // Location
    latitude: numericOptional(z.number().min(-90).max(90)),
    longitude: numericOptional(z.number().min(-180).max(180)),
    siteArea: optionalNonEmpty(z.string()),
    // Administrative
    dateInstalled: optionalNonEmpty(z.string()),
    ownerCsv: optionalNonEmpty(z.string()),
    ipAddressCsv: optionalNonEmpty(z.string()),
    addressJson: optionalNonEmpty(z.string()),
    // MQTT
    mqttTopicRoot: optionalNonEmpty(z.string()),
    mqttClientId: optionalNonEmpty(z.string()),
    mqttQos: numericOptional(z.number().int().min(0).max(2)),
    dataTypesJson: optionalNonEmpty(z.string()),
    mqttSecurityJson: optionalNonEmpty(z.string()),
    // PLC
    plcIpAddress: optionalNonEmpty(z.string()),
    plcPort: numericOptional(z.number().int().min(1).max(65535)),
    plcConnectionMethod: optionalNonEmpty(z.string()),
    plcReadFrequency: numericOptional(z.number().int().min(1)),
    plcTagsMapping: optionalNonEmpty(z.string()),
    plcCredentialsJson: optionalNonEmpty(z.string()),
    // LoRaWAN
    loraAppEui: optionalNonEmpty(z.string()),
    loraDevEui: optionalNonEmpty(z.string()),
    loraAppKey: optionalNonEmpty(z.string()),
    loraNetworkServer: optionalNonEmpty(z.string()),
    loraPayloadDecoder: optionalNonEmpty(z.string()),
  })
  .refine(
    (v) =>
      (v.latitude === undefined && v.longitude === undefined) ||
      (v.latitude !== undefined && v.longitude !== undefined),
    {
      message: "Latitude and longitude must be set together",
      path: ["longitude"],
    },
  );

export type DeviceFormValues = z.infer<typeof deviceFormSchema>;

export const operationTypeFormSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().optional().or(z.literal("").transform(() => undefined)),
  requires_component: z.boolean().default(false),
});

export type OperationTypeFormValues = z.infer<typeof operationTypeFormSchema>;

export const maintenanceLogFormSchema = z
  .object({
    operation_type_id: z.string().uuid({ message: "Pick an operation type" }),
    performed_by_id: z
      .string()
      .uuid()
      .optional()
      .or(z.literal("").transform(() => undefined)),
    start_time: z.string().min(1, "Start time is required"),
    end_time: z.string().optional().or(z.literal("").transform(() => undefined)),
    component_path: z.string().optional().or(z.literal("").transform(() => undefined)),
    details_notes: z.string().optional().or(z.literal("").transform(() => undefined)),
  })
  .refine(
    (v) => !v.end_time || new Date(v.end_time) >= new Date(v.start_time),
    { message: "end_time must be >= start_time", path: ["end_time"] },
  );

export type MaintenanceLogFormValues = z.infer<typeof maintenanceLogFormSchema>;

export { CATEGORY, PROTOCOL, STATE };
