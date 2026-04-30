"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Device } from "@/lib/types";

const GROUPS: Array<{ title: string; keys: (keyof Device)[] }> = [
  {
    title: "Identity",
    keys: ["id", "name", "category", "supportedProtocol", "deviceState", "controlledProperty"],
  },
  {
    title: "Hardware",
    keys: [
      "manufacturerName",
      "modelName",
      "firmwareVersion",
      "serialNumber",
      "serialNumberType",
      "ipAddress",
      "owner",
      "dateInstalled",
    ],
  },
  {
    title: "MQTT",
    keys: ["mqttTopicRoot", "mqttClientId", "mqttQos", "dataTypes", "mqttSecurity"],
  },
  {
    title: "PLC",
    keys: [
      "plcIpAddress",
      "plcPort",
      "plcConnectionMethod",
      "plcCredentials",
      "plcReadFrequency",
      "plcTagsMapping",
    ],
  },
  {
    title: "LoRaWAN",
    keys: [
      "loraAppEui",
      "loraDevEui",
      "loraAppKey",
      "loraNetworkServer",
      "loraPayloadDecoder",
    ],
  },
  { title: "Location", keys: ["location", "address"] },
];

export function OverviewTab({ device }: { device: Device }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {GROUPS.map((group) => {
        const rows = group.keys
          .map((k) => [k as string, device[k]] as const)
          .filter(([, v]) => v !== undefined && v !== null);
        if (rows.length === 0) return null;
        return (
          <Card key={group.title}>
            <CardHeader>
              <CardTitle className="text-base">{group.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2 text-sm">
                {rows.map(([k, v]) => (
                  <Row key={k} k={k} v={v} />
                ))}
              </dl>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function Row({ k, v }: { k: string; v: unknown }) {
  return (
    <>
      <dt className="font-medium text-muted-foreground">{k}</dt>
      <dd className="break-all">{render(v)}</dd>
    </>
  );
}

function render(v: unknown): string {
  if (v === undefined || v === null) return "—";
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}
