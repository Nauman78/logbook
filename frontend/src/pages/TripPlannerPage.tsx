import { useState } from "react";
import { planTrip, type PlanTripRequest, type PlanTripResponse } from "../api";
import TripRouteMap, { type Point } from "../components/TripRouteMap";
import AddressSearchInput from "../components/AddressSearchInput";

function TripPlannerPage() {
  const [currentPoint, setCurrentPoint] = useState<Point | null>(null);
  const [pickupPoint, setPickupPoint] = useState<Point | null>(null);
  const [dropoffPoint, setDropoffPoint] = useState<Point | null>(null);
  const [cycleUsed, setCycleUsed] = useState("0");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PlanTripResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPoint || !pickupPoint || !dropoffPoint) {
      setError("Select current, pickup, and dropoff locations from the address search.");
      return;
    }
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const body: PlanTripRequest = {
        current_location: { lat: currentPoint.lat, lng: currentPoint.lng },
        pickup_location: { lat: pickupPoint.lat, lng: pickupPoint.lng },
        dropoff_location: { lat: dropoffPoint.lat, lng: dropoffPoint.lng },
        current_cycle_used: Number(cycleUsed || 0)
      };
      const data = await planTrip(body);
      setResult(data);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: string } }; message?: string };
      setError(err?.response?.data?.error ?? err?.message ?? "Failed to plan trip");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Trip Planner</h2>
      </div>
      {error && <div className="alert error">{error}</div>}

      <form className="form-grid two-col" onSubmit={handleSubmit}>
        <AddressSearchInput
          label="Current location"
          placeholder="Search address or place"
          onLocationSelected={setCurrentPoint}
        />
        <AddressSearchInput
          label="Pickup location"
          placeholder="Search address or place"
          onLocationSelected={setPickupPoint}
        />
        <AddressSearchInput
          label="Dropoff location"
          placeholder="Search address or place"
          onLocationSelected={setDropoffPoint}
        />
        <div className="field">
          <label>Current Cycle Used (hours)</label>
          <input
            type="number"
            min={0}
            step="0.1"
            value={cycleUsed}
            onChange={(e) => setCycleUsed(e.target.value)}
          />
        </div>
        <button type="submit" className="btn-primary align-end" disabled={loading}>
          {loading ? "Planning…" : "Plan Trip"}
        </button>
      </form>

      <div className="grid-2 map-layout">
        <div>
          {result ? (
            <>
              <h3>Summary</h3>
              <p>
                Distance: <strong>{result.total_distance_miles.toFixed(1)} mi</strong>
              </p>
              <p>
                Duration: <strong>{result.total_duration_hours.toFixed(1)} hr</strong>
              </p>
              <h3>Route Instructions</h3>
              <ol className="simple-list">
                {result.route_instructions.map((ins) => (
                  <li key={ins.sequence}>
                    <span className="badge small">{ins.type}</span> {ins.instruction}
                  </li>
                ))}
              </ol>
            </>
          ) : (
            <p>Fill out the form and click &quot;Plan Trip&quot; to see results.</p>
          )}
        </div>

        <TripRouteMap
          encodedPolyline={result?.route_polyline ?? null}
          current={currentPoint}
          pickup={pickupPoint}
          dropoff={dropoffPoint}
          stops={result?.stops ?? []}
        />
      </div>
    </section>
  );
}

export default TripPlannerPage;
