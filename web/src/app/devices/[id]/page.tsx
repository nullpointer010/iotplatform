"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { OverviewTab } from "./overview-tab";
import { TelemetryTab } from "./telemetry-tab";
import { MaintenanceTab } from "./maintenance-tab";

export default function DeviceDetailPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const device = useQuery({
    queryKey: ["device", id],
    queryFn: () => api.getDevice(id),
  });

  if (device.isLoading) {
    return <p className="text-muted-foreground">Loading…</p>;
  }
  if (device.isError || !device.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Device not found</CardTitle>
        </CardHeader>
        <CardContent>
          <Link href="/devices" className="text-sm text-primary hover:underline">
            Back to devices
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Link
        href="/devices"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ChevronLeft className="mr-1 h-4 w-4" /> Back to devices
      </Link>
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {device.data.name ?? device.data.id}
          </h1>
          <p className="text-xs text-muted-foreground">{device.data.id}</p>
        </div>
        <Button asChild variant="outline">
          <Link href={`/devices/${encodeURIComponent(device.data.id)}/edit`}>
            <Pencil className="mr-2 h-4 w-4" /> Edit
          </Link>
        </Button>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="telemetry">Telemetry</TabsTrigger>
          <TabsTrigger value="maintenance">Maintenance</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">
          <OverviewTab device={device.data} />
        </TabsContent>
        <TabsContent value="telemetry">
          <TelemetryTab deviceId={device.data.id} device={device.data} />
        </TabsContent>
        <TabsContent value="maintenance">
          <MaintenanceTab deviceId={device.data.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
