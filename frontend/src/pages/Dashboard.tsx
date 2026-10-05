import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";

type Summary = {
  documents: number;
  notes: number;
  flashcards: number;
  due_today: number;
  last_document: string | null;
  weak_points: { id: string; label: string; reason: string }[];
  recent_documents: { id: string; name: string; status: string }[];
};

export default function Dashboard() {
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Summary>("/api/dashboard/summary")
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);
  if (error) return <div className="error">{error}</div>;
  if (!data) return <div className="muted">Loading dashboard…</div>;
  return (
    <div>
      <div className="hero">
        <h1>Next action</h1>
        <p className="muted">
          {data.due_today > 0
            ? `You have ${data.due_today} cards due today. Keep the SM-2 queue moving.`
            : data.documents === 0
              ? "Upload a lecture PDF or notes to generate evidence-grounded flashcards."
              : `Last material: ${data.last_document}. Generate a quiz or review Model Lab results.`}
        </p>
        <Link to={data.due_today ? "/study" : "/materials"}>
          <button className="btn">{data.due_today ? "Open revision queue" : "Go to materials"}</button>
        </Link>
      </div>
      <div className="stats">
        <div className="card">
          <h3>Due flashcards</h3>
          <div className="num">{data.due_today}</div>
        </div>
        <div className="card">
          <h3>Total notes</h3>
          <div className="num">{data.notes}</div>
        </div>
        <div className="card">
          <h3>Flashcards</h3>
          <div className="num">{data.flashcards}</div>
        </div>
        <div className="card">
          <h3>Documents</h3>
          <div className="num">{data.documents}</div>
        </div>
      </div>
      <div className="row">
        <div className="card col">
          <h3>Weak points</h3>
          {data.weak_points.length === 0 ? (
            <p className="muted">No unverified cards yet.</p>
          ) : (
            <ul className="list">
              {data.weak_points.map((w) => (
                <li key={w.id}>
                  <span>{w.label}</span>
                  <Link to="/study">
                    <button className="btn">Practice</button>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="card col">
          <h3>Recent documents</h3>
          {data.recent_documents.length === 0 ? (
            <p className="muted">Nothing uploaded yet.</p>
          ) : (
            <ul className="list">
              {data.recent_documents.map((d) => (
                <li key={d.id}>
                  <span>{d.name}</span>
                  <span className="badge">{d.status}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
