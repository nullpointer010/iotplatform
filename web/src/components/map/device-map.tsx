"use client";

import * as React from "react";
import L from "leaflet";
import {
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import Link from "next/link";
import "leaflet/dist/leaflet.css";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";
import type { Device } from "@/lib/types";

// Fix default marker icons under bundlers (Leaflet 1.x quirk).
// react-leaflet otherwise tries to resolve relative URLs that the
// webpack build does not provide.
delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: (iconRetinaUrl as unknown as { src: string }).src ?? (iconRetinaUrl as unknown as string),
  iconUrl: (iconUrl as unknown as { src: string }).src ?? (iconUrl as unknown as string),
  shadowUrl: (shadowUrl as unknown as { src: string }).src ?? (shadowUrl as unknown as string),
});

const ALMERIA: [number, number] = [36.8381, -2.4597];
const OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

function round6(n: number): number {
  return Math.round(n * 1_000_000) / 1_000_000;
}

function hasCoords(d: Device): d is Device & { location: { latitude: number; longitude: number } } {
  return (
    typeof d.location?.latitude === "number" &&
    typeof d.location?.longitude === "number"
  );
}

export type DeviceMapProps =
  | {
      mode: "list";
      devices: Device[];
      className?: string;
    }
  | {
      mode: "single";
      lat: number;
      lng: number;
      className?: string;
    }
  | {
      mode: "picker";
      lat?: number;
      lng?: number;
      onChange: (lat: number, lng: number) => void;
      className?: string;
    };

export default function DeviceMap(props: DeviceMapProps) {
  if (props.mode === "list") return <ListMap {...props} />;
  if (props.mode === "single") return <SingleMap {...props} />;
  return <PickerMap {...props} />;
}

function ListMap({ devices, className }: Extract<DeviceMapProps, { mode: "list" }>) {
  const geo = devices.filter(hasCoords);
  const center: [number, number] =
    geo.length > 0 ? [geo[0].location.latitude, geo[0].location.longitude] : ALMERIA;
  const initialZoom = geo.length === 0 ? 11 : 6;

  return (
    <div className={className ?? "w-full overflow-hidden rounded-lg border"}>
      <MapContainer
        center={center}
        zoom={initialZoom}
        scrollWheelZoom
        style={{ height: 480, width: "100%" }}
      >
        <TileLayer url={OSM_URL} attribution={OSM_ATTR} />
        <FitToDevices devices={geo} />
        {geo.map((d) => (
          <Marker
            key={d.id}
            position={[d.location.latitude, d.location.longitude]}
          >
            <Popup>
              <div className="space-y-1 text-sm">
                <Link
                  href={`/devices/${encodeURIComponent(d.id)}`}
                  className="font-medium text-primary hover:underline"
                >
                  {d.name ?? d.id}
                </Link>
                <div className="text-xs text-muted-foreground">{d.id}</div>
                <div className="text-xs">
                  {d.category ?? "—"} · {d.supportedProtocol ?? "—"}
                </div>
                {d.location.site_area && (
                  <div className="text-xs">{d.location.site_area}</div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}

function FitToDevices({ devices }: { devices: Array<Device & { location: { latitude: number; longitude: number } }> }) {
  const map = useMap();
  const sig = devices
    .map((d) => `${d.location.latitude},${d.location.longitude}`)
    .join("|");
  React.useEffect(() => {
    if (devices.length === 0) return;
    if (devices.length === 1) {
      map.setView(
        [devices[0].location.latitude, devices[0].location.longitude],
        13,
      );
      return;
    }
    const bounds = L.latLngBounds(
      devices.map((d) => [d.location.latitude, d.location.longitude] as [number, number]),
    );
    map.fitBounds(bounds, { padding: [32, 32] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sig, map]);
  return null;
}

function SingleMap({ lat, lng, className }: Extract<DeviceMapProps, { mode: "single" }>) {
  return (
    <div className={className ?? "w-full overflow-hidden rounded-lg border"}>
      <MapContainer
        center={[lat, lng]}
        zoom={15}
        scrollWheelZoom={false}
        style={{ height: 280, width: "100%" }}
      >
        <TileLayer url={OSM_URL} attribution={OSM_ATTR} />
        <Marker position={[lat, lng]} />
      </MapContainer>
    </div>
  );
}

function PickerMap({ lat, lng, onChange, className }: Extract<DeviceMapProps, { mode: "picker" }>) {
  const hasPin = typeof lat === "number" && typeof lng === "number";
  const center: [number, number] = hasPin ? [lat!, lng!] : ALMERIA;
  const initialZoom = hasPin ? 13 : 11;

  return (
    <div className={className ?? "w-full overflow-hidden rounded-lg border"}>
      <MapContainer
        center={center}
        zoom={initialZoom}
        scrollWheelZoom
        style={{ height: 320, width: "100%" }}
      >
        <TileLayer url={OSM_URL} attribution={OSM_ATTR} />
        <PickerInner lat={lat} lng={lng} onChange={onChange} />
      </MapContainer>
    </div>
  );
}

function PickerInner({
  lat,
  lng,
  onChange,
}: {
  lat?: number;
  lng?: number;
  onChange: (lat: number, lng: number) => void;
}) {
  const map = useMap();
  const hasPin = typeof lat === "number" && typeof lng === "number";

  // Recenter when external value changes meaningfully.
  const lastSyncRef = React.useRef<string>("");
  React.useEffect(() => {
    if (!hasPin) return;
    const sig = `${lat},${lng}`;
    if (sig === lastSyncRef.current) return;
    lastSyncRef.current = sig;
    map.panTo([lat!, lng!]);
  }, [lat, lng, hasPin, map]);

  useMapEvents({
    click(e) {
      onChange(round6(e.latlng.lat), round6(e.latlng.lng));
    },
  });

  if (!hasPin) return null;
  return (
    <Marker
      position={[lat!, lng!]}
      draggable
      eventHandlers={{
        dragend: (e) => {
          const m = e.target as L.Marker;
          const ll = m.getLatLng();
          onChange(round6(ll.lat), round6(ll.lng));
        },
      }}
    />
  );
}
