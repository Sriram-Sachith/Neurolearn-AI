import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../services/api";
import type { TokenPayload } from "../types";

export default function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("demo@neurolearn.local");
  const [password, setPassword] = useState("demo1234");
  const [name, setName] = useState("Demo Student");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const body = mode === "login" ? { email, password } : { email, password, name };
      const res = await api<TokenPayload>(path, { method: "POST", body: JSON.stringify(body) });
      setToken(res.access_token);
      nav("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  };

  return (
    <div className="auth">
      <form className="card auth-card" onSubmit={submit}>
        <h2>NeuroLearn AI</h2>
        <p className="muted">Local-first study platform. Demo account is pre-seeded.</p>
        {mode === "register" && (
          <>
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </>
        )}
        <label>Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} />
        <label>Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <p className="error">{error}</p>}
        <button className="btn" type="submit">
          {mode === "login" ? "Sign in" : "Create account"}
        </button>
        <p>
          <button type="button" className="btn ghost" onClick={() => setMode(mode === "login" ? "register" : "login")}>
            {mode === "login" ? "Need an account?" : "Have an account?"}
          </button>
        </p>
      </form>
    </div>
  );
}
