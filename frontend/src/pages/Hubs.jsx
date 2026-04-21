import React, { useEffect, useState } from "react";
import { http, fmtDate } from "../lib/api";
import MapView from "../components/MapView";
import HubPicker from "../components/HubPicker";
import { Modal, Badge } from "../components/UI";

export default function Hubs() {
  const [hubs, setHubs] = useState([]);
  const [editing, setEditing] = useState(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", address: "", lat: 1.3521, lng: 103.8198, is_default: false, notes: "" });
  const [geo, setGeo] = useState({ q: "", busy: false, results: [], error: "" });

  const load = async () => { const r = await http.get("/hubs"); setHubs(r.data); };
  useEffect(() => { load(); }, []);

  const openNew = () => {
    setEditing(null);
    setForm({ name: "", address: "", lat: 1.3521, lng: 103.8198, is_default: hubs.length === 0, notes: "" });
    setGeo({ q: "", busy: false, results: [], error: "" });
    setOpen(true);
  };
  const openEdit = (h) => {
    setEditing(h);
    setForm({ name: h.name, address: h.address || "", lat: h.lat, lng: h.lng, is_default: !!h.is_default, notes: h.notes || "" });
    setGeo({ q: "", busy: false, results: [], error: "" });
    setOpen(true);
  };

  const save = async () => {
    if (!form.name) return;
    if (editing) await http.put(`/hubs/${editing.id}`, form);
    else await http.post("/hubs", form);
    setOpen(false); load();
  };
  const remove = async (h) => { if (!window.confirm(`Delete hub "${h.name}"?`)) return; await http.delete(`/hubs/${h.id}`); load(); };
  const makeDefault = async (h) => { await http.put(`/hubs/${h.id}`, { ...h, is_default: true }); load(); };

  const geocode = async () => {
    if (!geo.q || geo.q.length < 3) return;
    setGeo(g => ({ ...g, busy: true, error: "", results: [] }));
    try {
      const r = await http.get("/geocode", { params: { q: geo.q } });
      if (r.data.error) setGeo(g => ({ ...g, busy: false, error: r.data.error, results: [] }));
      else setGeo(g => ({ ...g, busy: false, results: r.data.results || [] }));
    } catch (e) {
      setGeo(g => ({ ...g, busy: false, error: "Geocoder error — drag the pin on the map instead." }));
    }
  };

  const selectGeo = (r) => {
    setForm(f => ({ ...f, lat: r.lat, lng: r.lng, address: f.address || r.name }));
    setGeo(g => ({ ...g, results: [] }));
  };

  return (
    <div>
      <div className="page-title"><span className="accent"></span>Hubs</div>
      <div className="page-subtitle">Multiple hub locations · Click a row or the map to add / edit / relocate</div>

      <div className="toolbar">
        <button className="btn primary" data-testid="add-hub-btn" onClick={openNew}>+ Add Hub</button>
        <span className="muted" style={{ fontSize: 12 }}>Default hub is used by route planning & auto-assignment.</span>
      </div>

      <div className="section">
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <MapView height={520} hubs={hubs} />
        </div>

        <div className="card" style={{ padding: 0, maxHeight: 620, overflow: "auto" }}>
          <table className="tbl" data-testid="hubs-table">
            <thead><tr><th>Name</th><th>Address / Coords</th><th>Default</th><th></th></tr></thead>
            <tbody>
              {hubs.map(h => (
                <tr key={h.id}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--red)" }}></span>
                      <b>{h.name}</b>
                    </div>
                    <div className="muted" style={{ fontSize: 11 }}>{fmtDate(h.created_at)}</div>
                  </td>
                  <td style={{ fontSize: 12 }}>
                    <div>{h.address || <span className="muted">No address</span>}</div>
                    <div className="muted">{h.lat.toFixed(4)}, {h.lng.toFixed(4)}</div>
                  </td>
                  <td>{h.is_default ? <Badge tone="ev">Default</Badge> :
                    <button className="btn sm ghost" onClick={() => makeDefault(h)} data-testid={`set-default-hub-${h.id}`}>Set default</button>}</td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn sm ghost" onClick={() => openEdit(h)} data-testid={`edit-hub-${h.id}`}>Edit</button>
                    <button className="btn sm ghost" style={{ color: "#b91c1c" }} onClick={() => remove(h)} data-testid={`del-hub-${h.id}`}>Delete</button>
                  </td>
                </tr>
              ))}
              {hubs.length === 0 && <tr><td colSpan={4} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>No hubs yet. Add your first hub.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <Modal open={open} title={editing ? `Edit ${editing.name}` : "New Hub"} onClose={() => setOpen(false)}
        footer={<>
          <button className="btn" onClick={() => setOpen(false)}>Cancel</button>
          <button className="btn primary" onClick={save} disabled={!form.name} data-testid="save-hub-btn">{editing ? "Save" : "Create"}</button>
        </>}>
        <div className="field"><label className="label">Hub name</label>
          <input className="input" data-testid="hub-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
        <div className="field"><label className="label">Address (optional, free text)</label>
          <input className="input" data-testid="hub-address" value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} placeholder="e.g., 1 Tanglin Rd, Singapore" /></div>

        <div className="field">
          <label className="label">Search address (OpenStreetMap)</label>
          <div style={{ display: "flex", gap: 8 }}>
            <input className="input" data-testid="hub-geocode-q" value={geo.q} onChange={e => setGeo(g => ({ ...g, q: e.target.value }))}
              onKeyDown={e => e.key === "Enter" && geocode()} placeholder="e.g., Marina Bay Sands" />
            <button type="button" className="btn" disabled={geo.busy || geo.q.length < 3} onClick={geocode} data-testid="hub-geocode-btn">
              {geo.busy ? "…" : "Search"}
            </button>
          </div>
          {geo.error && <div style={{ color: "#b91c1c", fontSize: 11.5, marginTop: 6 }}>{geo.error}</div>}
          {geo.results.length > 0 && (
            <div style={{ marginTop: 6, border: "1px solid var(--border)", borderRadius: 8, maxHeight: 140, overflow: "auto" }}>
              {geo.results.map((r, i) => (
                <div key={i} style={{ padding: "8px 10px", borderBottom: "1px solid var(--border)", fontSize: 12, cursor: "pointer" }}
                  onClick={() => selectGeo(r)} data-testid={`geo-result-${i}`}>
                  <b>{r.name.split(",")[0]}</b> <span className="muted">{r.name}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="field">
          <label className="label">Location — click the map or drag the pin</label>
          <HubPicker position={[form.lat, form.lng]} onChange={(p) => setForm(f => ({ ...f, lat: p[0], lng: p[1] }))} height={260} />
          <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
            {form.lat.toFixed(5)}, {form.lng.toFixed(5)}
          </div>
        </div>

        <div className="field" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input type="checkbox" id="hub-default" data-testid="hub-is-default"
            checked={!!form.is_default} onChange={e => setForm({ ...form, is_default: e.target.checked })} />
          <label htmlFor="hub-default" style={{ fontSize: 13 }}>Use as default hub (routes + auto-assign start here)</label>
        </div>
        <div className="field"><label className="label">Notes</label>
          <textarea className="textarea" data-testid="hub-notes" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
      </Modal>
    </div>
  );
}
