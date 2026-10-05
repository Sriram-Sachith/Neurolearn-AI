import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { DocumentItem, Note, Topic } from "../types";

export default function Notes() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [docId, setDocId] = useState("");
  const [notes, setNotes] = useState<Note[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Note | null>(null);

  useEffect(() => {
    api<DocumentItem[]>("/api/documents")
      .then((d) => {
        setDocs(d);
        if (d[0]) setDocId(d[0].id);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!docId) return;
    Promise.all([api<Note[]>(`/api/notes/${docId}`), api<Topic[]>(`/api/topics/${docId}`)])
      .then(([n, t]) => {
        setNotes(n);
        setTopics(t);
        setSelected(n[0] || null);
      })
      .catch((e) => setError(String(e)));
  }, [docId]);

  const parsed = selected
    ? (() => {
        try {
          return JSON.parse(selected.content);
        } catch {
          return { detailed_summary: selected.content };
        }
      })()
    : null;

  const exportNotes = () => {
    const blob = new Blob([JSON.stringify(notes, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "neurolearn-notes.json";
    a.click();
  };

  return (
    <div>
      <h1>Smart notes</h1>
      {error && <p className="error">{error}</p>}
      {docs.length === 0 ? (
        <div className="empty">Upload a document first.</div>
      ) : (
        <>
          <select value={docId} onChange={(e) => setDocId(e.target.value)}>
            {docs.map((d) => (
              <option key={d.id} value={d.id}>
                {d.original_name}
              </option>
            ))}
          </select>
          <button className="btn ghost" onClick={exportNotes}>
            Export JSON
          </button>
          <div className="split">
            <div className="card">
              {notes.map((n) => (
                <div key={n.id} className="list">
                  <li>
                    <button className="btn ghost" onClick={() => setSelected(n)}>
                      {n.title}
                    </button>
                    <span className="badge">p. {n.source_pages || "?"}</span>
                  </li>
                </div>
              ))}
              {parsed && (
                <div>
                  <h2>{selected?.title}</h2>
                  <p>{parsed.short_summary || parsed.detailed_summary}</p>
                  {parsed.key_points && (
                    <ul>
                      {parsed.key_points.map((k: string, i: number) => (
                        <li key={i}>{k}</li>
                      ))}
                    </ul>
                  )}
                  <p className="muted">Model: {selected?.model_name} · pages {selected?.source_pages}</p>
                </div>
              )}
            </div>
            <div>
              <div className="card">
                <h3>Concept map (cluster names are editable in data; not assumed academic truth)</h3>
                <div className="graph">
                  {topics.length === 0 && <p className="muted">No topics extracted.</p>}
                  {topics.map((t) => (
                    <div className="node" key={t.id}>
                      <strong>{t.topic_name}</strong>
                      <div className="muted">{t.keywords}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
