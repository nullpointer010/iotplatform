"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import {
  CATEGORY,
  PROTOCOL,
  STATE,
  deviceFormSchema,
  type DeviceFormValues,
} from "@/lib/zod";
import { toast } from "@/components/ui/use-toast";
import type { Device, DeviceCreate, DeviceUpdate, Protocol } from "@/lib/types";

type Mode =
  | { mode: "create" }
  | { mode: "edit"; device: Device };

export function DeviceForm(props: Mode) {
  const router = useRouter();
  const initial: Partial<DeviceFormValues> =
    props.mode === "edit"
      ? {
          name: props.device.name,
          category: props.device.category,
          supportedProtocol: props.device.supportedProtocol,
          serialNumber: props.device.serialNumber,
          serialNumberType: props.device.serialNumberType,
          manufacturerName: props.device.manufacturerName,
          modelName: props.device.modelName,
          firmwareVersion: props.device.firmwareVersion,
          deviceState: props.device.deviceState,
          controlledProperty: props.device.controlledProperty?.join(", "),
          mqttTopicRoot: props.device.mqttTopicRoot,
          mqttClientId: props.device.mqttClientId,
          mqttQos: props.device.mqttQos,
          plcIpAddress: props.device.plcIpAddress,
          plcPort: props.device.plcPort,
          plcConnectionMethod: props.device.plcConnectionMethod,
          plcReadFrequency: props.device.plcReadFrequency,
          plcTagsMapping: props.device.plcTagsMapping
            ? JSON.stringify(props.device.plcTagsMapping)
            : undefined,
          loraAppEui: props.device.loraAppEui,
          loraDevEui: props.device.loraDevEui,
          loraAppKey: props.device.loraAppKey,
          loraNetworkServer: props.device.loraNetworkServer,
          loraPayloadDecoder: props.device.loraPayloadDecoder,
        }
      : { category: "sensor", supportedProtocol: "http" };

  const form = useForm<DeviceFormValues>({
    resolver: zodResolver(deviceFormSchema),
    defaultValues: initial as DeviceFormValues,
  });

  const protocol = form.watch("supportedProtocol");

  const mutation = useMutation({
    mutationFn: async (values: DeviceFormValues) => {
      const body = toApiPayload(values);
      if (props.mode === "create") {
        return api.createDevice(body as DeviceCreate);
      }
      return api.updateDevice(props.device.id, body as DeviceUpdate);
    },
    onSuccess: (device) => {
      toast({
        title: props.mode === "create" ? "Device created" : "Device updated",
      });
      router.push(`/devices/${encodeURIComponent(device.id)}`);
      router.refresh();
    },
    onError: (err: unknown) => {
      const message =
        err instanceof ApiError ? err.message : (err as Error).message;
      toast({ title: "Save failed", description: message, variant: "destructive" });
    },
  });

  return (
    <form
      className="space-y-6"
      onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
    >
      <Section title="Identity">
        <Field label="Name *" error={form.formState.errors.name?.message}>
          <Input {...form.register("name")} />
        </Field>
        <Field label="Category *">
          <Select
            value={form.watch("category")}
            onValueChange={(v) => form.setValue("category", v as DeviceFormValues["category"])}
          >
            <SelectTrigger>
              <SelectValue placeholder="Pick a category" />
            </SelectTrigger>
            <SelectContent>
              {CATEGORY.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Supported protocol *">
          <Select
            value={form.watch("supportedProtocol")}
            onValueChange={(v) =>
              form.setValue("supportedProtocol", v as Protocol)
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Pick a protocol" />
            </SelectTrigger>
            <SelectContent>
              {PROTOCOL.map((p) => (
                <SelectItem key={p} value={p}>
                  {p}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Device state">
          <Select
            value={form.watch("deviceState") ?? ""}
            onValueChange={(v) =>
              form.setValue("deviceState", (v || undefined) as DeviceFormValues["deviceState"])
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Optional" />
            </SelectTrigger>
            <SelectContent>
              {STATE.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Controlled properties (comma-separated)">
          <Input
            placeholder="temperature, humidity"
            {...form.register("controlledProperty")}
          />
        </Field>
      </Section>

      <Section title="Hardware">
        <Field label="Serial number">
          <Input {...form.register("serialNumber")} />
        </Field>
        <Field label="Serial number type">
          <Input placeholder="MAC, IMEI…" {...form.register("serialNumberType")} />
        </Field>
        <Field label="Manufacturer">
          <Input {...form.register("manufacturerName")} />
        </Field>
        <Field label="Model">
          <Input {...form.register("modelName")} />
        </Field>
        <Field label="Firmware version">
          <Input {...form.register("firmwareVersion")} />
        </Field>
      </Section>

      {protocol === "mqtt" && (
        <Section title="MQTT">
          <Field label="mqttTopicRoot *" error={form.formState.errors.mqttTopicRoot?.message}>
            <Input
              placeholder="installation/areaA/temp/sensor1"
              {...form.register("mqttTopicRoot")}
            />
          </Field>
          <Field label="mqttClientId *" error={form.formState.errors.mqttClientId?.message}>
            <Input {...form.register("mqttClientId")} />
          </Field>
          <Field label="mqttQos (0–2)" error={form.formState.errors.mqttQos?.message}>
            <Input type="number" min={0} max={2} {...form.register("mqttQos")} />
          </Field>
        </Section>
      )}

      {protocol === "plc" && (
        <Section title="PLC">
          <Field label="plcIpAddress *" error={form.formState.errors.plcIpAddress?.message}>
            <Input placeholder="192.168.1.100" {...form.register("plcIpAddress")} />
          </Field>
          <Field label="plcPort *" error={form.formState.errors.plcPort?.message}>
            <Input type="number" min={1} max={65535} {...form.register("plcPort")} />
          </Field>
          <Field label="plcConnectionMethod *">
            <Input placeholder="Modbus TCP" {...form.register("plcConnectionMethod")} />
          </Field>
          <Field label="plcReadFrequency (seconds)">
            <Input type="number" min={1} {...form.register("plcReadFrequency")} />
          </Field>
          <Field
            label="plcTagsMapping (JSON) *"
            error={form.formState.errors.plcTagsMapping?.message}
          >
            <Textarea
              placeholder='{"DB1.DW10":"Temperatura"}'
              {...form.register("plcTagsMapping")}
            />
          </Field>
        </Section>
      )}

      {protocol === "lorawan" && (
        <Section title="LoRaWAN">
          <Field label="loraAppEui * (16 hex)" error={form.formState.errors.loraAppEui?.message}>
            <Input {...form.register("loraAppEui")} />
          </Field>
          <Field label="loraDevEui * (16 hex)" error={form.formState.errors.loraDevEui?.message}>
            <Input {...form.register("loraDevEui")} />
          </Field>
          <Field label="loraAppKey * (32 hex)" error={form.formState.errors.loraAppKey?.message}>
            <Input {...form.register("loraAppKey")} />
          </Field>
          <Field label="loraNetworkServer *">
            <Input {...form.register("loraNetworkServer")} />
          </Field>
          <Field label="loraPayloadDecoder *">
            <Input {...form.register("loraPayloadDecoder")} />
          </Field>
        </Section>
      )}

      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => router.back()}
        >
          Cancel
        </Button>
        <Button type="submit" loading={mutation.isPending}>
          {props.mode === "create" ? "Create device" : "Save changes"}
        </Button>
      </div>
    </form>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4 rounded-lg border bg-card p-6 shadow-sm">
      <h2 className="text-base font-semibold">{title}</h2>
      <div className="grid gap-4 md:grid-cols-2">{children}</div>
    </section>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

function toApiPayload(values: DeviceFormValues): DeviceCreate | DeviceUpdate {
  const out: Record<string, unknown> = {};
  const set = (k: string, v: unknown) => {
    if (v !== undefined && v !== "" && v !== null) out[k] = v;
  };
  set("name", values.name);
  set("category", values.category);
  set("supportedProtocol", values.supportedProtocol);
  set("serialNumber", values.serialNumber);
  set("serialNumberType", values.serialNumberType);
  set("manufacturerName", values.manufacturerName);
  set("modelName", values.modelName);
  set("firmwareVersion", values.firmwareVersion);
  set("deviceState", values.deviceState);
  if (values.controlledProperty) {
    set(
      "controlledProperty",
      values.controlledProperty
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    );
  }
  if (values.supportedProtocol === "mqtt") {
    set("mqttTopicRoot", values.mqttTopicRoot);
    set("mqttClientId", values.mqttClientId);
    set("mqttQos", values.mqttQos);
  }
  if (values.supportedProtocol === "plc") {
    set("plcIpAddress", values.plcIpAddress);
    set("plcPort", values.plcPort);
    set("plcConnectionMethod", values.plcConnectionMethod);
    set("plcReadFrequency", values.plcReadFrequency);
    if (values.plcTagsMapping) {
      try {
        out.plcTagsMapping = JSON.parse(values.plcTagsMapping);
      } catch {
        // let server reject
        out.plcTagsMapping = values.plcTagsMapping;
      }
    }
  }
  if (values.supportedProtocol === "lorawan") {
    set("loraAppEui", values.loraAppEui);
    set("loraDevEui", values.loraDevEui);
    set("loraAppKey", values.loraAppKey);
    set("loraNetworkServer", values.loraNetworkServer);
    set("loraPayloadDecoder", values.loraPayloadDecoder);
  }
  return out as DeviceCreate | DeviceUpdate;
}
