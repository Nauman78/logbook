import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import TripPlannerPage from "./pages/TripPlannerPage";
import LogsViewerPage from "./pages/LogsViewerPage";

function App() {
  return (
    <div className="app-root">
      <header className="app-header">
        <h1>Logbook Trip Planner</h1>
        <p className="subtitle">Plan trips on a map and view generated ELD logs.</p>
        <nav className="nav-links">
          <NavLink to="/plan" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            Trip Planner
          </NavLink>
          <NavLink to="/logs" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            Logs Viewer
          </NavLink>
        </nav>
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/plan" replace />} />
          <Route path="/plan" element={<TripPlannerPage />} />
          <Route path="/logs" element={<LogsViewerPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
