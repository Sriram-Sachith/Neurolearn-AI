import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { DocumentItem, Flashcard, Quiz, RevisionCard } from "../types";

export default function Study() {
  const [tab, setTab] = useState<"revise" | "cards" | "quiz">("revise");
  const [queue, setQueue] = useState<RevisionCard[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [docId, setDocId] = useState("");
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [show, setShow] = useState(false);
  const [idx, setIdx] = useState(0);
  const [evidence, setEvidence] = useState<Flashcard | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<string>("");
  const [error, setError] = useState("");

  const loadQueue = () => api<RevisionCard[]>("/api/revision/today").then(setQueue);
  useEffect(() => {
    loadQueue().catch((e) => setError(String(e)));
    api<DocumentItem[]>("/api/documents").then((d) => {
      setDocs(d);
      if (d[0]) setDocId(d[0].id);
    });
  }, []);

  useEffect(() => {
    if (!docId) return;
    api<Flashcard[]>(`/api/flashcards/${docId}`).then(setCards);
    api<Quiz[]>(`/api/quizzes/${docId}`).then(setQuizzes);
  }, [docId]);

  const current = queue[idx];
  const rate = async (rating: string) => {
    if (!current) return;
    await api("/api/revision/submit", { method: "POST", body: JSON.stringify({ card_id: current.card_id, rating }) });
    setShow(false);
    const next = await api<RevisionCard[]>("/api/revision/today");
    setQueue(next);
    setIdx(0);
  };

  const submitQuiz = async (quiz: Quiz) => {
    const r = await api<{ score: number; correct: number; total: number }>(`/api/quizzes/submit`, {
      method: "POST",
      body: JSON.stringify({ quiz_id: quiz.id, answers }),
    });
    setResult(`Score ${r.correct}/${r.total} (${Math.round(r.score * 100)}%). Mastery uses SM-2 history, not this number alone.`);
  };

  return (
    <div>
      <h1>Flashcards & quizzes</h1>
      <p>
        <button className="btn ghost" onClick={() => setTab("revise")}>
          Revision queue
        </button>{" "}
        <button className="btn ghost" onClick={() => setTab("cards")}>
          All cards
        </button>{" "}
        <button className="btn ghost" onClick={() => setTab("quiz")}>
          Quizzes
        </button>
      </p>
      {error && <p className="error">{error}</p>}
      {tab === "revise" && (
        <div className="card">
          {!current ? (
            <div className="empty">No cards due. Upload material or come back tomorrow.</div>
          ) : (
            <>
              <div className="flash">{show ? current.answer : current.question}</div>
              <p className="muted">
                {current.difficulty} · {current.support_status} · SM-2 n={current.n} EF={current.ef.toFixed(2)}
              </p>
              <button className="btn ghost" onClick={() => setShow(!show)}>
                {show ? "Hide answer" : "Show answer"}
              </button>
              <div className="ratings">
                <button className="btn bad" onClick={() => rate("again")}>
                  Again
                </button>
                <button className="btn warn" onClick={() => rate("hard")}>
                  Hard
                </button>
                <button className="btn" onClick={() => rate("good")}>
                  Good
                </button>
                <button className="btn good" onClick={() => rate("easy")}>
                  Easy
                </button>
              </div>
            </>
          )}
        </div>
      )}
      {tab === "cards" && (
        <div>
          <select value={docId} onChange={(e) => setDocId(e.target.value)}>
            {docs.map((d) => (
              <option key={d.id} value={d.id}>
                {d.original_name}
              </option>
            ))}
          </select>
          <div className="split">
            <div className="card">
              {cards.map((c) => (
                <div key={c.id} className="list">
                  <li>
                    <span>{c.question}</span>
                    <span>
                      <span className={`badge ${c.support_status}`}>{c.support_status}</span>{" "}
                      <button className="btn ghost" onClick={() => setEvidence(c)}>
                        Source p.{c.source_pages || "?"}
                      </button>
                    </span>
                  </li>
                </div>
              ))}
            </div>
            <div className="card">
              <h3>Source passage</h3>
              {!evidence && <p className="muted">Select a card to inspect evidence. Similarity is retrieval, not proof.</p>}
              {evidence?.evidence?.map((e) => (
                <div key={e.chunk_id}>
                  <p>
                    Page {e.page_number} · score {e.score.toFixed(3)} · {e.support_status}
                  </p>
                  <p className="passage">{e.passage}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      {tab === "quiz" && (
        <div className="card">
          {quizzes.length === 0 && <div className="empty">No quiz generated yet.</div>}
          {quizzes.map((q) => (
            <div key={q.id}>
              <h3>{q.title}</h3>
              {q.items.map((it) => (
                <div key={it.id}>
                  <p>
                    {it.question} <span className="badge">{it.qtype}</span>
                  </p>
                  {it.qtype === "mcq" ? (
                    <select onChange={(e) => setAnswers({ ...answers, [it.id]: e.target.value })}>
                      <option value="">Select</option>
                      {it.options.map((o) => (
                        <option key={o} value={o}>
                          {o}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input onChange={(e) => setAnswers({ ...answers, [it.id]: e.target.value })} />
                  )}
                </div>
              ))}
              <button className="btn" onClick={() => submitQuiz(q)}>
                Submit
              </button>
              {result && <p>{result}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
