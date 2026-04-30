"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FieldLabel } from "@/components/forms/field-label";
import { api } from "@/lib/api";
import {
  CATEGORY,
  PROTOCOL,
  STATE,
  deviceFormSchema,
  type DeviceFormValues,
} from "@/lib/zod";
import { useMutateWithToast } from "@/lib/mutate";
import type { Device, DeviceCreate, DeviceUpdate, Protocol } from "@/lib/types";
import { DeviceMap } from "@/components/map/device-map.client";

type Mode = { mode: "create" } | { mode: "edit"; device: Device };

export function DeviceForm(props: Mode) {
  const router = useRouter();
  const t = useTranslations();
  const initial: Partial<DeviceFormValues> =
    props.mode === "edit"
      ? toFormValues(props.device)
      : { category: "sensor", supportedProtocol: "http" };

  const form = useForm<DeviceFormValues>({
    resolver: zodResolver(deviceFormSchema),
    mode: "onBlur",
    defaultValues: initial as DeviceFormValues,
  });

  const protocol = form.watch("supportedProtocol");

  const errs = form.formState.errors;
  const ph = (key: string): string | undefined => safe(t, `device.placeholder.${key}`);
  const inv = (name: keyof DeviceFormValues | "ownerCsv" | "ipAddressCsv" | "addressJson" | "mqttSecurityJson" | "plcCredentialsJson") =>
    (errs as Record<string, unknown>)[name as string] ? { "aria-invalid": true as const } : {};

  const fmt = (msg?: string): string | undefined => {
    if (!msg) return undefined;
    if (msg.startsWith("orionForbidden:")) {
      return t("zod.orionForbidden", { char: msg.slice("orionForbidden:".length) });
    }
    return msg;
  };

  const mutation = useMutateWithToast<Device, DeviceFormValues>({
    mutationFn: async (values) => {
      const body = toApiPayload(values);
      if (props.mode === "create") {
        return api.createDevice(body as DeviceCreate);
      }
      return api.updateDevice(props.device.id, body as DeviceUpdate);
    },
    onSuccess: (device) => {
      router.push(`/devices/${encodeURIComponent(device.id)}`);
      router.refresh();
    },
  });

  // Helper to render label + tooltip from i18n keys.
  const f = (key: string, required = false) => ({
    label: t(`device.field.${key}.label`),
    tooltip: safe(t, `device.field.${key}.tooltip`),
    required,
  });

  return (
    <form
      className="space-y-6"
      onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
    >
      <Section title={t("device.section.identity.title")}>
        <FormRow {...f("name", true)} htmlFor="name" error={fmt(form.formState.errors.name?.message)}>
          <Input id="name" placeholder={ph("name")} {...inv("name")} {...form.register("name")} />
        </FormRow>
        <FormRow {...f("category", true)} htmlFor="category">
          <Select
            value={form.watch("category")}
            onValueChange={(v) => form.setValue("category", v as DeviceFormValues["category"])}
          >
            <SelectTrigger id="category"><SelectValue /></SelectTrigger>
            <SelectContent>
              {CATEGORY.map((c) => (
                <SelectItem key={c} value={c}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormRow>
        <FormRow {...f("supportedProtocol", true)} htmlFor="supportedProtocol">
          <Select
            value={form.watch("supportedProtocol")}
            onValueChange={(v) => form.setValue("supportedProtocol", v as Protocol)}
          >
            <SelectTrigger id="supportedProtocol"><SelectValue /></SelectTrigger>
            <SelectContent>
              {PROTOCOL.map((p) => (
                <SelectItem key={p} value={p}>{p}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormRow>
        <FormRow {...f("deviceState")} htmlFor="deviceState">
          <Select
            value={form.watch("deviceState") ?? ""}
            onValueChange={(v) =>
              form.setValue("deviceState", (v || undefined) as DeviceFormValues["deviceState"])
            }
          >
            <SelectTrigger id="deviceState"><SelectValue placeholder="—" /></SelectTrigger>
            <SelectContent>
              {STATE.map((s) => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormRow>
        <FormRow {...f("controlledProperty")} htmlFor="controlledProperty">
          <Input
            id="controlledProperty"
            placeholder={ph("controlledProperty")}
            {...form.register("controlledProperty")}
          />
        </FormRow>
      </Section>

      <Section title={t("device.section.hardware.title")}>
        <FormRow {...f("serialNumber")} htmlFor="serialNumber" error={fmt(form.formState.errors.serialNumber?.message)}>
          <Input id="serialNumber" placeholder={ph("serialNumber")} {...inv("serialNumber")} {...form.register("serialNumber")} />
        </FormRow>
        <FormRow {...f("serialNumberType")} htmlFor="serialNumberType">
          <Input id="serialNumberType" placeholder={ph("serialNumberType")} {...form.register("serialNumberType")} />
        </FormRow>
        <FormRow {...f("manufacturerName")} htmlFor="manufacturerName" error={fmt(form.formState.errors.manufacturerName?.message)}>
          <Input id="manufacturerName" placeholder={ph("manufacturerName")} {...inv("manufacturerName")} {...form.register("manufacturerName")} />
        </FormRow>
        <FormRow {...f("modelName")} htmlFor="modelName" error={fmt(form.formState.errors.modelName?.message)}>
          <Input id="modelName" placeholder={ph("modelName")} {...inv("modelName")} {...form.register("modelName")} />
        </FormRow>
        <FormRow {...f("firmwareVersion")} htmlFor="firmwareVersion" error={fmt(form.formState.errors.firmwareVersion?.message)}>
          <Input id="firmwareVersion" placeholder={ph("firmwareVersion")} {...inv("firmwareVersion")} {...form.register("firmwareVersion")} />
        </FormRow>
      </Section>

      <Section title={t("device.section.location.title")}>
        <FormRow {...f("latitude")} htmlFor="latitude" error={form.formState.errors.latitude?.message as string | undefined}>
          <Input id="latitude" type="number" step="any" placeholder={ph("latitude")} {...inv("latitude")} {...form.register("latitude")} />
        </FormRow>
        <FormRow {...f("longitude")} htmlFor="longitude" error={form.formState.errors.longitude?.message as string | undefined}>
          <Input id="longitude" type="number" step="any" placeholder={ph("longitude")} {...inv("longitude")} {...form.register("longitude")} />
        </FormRow>
        <FormRow {...f("siteArea")} htmlFor="siteArea" error={fmt(form.formState.errors.siteArea?.message)}>
          <Input id="siteArea" placeholder={ph("siteArea")} {...inv("siteArea")} {...form.register("siteArea")} />
        </FormRow>
        <LocationPicker form={form} hint={t("map.picker.hint")} />
      </Section>

      <Section title={t("device.section.admin.title")}>
        <FormRow {...f("dateInstalled")} htmlFor="dateInstalled">
          <Input id="dateInstalled" type="datetime-local" {...form.register("dateInstalled")} />
        </FormRow>
        <FormRow {...f("owner")} htmlFor="ownerCsv" error={fmt((form.formState.errors.ownerCsv as { message?: string } | undefined)?.message)}>
          <Input id="ownerCsv" placeholder={ph("ownerCsv")} {...inv("ownerCsv")} {...form.register("ownerCsv")} />
        </FormRow>
        <FormRow {...f("ipAddress")} htmlFor="ipAddressCsv">
          <Input id="ipAddressCsv" placeholder={ph("ipAddressCsv")} {...form.register("ipAddressCsv")} />
        </FormRow>
        <FormRow {...f("address")} htmlFor="addressJson" error={form.formState.errors.addressJson?.message}>
          <Textarea
            id="addressJson"
            placeholder={ph("addressJson")}
            {...inv("addressJson")}
            {...form.register("addressJson")}
          />
        </FormRow>
      </Section>

      {protocol === "mqtt" && (
        <Section title={t("device.section.mqtt.title")}>
          <FormRow {...f("mqttTopicRoot", true)} htmlFor="mqttTopicRoot" error={form.formState.errors.mqttTopicRoot?.message}>
            <Input id="mqttTopicRoot" placeholder={ph("mqttTopicRoot")} {...inv("mqttTopicRoot")} {...form.register("mqttTopicRoot")} />
          </FormRow>
          <FormRow {...f("mqttClientId", true)} htmlFor="mqttClientId" error={fmt(form.formState.errors.mqttClientId?.message)}>
            <Input id="mqttClientId" placeholder={ph("mqttClientId")} {...inv("mqttClientId")} {...form.register("mqttClientId")} />
          </FormRow>
          <FormRow {...f("mqttQos")} htmlFor="mqttQos" error={form.formState.errors.mqttQos?.message}>
            <Input id="mqttQos" type="number" min={0} max={2} {...inv("mqttQos")} {...form.register("mqttQos")} />
          </FormRow>
          <FormRow {...f("mqttSecurity")} htmlFor="mqttSecurityJson">
            <Textarea id="mqttSecurityJson" placeholder={ph("mqttSecurityJson")} {...form.register("mqttSecurityJson")} />
          </FormRow>
        </Section>
      )}

      {protocol === "plc" && (
        <Section title={t("device.section.plc.title")}>
          <FormRow {...f("plcIpAddress", true)} htmlFor="plcIpAddress" error={form.formState.errors.plcIpAddress?.message}>
            <Input id="plcIpAddress" placeholder={ph("plcIpAddress")} {...inv("plcIpAddress")} {...form.register("plcIpAddress")} />
          </FormRow>
          <FormRow {...f("plcPort", true)} htmlFor="plcPort" error={form.formState.errors.plcPort?.message}>
            <Input id="plcPort" type="number" min={1} max={65535} {...inv("plcPort")} {...form.register("plcPort")} />
          </FormRow>
          <FormRow {...f("plcConnectionMethod", true)} htmlFor="plcConnectionMethod">
            <Input id="plcConnectionMethod" placeholder={ph("plcConnectionMethod")} {...form.register("plcConnectionMethod")} />
          </FormRow>
          <FormRow {...f("plcReadFrequency")} htmlFor="plcReadFrequency">
            <Input id="plcReadFrequency" type="number" min={1} {...form.register("plcReadFrequency")} />
          </FormRow>
          <FormRow {...f("plcTagsMapping", true)} htmlFor="plcTagsMapping" error={form.formState.errors.plcTagsMapping?.message}>
            <Textarea id="plcTagsMapping" placeholder={ph("plcTagsMapping")} {...inv("plcTagsMapping")} {...form.register("plcTagsMapping")} />
          </FormRow>
          <FormRow {...f("plcCredentials")} htmlFor="plcCredentialsJson">
            <Textarea id="plcCredentialsJson" placeholder={ph("plcCredentialsJson")} {...form.register("plcCredentialsJson")} />
          </FormRow>
        </Section>
      )}

      {protocol === "lorawan" && (
        <Section title={t("device.section.lora.title")}>
          <FormRow {...f("loraDevEui", true)} htmlFor="loraDevEui" error={form.formState.errors.loraDevEui?.message}>
            <Input id="loraDevEui" {...form.register("loraDevEui")} />
          </FormRow>
          <FormRow {...f("loraAppEui", true)} htmlFor="loraAppEui" error={form.formState.errors.loraAppEui?.message}>
            <Input id="loraAppEui" {...form.register("loraAppEui")} />
          </FormRow>
          <FormRow {...f("loraAppKey", true)} htmlFor="loraAppKey" error={form.formState.errors.loraAppKey?.message}>
            <Input id="loraAppKey" {...form.register("loraAppKey")} />
          </FormRow>
          <FormRow {...f("loraNetworkServer", true)} htmlFor="loraNetworkServer">
            <Input id="loraNetworkServer" {...form.register("loraNetworkServer")} />
          </FormRow>
          <FormRow {...f("loraPayloadDecoder", true)} htmlFor="loraPayloadDecoder">
            <Input id="loraPayloadDecoder" {...form.register("loraPayloadDecoder")} />
          </FormRow>
        </Section>
      )}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => router.back()}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" loading={mutation.isPending}>
          {props.mode === "create" ? t("device.create") : t("common.save")}
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

function FormRow({
  htmlFor,
  label,
  tooltip,
  required,
  error,
  children,
}: {
  htmlFor: string;
  label: string;
  tooltip?: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <FieldLabel htmlFor={htmlFor} label={label} tooltip={tooltip} required={required} />
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

function LocationPicker({
  form,
  hint,
}: {
  form: ReturnType<typeof useForm<DeviceFormValues>>;
  hint: string;
}) {
  const lat = form.watch("latitude");
  const lng = form.watch("longitude");
  const setBoth = React.useCallback(
    (la: number, lo: number) => {
      form.setValue("latitude", la, { shouldDirty: true, shouldValidate: false });
      form.setValue("longitude", lo, { shouldDirty: true, shouldValidate: false });
    },
    [form],
  );
  return (
    <div className="space-y-1.5">
      <DeviceMap
        mode="picker"
        lat={typeof lat === "number" ? lat : undefined}
        lng={typeof lng === "number" ? lng : undefined}
        onChange={setBoth}
      />
      <p className="text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

/** Return undefined if a translation key is missing instead of throwing. */
function safe(t: ReturnType<typeof useTranslations>, key: string): string | undefined {
  try {
    const v = t(key);
    // next-intl returns the key path on miss in dev; treat missing key as undefined.
    return v && v !== key ? v : undefined;
  } catch {
    return undefined;
  }
}

function toFormValues(d: Device): Partial<DeviceFormValues> {
  return {
    name: d.name,
    category: d.category,
    supportedProtocol: d.supportedProtocol,
    serialNumber: d.serialNumber,
    serialNumberType: d.serialNumberType,
    manufacturerName: d.manufacturerName,
    modelName: d.modelName,
    firmwareVersion: d.firmwareVersion,
    deviceState: d.deviceState,
    controlledProperty: d.controlledProperty?.join(", "),
    latitude: d.location?.latitude,
    longitude: d.location?.longitude,
    siteArea: d.location?.site_area ?? undefined,
    dateInstalled: d.dateInstalled
      ? d.dateInstalled.replace("Z", "").slice(0, 16)
      : undefined,
    ownerCsv: d.owner?.join(", "),
    ipAddressCsv: d.ipAddress?.join(", "),
    addressJson: d.address ? JSON.stringify(d.address) : undefined,
    mqttTopicRoot: d.mqttTopicRoot,
    mqttClientId: d.mqttClientId,
    mqttQos: d.mqttQos,
    dataTypesJson: d.dataTypes ? JSON.stringify(d.dataTypes) : undefined,
    mqttSecurityJson: d.mqttSecurity ? JSON.stringify(d.mqttSecurity) : undefined,
    plcIpAddress: d.plcIpAddress,
    plcPort: d.plcPort,
    plcConnectionMethod: d.plcConnectionMethod,
    plcReadFrequency: d.plcReadFrequency,
    plcTagsMapping: d.plcTagsMapping ? JSON.stringify(d.plcTagsMapping) : undefined,
    plcCredentialsJson: d.plcCredentials ? JSON.stringify(d.plcCredentials) : undefined,
    loraAppEui: d.loraAppEui,
    loraDevEui: d.loraDevEui,
    loraAppKey: d.loraAppKey,
    loraNetworkServer: d.loraNetworkServer,
    loraPayloadDecoder: d.loraPayloadDecoder,
  };
}

function tryJson(text: string | undefined): unknown {
  if (!text) return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function csvList(text: string | undefined): string[] | undefined {
  if (!text) return undefined;
  const arr = text.split(",").map((s) => s.trim()).filter(Boolean);
  return arr.length ? arr : undefined;
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
  set("controlledProperty", csvList(values.controlledProperty));
  set("owner", csvList(values.ownerCsv));
  set("ipAddress", csvList(values.ipAddressCsv));
  if (values.dateInstalled) {
    const v = values.dateInstalled.length === 16
      ? `${values.dateInstalled}:00Z`
      : values.dateInstalled;
    out.dateInstalled = v;
  }
  if (values.latitude !== undefined && values.longitude !== undefined) {
    const loc: Record<string, unknown> = {
      latitude: values.latitude,
      longitude: values.longitude,
    };
    if (values.siteArea) loc.site_area = values.siteArea;
    out.location = loc;
  }
  if (values.addressJson) {
    out.address = tryJson(values.addressJson);
  }
  if (values.supportedProtocol === "mqtt") {
    set("mqttTopicRoot", values.mqttTopicRoot);
    set("mqttClientId", values.mqttClientId);
    set("mqttQos", values.mqttQos);
    if (values.dataTypesJson) out.dataTypes = tryJson(values.dataTypesJson);
    if (values.mqttSecurityJson) out.mqttSecurity = tryJson(values.mqttSecurityJson);
  }
  if (values.supportedProtocol === "plc") {
    set("plcIpAddress", values.plcIpAddress);
    set("plcPort", values.plcPort);
    set("plcConnectionMethod", values.plcConnectionMethod);
    set("plcReadFrequency", values.plcReadFrequency);
    if (values.plcTagsMapping) out.plcTagsMapping = tryJson(values.plcTagsMapping);
    if (values.plcCredentialsJson) out.plcCredentials = tryJson(values.plcCredentialsJson);
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
