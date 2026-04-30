"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";
import { DeviceForm } from "@/components/forms/device-form";
import { api } from "@/lib/api";

export default function EditDevicePage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const device = useQuery({
    queryKey: ["device", id],
    queryFn: () => api.getDevice(id),
  });

  return (
    <div className="space-y-6">
      <Link
        href={`/devices/${encodeURIComponent(id)}`}
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ChevronLeft className="mr-1 h-4 w-4" /> Back to device
      </Link>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Edit device</h1>
        <p className="text-xs text-muted-foreground">{id}</p>
      </div>
      {device.isLoading && <p className="text-muted-foreground">Loading…</p>}
      {device.isError && (
        <p className="text-destructive">{(device.error as Error).message}</p>
      )}
      {device.data && <DeviceForm mode="edit" device={device.data} />}
    </div>
  );
}
