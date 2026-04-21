import React, { useState, useEffect } from "react";
import { MapContainer, TileLayer, Polygon, Polyline, CircleMarker, Marker, useMapEvents } from "react-leaflet";
import L from "leaflet";

const vertexIcon = L.divIcon({
  className: "",
  html: `<div style="background:#fff;border:2px solid #0d7c78;border-radius:50%;width:12px;height:12px;box-shadow:0 1px 3px rgba(0,0,0,.2)"></div>`,
  iconSize: [12, 12],
  iconAnchor: [6, 6],
});

function ClickHandler({ onClick, enabled }) {
  useMapEvents({
    click(e) { if (enabled) onClick([e.latlng.lat, e.latlng.lng]); },
  });
  return null;
}

/**
 * Interactive polygon editor.
 * - Click on map to add a vertex (when Draw Mode on)
 * - Drag any vertex to reshape
 * - Click a vertex in the list to remove it
 *
 * Props:
 *   value: number[][]    // current polygon [[lat,lng], ...]
 *   onChange(points)
 *   color: string        // outline color
 *   height: number
 */
export default function PolygonEditor({ value = [], onChange, color = "#0d7c78", height = 420 }) {
  const [drawMode, setDrawMode] = useState(value.length < 3);
  const [points, setPoints] = useState(value || []);

  useEffect(() => { setPoints(value || []); }, [value]);

  const push = (p) => { const next = [...points, p]; setPoints(next); onChange && onChange(next); };
  const updateAt = (i, p) => { const next = points.map((x, idx) => (idx === i ? p : x)); setPoints(next); onChange && onChange(next); };
  const removeAt = (i) => { const next = points.filter((_, idx) => idx !== i); setPoints(next); onChange && onChange(next); };
  const clear = () => { setPoints([]); onChange && onChange([]); };
  const undo = () => { const next = points.slice(0, -1); setPoints(next); onChange && onChange(next); };

  const center = points.length ? points[0] : [1.3521, 103.8198];

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center", flexWrap: "wrap" }}>
        <button type="button" className={`btn sm ${drawMode ? "primary" : ""}`}
          onClick={() => setDrawMode(v => !v)} data-testid="toggle-draw-mode">
          {drawMode ? "✍ Draw mode: ON" : "✍ Draw mode: OFF"}
        </button>
        <button type="button" className="btn sm" disabled={points.length === 0} onClick={undo} data-testid="undo-vertex">↶ Undo vertex</button>
        <button type="button" className="btn sm ghost" disabled={points.length === 0} onClick={clear} data-testid="clear-polygon" style={{ color: "#b91c1c" }}>Clear</button>
        <span className="muted" style={{ fontSize: 11.5 }}>
          Vertices: <b>{points.length}</b>{points.length < 3 ? " — add at least 3 to form a polygon" : ""}
        </span>
      </div>
      <div style={{ height, borderRadius: 8, overflow: "hidden", border: "1px solid var(--border)", position: "relative", cursor: drawMode ? "crosshair" : "grab" }}>
        <MapContainer center={center} zoom={12} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            attribution="&copy; OpenStreetMap &copy; CARTO"
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />
          <ClickHandler enabled={drawMode} onClick={push} />

          {points.length >= 3 && (
            <Polygon positions={points} pathOptions={{ color, weight: 2, fillOpacity: 0.18 }} />
          )}
          {points.length === 2 && (
            <Polyline positions={points} pathOptions={{ color, weight: 2, dashArray: "4 4" }} />
          )}
          {points.map((p, i) => (
            <Marker key={i} position={p} icon={vertexIcon} draggable
              eventHandlers={{
                dragend: (e) => { const { lat, lng } = e.target.getLatLng(); updateAt(i, [lat, lng]); },
                click: () => { if (!drawMode) removeAt(i); },
              }} />
          ))}
        </MapContainer>
      </div>
      <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>
        Tip: Toggle <b>Draw mode OFF</b> and click a vertex to remove it. Drag any vertex to reshape. Zoom in and add more vertices along roads to trace curves precisely.
      </div>
    </div>
  );
}
