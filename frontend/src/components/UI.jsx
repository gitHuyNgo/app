import React from "react";

export function Modal({ open, title, onClose, children, footer }) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={onClose} data-testid="modal-backdrop">
      <div className="modal" onClick={(e) => e.stopPropagation()} data-testid="modal">
        <h3>{title}</h3>
        {children}
        {footer && <div className="modal-actions">{footer}</div>}
      </div>
    </div>
  );
}

export function Badge({ children, tone = "default" }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Empty({ title = "Nothing here yet", hint }) {
  return <div className="empty"><div style={{ fontWeight: 600, color: "#0b1e24", marginBottom: 4 }}>{title}</div>{hint && <div>{hint}</div>}</div>;
}
