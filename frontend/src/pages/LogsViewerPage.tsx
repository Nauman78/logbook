import { useCallback, useEffect, useState } from "react";
import { getTripLog, listTripLogs, type TripLogDetail, type TripLogSummary } from "../api";
import { normalizeImageUrl } from "../utils/function";

function LogsViewerPage() {
  const [logs, setLogs] = useState<TripLogSummary[]>([]);
  const [selected, setSelected] = useState<TripLogDetail | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageErrors, setImageErrors] = useState<Set<string>>(new Set());

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listTripLogs();
      setLogs(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load trip logs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const openLog = useCallback((id: number) => {
    setSelected(null);
    setSelectedId(id);
    setError(null);
    getTripLog(id)
      .then(setSelected)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load log")
      );
  }, []);

  const dailyLogs = selected?.daily_logs ?? [];
  const totalDays = dailyLogs.length;

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Logs Viewer</h2>
        <button type="button" className="btn-secondary" onClick={fetchLogs}>
          Refresh
        </button>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="grid-2 logs-viewer-layout">
        <div className="logs-sidebar">
          <h3>Recent Logs</h3>
          {loading && <div>Loading…</div>}
          {!loading && logs.length === 0 && <div>No logs yet.</div>}
          <ul className="simple-list">
            {logs.map((log) => (
              <li key={log.id}>
                <button
                  type="button"
                  className={selectedId === log.id ? "link-button active" : "link-button"}
                  onClick={() => openLog(log.id)}
                >
                  #{log.id} — {log.total_distance_miles.toFixed(1)} mi /{" "}
                  {log.total_duration_hours.toFixed(1)} hr
                </button>
              </li>
            ))}
          </ul>
          {selected && (
            <div className="stack log-meta">
              <p>
                Distance: <strong>{selected.total_distance_miles.toFixed(1)} mi</strong>
              </p>
              <p>
                Duration: <strong>{selected.total_duration_hours.toFixed(1)} hr</strong>
              </p>
              <ol className="simple-list">
                {selected.route_instructions.map((ins, idx) => (
                  <li key={idx}>
                    <span className="badge small">{ins.type}</span> {ins.instruction}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
        <div className="log-sheet-viewer">
          {!selected && (
            <p className="viewer-placeholder">Select a log to view log sheet images.</p>
          )}
          {selected && totalDays === 0 && (
            <p className="viewer-placeholder">No log sheet images for this trip.</p>
          )}
          {selected && totalDays > 0 && (
            <>
              <div className="log-sheet-scroll">
                {dailyLogs.map((url, idx) => {
                  const normalizedUrl = normalizeImageUrl(url);
                  const hasError = imageErrors.has(url);
                  return (
                    <div key={url} className="log-sheet-day-block">
                      <h4 className="log-sheet-day-heading">Day {idx + 1} of {totalDays}</h4>
                      {hasError ? (
                        <div className="image-error">
                          <p>Failed to load image</p>
                        </div>
                      ) : (
                        <img
                          src={normalizedUrl}
                          alt={`Log sheet Day ${idx + 1}`}
                          className="log-sheet-image"
                          onError={() => {
                            setImageErrors((prev) => new Set(prev).add(url));
                          }}
                          loading="lazy"
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

export default LogsViewerPage;
