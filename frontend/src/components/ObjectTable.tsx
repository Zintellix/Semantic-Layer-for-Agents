import type { ObjectsView } from "../types";

const MONEY_HINT = /revenue|amount|budget|spend|arr|pipeline|quota/i;

function fmt(col: string, v: string | number | boolean | null): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    if (MONEY_HINT.test(col)) return "₹" + v.toLocaleString("en-IN", { maximumFractionDigits: 0 });
    return String(v);
  }
  return String(v);
}

export function ObjectTable({
  view,
  onSignal,
}: {
  view: ObjectsView;
  onSignal: (key: string) => void;
}) {
  const w = view.window;
  return (
    <div>
      {w && (
        <p className="muted small">
          Seeded window · <b>{w.window}</b>: starts in {w.starts_in_days} days, runs{" "}
          {w.duration_days} days, +{w.expected_uplift_pct}% demand.
        </p>
      )}
      <p className="muted small">
        Object set <code>{view.object_set}</code> members are flagged <b>top</b> and ranked first.
      </p>
      <div className="table-scroll">
        <table className="shades">
          <thead>
            <tr>
              <th>{view.label}</th>
              {view.columns.map((c) => (
                <th key={c} className="r">
                  {c}
                </th>
              ))}
              <th></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {view.rows.map((r) => (
              <tr key={r.key} className={r.top ? "hero" : ""}>
                <td>
                  <span className="mono">{r.title}</span>
                </td>
                {view.columns.map((c) => (
                  <td key={c} className="r">
                    {fmt(c, r[c] ?? null)}
                  </td>
                ))}
                <td>{r.top && <span className="badge hero-badge">top</span>}</td>
                <td>
                  <button className="btn tiny" onClick={() => onSignal(r.key)}>
                    signal
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
