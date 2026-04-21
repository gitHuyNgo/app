import React from "react";
import { MapContainer, TileLayer, Marker, Popup, Polygon, Polyline, CircleMarker, Tooltip as LTooltip } from "react-leaflet";
import L from "leaflet";

// Fix default icon shadows issue when bundling
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const SG_CENTER = [1.3521, 103.8198];

const hubIcon = L.divIcon({ className: "", html: `<div class="hub-marker"></div>`, iconSize: [18, 18] });
const hubIconLg = L.divIcon({ className: "", html: `<div class="hub-marker lg"></div>`, iconSize: [22, 22] });
const orderIcon = (status = "pending") =>
  L.divIcon({ className: "", html: `<div class="order-marker ${status}"></div>`, iconSize: [12, 12] });
const driverIcon = (initial = "D") =>
  L.divIcon({ className: "", html: `<div class="driver-marker">${initial}</div>`, iconSize: [22, 22] });

// Traffic speed bands color
function speedColor(band) {
  // 1 = slowest (red) ... 8 = fast (green)
  const colors = ["#b91c1c", "#ef4444", "#f97316", "#f59e0b", "#eab308", "#84cc16", "#22c55e", "#16a34a"];
  return colors[Math.min(Math.max(band - 1, 0), 7)];
}

export default function MapView({
  height = 560,
  orders = [],
  drivers = [],
  zones = [],
  routes = [],            // [{ geometry: [[lat,lng],...], color }]
  incidents = [],
  speedBands = [],
  hubs = [],              // [{id, name, lat, lng, is_default}]
  showHub = false,        // legacy: single hub at SG_CENTER
  fitTo = null,
}) {
  const center = SG_CENTER;
  return (
    <div className="map-wrap" style={{ height }}>
      <MapContainer center={center} zoom={12} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
        <TileLayer
          attribution='&copy; OpenStreetMap &copy; CARTO'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />

        {speedBands.map((s, i) => (
          <Polyline
            key={`sb-${i}`}
            positions={[[s.StartLat, s.StartLon], [s.EndLat, s.EndLon]]}
            pathOptions={{ color: speedColor(s.SpeedBand || 4), weight: 3, opacity: 0.5 }}
          />
        ))}

        {zones.map((z) => (
          <Polygon key={z.id} positions={z.polygon} pathOptions={{ color: z.color || "#0d7c78", weight: 2, fillOpacity: 0.12 }}>
            <LTooltip sticky>{z.name}</LTooltip>
          </Polygon>
        ))}

        {routes.map((r, i) => (
          <Polyline key={`rt-${i}`} positions={r.geometry || []}
            pathOptions={{ color: r.color || "#0d7c78", weight: 4, opacity: 0.85 }} />
        ))}

        {hubs.map((h) => (
          <Marker key={h.id} position={[h.lat, h.lng]} icon={h.is_default ? hubIconLg : hubIcon}>
            <Popup>
              <div style={{ fontSize: 12 }}>
                <div style={{ fontWeight: 600 }}>{h.name} {h.is_default && <span style={{color:'#d2233c'}}>· default</span>}</div>
                {h.address && <div style={{ color: "#475569" }}>{h.address}</div>}
                <div style={{ color: "#64748b" }}>{h.lat.toFixed(4)}, {h.lng.toFixed(4)}</div>
              </div>
            </Popup>
          </Marker>
        ))}

        {showHub && hubs.length === 0 && (
          <Marker position={[1.3521, 103.8198]} icon={hubIcon}>
            <Popup>Central Hub</Popup>
          </Marker>
        )}

        {orders.map((o) => (
          <Marker key={o.id} position={[o.lat, o.lng]} icon={orderIcon(o.status)}>
            <Popup>
              <div style={{ fontSize: 12 }}>
                <div style={{ fontWeight: 600 }}>{o.code}</div>
                <div>{o.address}</div>
                <div style={{ color: "#64748b" }}>Postal {o.postal_code} · {o.weight_kg} kg</div>
                <div>Status: <b>{o.status}</b></div>
                {o.sequence && <div>Sequence: #{o.sequence}</div>}
              </div>
            </Popup>
          </Marker>
        ))}

        {drivers.filter(d => d.location).map((d) => (
          <Marker key={d.id} position={[d.location.lat, d.location.lng]} icon={driverIcon((d.name || "?")[0])}>
            <Popup>
              <div style={{ fontSize: 12 }}>
                <div style={{ fontWeight: 600 }}>{d.name}</div>
                <div>Status: {d.status}</div>
                <div>Last update: {d.location.updated_at}</div>
              </div>
            </Popup>
          </Marker>
        ))}

        {incidents.map((e, i) => (
          <CircleMarker key={`inc-${i}`} center={[e.Latitude, e.Longitude]} radius={5}
            pathOptions={{ color: "#d2233c", fillColor: "#d2233c", fillOpacity: 0.7 }}>
            <Popup><div style={{ fontSize: 11, maxWidth: 260 }}><b>{e.Type}</b><br/>{e.Message}</div></Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
