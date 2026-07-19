import type { Stage } from "../types";

const STAGE_HINT: Record<string, string> = {
  parse: "keyword extraction → entity_mentions",
  resolve: "L6 · resolution ladder + O6 gate",
  plan: "L7 · link-path validation",
  prefetch: "L7 · object reads + function evals",
  agent: "L10 · agent call with Ontology Context",
  validate: "L11 · numeric + entity + action-schema",
  respond: "L12 · answer + citations + action card",
};

export function TraceView({ stages }: { stages: Stage[] }) {
  return (
    <ol className="trace">
      {stages.map((s) => (
        <li key={s.n} className="trace-step">
          <div className="trace-num">{s.n}</div>
          <div className="trace-body">
            <div className="trace-head">
              <span className="trace-name">{s.name}</span>
              <span className="trace-hint">{STAGE_HINT[s.name] ?? ""}</span>
            </div>
            {s.lines.map((l, i) => (
              <div key={i} className="trace-line">
                {l}
              </div>
            ))}
          </div>
        </li>
      ))}
    </ol>
  );
}
