"use client";

export function PreviewPanel() {
  return (
    <div className="preview-frame">
      <div className="preview-toolbar">
        <span />
        <span />
        <span />
      </div>
      <div className="preview-body">
        <p className="eyebrow">Generated Product</p>
        <h3>Mock-first analysis console</h3>
        <div className="preview-metric">
          <span>Demo readiness</span>
          <strong>4.2 / 5</strong>
        </div>
        <div className="preview-metric">
          <span>Adapter mode</span>
          <strong>Mock</strong>
        </div>
      </div>
    </div>
  );
}
