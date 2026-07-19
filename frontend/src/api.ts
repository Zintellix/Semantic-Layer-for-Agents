import type {
  AskResult, Health, SignalResult, ActionCard, DomainInfo, ObjectsView,
} from "./types";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export const api = {
  health: () => get<Health>("/api/health"),
  domains: () => get<{ domains: DomainInfo[] }>("/api/domains"),
  objects: (domain: string) => get<ObjectsView>(`/api/objects?domain=${domain}`),
  ask: (question: string, domain: string, use_llm: boolean) =>
    post<AskResult>("/api/ask", { question, domain, use_llm }),
  signal: (domain: string, key: string) =>
    post<SignalResult>("/api/signal", { domain, key }),
  approve: (domain: string, action_id: string) =>
    post<ActionCard>("/api/approve", { domain, action_id }),
};
