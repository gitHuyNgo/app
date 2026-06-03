import React, { useEffect } from "react";
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";

const buildPinIcon = (color = "#d2233c") => L.divIcon({
  className: "",
  html: `<div style="background:${color};border:3px solid #fff;border-radius:50% 50% 50% 0;width:22px;height:22px;transform:rotate(-45deg);box-shadow:0 2px 6px rgba(0,0,0,.3)"></div>`,
  iconSize: [22, 22],
  iconAnchor: [11, 22],
});

/** Pans the map whenever the controlled ``position`` changes. */
function PanTo({ position }) {
  const map = useMap();
  useEffect(() => {
    if (position) map.flyTo(position, Math.max(map.getZoom(), 15), { duration: 0.6 });
  }, [position?.[0], position?.[1]]);  // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

function ClickHandler({ onPick }) {
  useMapEvents({
    click(e) { onPick([e.latlng.lat, e.latlng.lng]); },
  });
  return null;
}

/**
 * Fully-controlled map picker.
 *
 * Props:
 *   position: [lat, lng]       — current pin location (source of truth lives in parent)
 *   onChange(point)            — called whenever the user clicks the map or drags the pin
 *   height
 */
export default function HubPicker({ position, onChange, height = 320, color = "#d2233c" }) {
  const pos = position || [1.3521, 103.8198];
  const pinIcon = buildPinIcon(color);

  return (
    <div style={{ height, borderRadius: 8, overflow: "hidden", border: "1px solid var(--border)" }}>
      <MapContainer center={pos} zoom={13} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution="&copy; OpenStreetMap &copy; CARTO"
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <PanTo position={pos} />
        <ClickHandler onPick={(p) => onChange && onChange(p)} />
        <Marker
          position={pos}
          icon={pinIcon}
          draggable
          eventHandlers={{
            dragend: (e) => {
              const { lat, lng } = e.target.getLatLng();
              onChange && onChange([lat, lng]);
            },
          }}
        />
      </MapContainer>
    </div>
  );
}
