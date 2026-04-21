import React, { useState } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
import L from "leaflet";

const pinIcon = L.divIcon({
  className: "",
  html: `<div style="background:#d2233c;border:3px solid #fff;border-radius:50% 50% 50% 0;width:22px;height:22px;transform:rotate(-45deg);box-shadow:0 2px 6px rgba(0,0,0,.3)"></div>`,
  iconSize: [22, 22],
  iconAnchor: [11, 22],
});

function ClickHandler({ onPick }) {
  useMapEvents({
    click(e) { onPick([e.latlng.lat, e.latlng.lng]); },
  });
  return null;
}

/** Interactive map to pick a geo location by clicking or dragging the pin. */
export default function HubPicker({ position, onChange, height = 320 }) {
  const [pos, setPos] = useState(position || [1.3521, 103.8198]);

  const set = (p) => { setPos(p); onChange && onChange(p); };

  return (
    <div style={{ height, borderRadius: 8, overflow: "hidden", border: "1px solid var(--border)" }}>
      <MapContainer center={pos} zoom={13} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution="&copy; OpenStreetMap &copy; CARTO"
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <ClickHandler onPick={set} />
        <Marker
          position={pos}
          icon={pinIcon}
          draggable
          eventHandlers={{
            dragend: (e) => {
              const { lat, lng } = e.target.getLatLng();
              set([lat, lng]);
            },
          }}
        />
      </MapContainer>
    </div>
  );
}
