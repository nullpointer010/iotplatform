import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { DeviceForm } from "@/components/forms/device-form";

export default function NewDevicePage() {
  return (
    <div className="space-y-6">
      <Link
        href="/devices"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ChevronLeft className="mr-1 h-4 w-4" /> Back to devices
      </Link>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New device</h1>
        <p className="text-sm text-muted-foreground">
          Register a Device entity in Orion. Required protocol-specific fields
          appear after picking a protocol.
        </p>
      </div>
      <DeviceForm mode="create" />
    </div>
  );
}
