import { useEffect, useState } from "react";
import { api } from "../services/api";
import { useJobPoll } from "../hooks/useJobPoll";
import type { DocumentItem, Job } from "../types";

export default function Materials() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [model, setModel] = useState("");
  const [providers, setProviders] = useState<{ name: string; available: boolean }[]>([]);
  const job = useJobPoll(jobId, () => refresh());

  const refresh = () => api<DocumentItem[]>("/api/documents").then(setDocs).catch((e) => setError(String(e)));
  useEffect(() => {
    refresh();
    api<{ name: string; available: boolean }[]>("/api/evaluation/providers").then(setProviders).catch(() => {});
  }, []);

  const onFile = async (f: File | null) => {
    if (!f) return;
    setError("");
    const body = new FormData();
    body.append("file", f);
    const q = model ? `?model_name=${encodeURIComponent(model)}` : "";
    try {
      const j = await api<Job>(`/api/documents/upload${q}`, { method: "POST", body });
      setJobId(j.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "upload failed");
    }
  };

  return (
    <div>
      <h1>My materials</h1>
      <p className="muted">PDF, PPTX, DOCX, TXT, or scanned images. Max 50 MB. Processing runs as a background job.</p>
      <div className="card">
        <label>Model for generation</label>
        <select value={model} onChange={(e) => setModel(e.target.value)}>
          <option value="">Auto (Ollama if available, else heuristic)</option>
          {providers.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name} {p.available ? "" : "(offline)"}
            </option>
          ))}
        </select>
        <input type="file" onChange={(e) => onFile(e.target.files?.[0] || null)} />
        {job && (
          <div>
            <div>
              Job {job.status} · {job.progress}%
            </div>
            <div className="progress">
              <div style={{ width: `${job.progress}%` }} />
            </div>
            {job.error_message && <p className="error">{job.error_message}</p>}
          </div>
        )}
        {error && <p className="error">{error}</p>}
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        {docs.length === 0 ? (
          <div className="empty">No documents yet. Upload a lecture to start.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Size</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>{d.original_name}</td>
                  <td>
                    <span className="badge">{d.status}</span>
                  </td>
                  <td>{Math.round(d.size_bytes / 1024)} KB</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
