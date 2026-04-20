import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const http = axios.create({ baseURL: API, timeout: 20000 });

export const fmtDist = (m) => (m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`);
export const fmtDur = (s) => {
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
};
export const fmtDate = (iso) => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-SG", { dateStyle: "medium", timeStyle: "short" });
  } catch { return iso; }
};

export const ROLES = [
  { id: "admin", label: "Super Admin" },
  { id: "hub_manager", label: "Hub Manager" },
  { id: "shipper", label: "Shipper" },
];
