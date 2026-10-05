import { useEffect, useState } from "react";
import { api } from "../services/api";

export default function Settings() {
  const [providers, setProviders] = useState<any[]>([]);
  const [mastery, setMastery] = useState<any>(null);
  useEffect(() => {
    api<any[]>("/api/evaluation/providers").then(setProviders);
    api("/api/learning/mastery").then(setMastery);
  }, []);
  return (
    <div>
      <h1>Settings</h1>
      <div className="card">
        <h3>Privacy</h3>
        <p className="muted">
          Documents stay on this machine. Default LLM path is local Ollama or an on-device heuristic extractor. No
          cloud LLM is required. Document text is not written to application logs.
        </p>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Providers</h3>
        <ul>
          {providers.map((p) => (
            <li key={p.name}>
              {p.name} · {p.family} · {p.available ? "available" : "offline"}
            </li>
          ))}
        </ul>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Mastery vs quiz accuracy</h3>
        <pre className="passage">{JSON.stringify(mastery, null, 2)}</pre>
      </div>
    </div>
  );
}
