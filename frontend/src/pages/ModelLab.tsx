import { useEffect, useState } from "react";
import { Bar, BarChart, Legend, PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../services/api";

type Bundle = {
  missing: string[];
  experiments: Record<string, any>;
};

export default function ModelLab() {
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Bundle>("/api/evaluation/compare")
      .then(setBundle)
      .catch((e) => setError(String(e)));
    api<any[]>("/api/evaluation/runs").then(setRuns).catch(() => {});
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!bundle) return <p className="muted">Loading measured results…</p>;

  const retrieval = bundle.experiments.retrieval;
  const clustering = bundle.experiments.clustering;
  const performance = bundle.experiments.performance;
  const flash = bundle.experiments.flashcard_quality;
  const llm = bundle.experiments.llm_comparison;

  const radarData = (retrieval?.models || []).map((m: any) => ({
    name: m.name,
    recall5: m.recall_at_5,
    mrr: m.mrr,
  }));

  return (
    <div>
      <h1>Model Lab</h1>
      <p className="muted">
        Only numbers written by experiment scripts are shown. Missing files mean that experiment has not been run on this machine yet — never a placeholder accuracy.
      </p>
      {bundle.missing.length > 0 && (
        <div className="card">
          <h3>Not yet measured</h3>
          <ul>
            {bundle.missing.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
          <p className="muted">Run: python experiments/run_all.py</p>
        </div>
      )}
      {retrieval && (
        <div className="card">
          <h3>Experiment C — retrieval (Recall@5, MRR)</h3>
          <p className="muted">{retrieval.notes}</p>
          <table className="table">
            <thead>
              <tr>
                <th>Backend</th>
                <th>Recall@5</th>
                <th>MRR</th>
                <th>Latency ms (median)</th>
              </tr>
            </thead>
            <tbody>
              {(retrieval.models || []).map((m: any) => (
                <tr key={m.name}>
                  <td>{m.name}</td>
                  <td>{m.recall_at_5}</td>
                  <td>{m.mrr}</td>
                  <td>{m.latency_ms_median}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {radarData.length > 0 && (
            <div style={{ height: 280 }}>
              <ResponsiveContainer>
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="name" />
                  <Radar dataKey="recall5" name="Recall@5" stroke="#7c9cff" fill="#7c9cff" fillOpacity={0.3} />
                  <Radar dataKey="mrr" name="MRR" stroke="#3dd68c" fill="#3dd68c" fillOpacity={0.2} />
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
      {performance && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Experiment E — local pipeline timing</h3>
          <p className="muted">{performance.notes}</p>
          <div style={{ height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={performance.trials_summary || []}>
                <XAxis dataKey="stage" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="median_ms" fill="#7c9cff" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
      {clustering && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Experiment F — K-Means silhouette</h3>
          <p>
            Best K={clustering.best_k} · silhouette={clustering.best_silhouette} · n_docs={clustering.n_documents}
          </p>
          <p className="muted">{clustering.notes}</p>
        </div>
      )}
      {flash && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Experiment B — flashcard pipeline stats</h3>
          <p className="muted">{flash.notes}</p>
          <pre className="passage">{JSON.stringify(flash.metrics, null, 2)}</pre>
        </div>
      )}
      {llm && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Experiment A — LLM comparison</h3>
          <p className="muted">{llm.notes}</p>
          <pre className="passage">{JSON.stringify(llm.runs, null, 2)}</pre>
        </div>
      )}
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Live model_runs from this database</h3>
        {runs.length === 0 ? (
          <p className="muted">No pipeline runs recorded yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Task</th>
                <th>Latency ms</th>
                <th>Output chars</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td>{r.model_name}</td>
                  <td>{r.task}</td>
                  <td>{r.latency_ms?.toFixed?.(2) ?? r.latency_ms}</td>
                  <td>{r.output_chars}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
