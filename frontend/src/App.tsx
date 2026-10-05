import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { getToken, clearToken } from "./services/api";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Materials from "./pages/Materials";
import Notes from "./pages/Notes";
import Study from "./pages/Study";
import ModelLab from "./pages/ModelLab";
import Settings from "./pages/Settings";

function Shell() {
  const nav = useNavigate();
  const logout = () => {
    clearToken();
    nav("/login");
  };
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">NeuroLearn AI</div>
        <div className="tag">Upload. Understand. Remember. Revise.</div>
        <nav className="nav">
          <NavLink to="/" end>
            Home
          </NavLink>
          <NavLink to="/materials">Knowledge</NavLink>
          <NavLink to="/notes">Notes</NavLink>
          <NavLink to="/study">Flashcards / Quizzes</NavLink>
          <NavLink to="/lab">Model Lab</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
        <button className="btn ghost" style={{ marginTop: 24, width: "100%" }} onClick={logout}>
          Sign out
        </button>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/materials" element={<Materials />} />
          <Route path="/notes" element={<Notes />} />
          <Route path="/study" element={<Study />} />
          <Route path="/lab" element={<ModelLab />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}

function Private({ children }: { children: JSX.Element }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <Private>
            <Shell />
          </Private>
        }
      />
    </Routes>
  );
}
