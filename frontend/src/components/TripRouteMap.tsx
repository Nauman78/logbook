import { useEffect, useMemo } from "react";
import { MapContainer, Polyline, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import type { LatLngExpression } from "leaflet";
import L from "leaflet";
import polyline from "@mapbox/polyline";
import type { PlanTripResponse, RoutePolyline } from "../api";

export type Point = { lat: number; lng: number };

type Props = {
  encodedPolyline?: RoutePolyline | null;
  current?: Point | null;
  pickup?: Point | null;
  dropoff?: Point | null;
  stops?: PlanTripResponse["stops"];
};

type StopWithPosition = PlanTripResponse["stops"][number] & { position: [number, number] };

const DEFAULT_CENTER: LatLngExpression = [40.69959172666929, -103.04816033981959];

function getBoundsCenter(points: LatLngExpression[]): LatLngExpression {
  if (!points.length) return DEFAULT_CENTER;
  let minLat = Infinity;
  let maxLat = -Infinity;
  let minLng = Infinity;
  let maxLng = -Infinity;
  for (const p of points) {
    const [lat, lng] = p as [number, number];
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
    if (lng < minLng) minLng = lng;
    if (lng > maxLng) maxLng = lng;
  }
  return [(minLat + maxLat) / 2, (minLng + maxLng) / 2];
}

function getStopColor(type: string) {
  if (type === "pickup") return "#6366f1";
  if (type === "dropoff") return "#f97316";
  if (type === "fuel_stop") return "#22c55e";
  if (type === "break") return "#eab308";
  return "#38bdf8";
}

function MapFitBounds({
  path,
  current,
  pickup,
  dropoff
}: {
  path: LatLngExpression[];
  current?: Point | null;
  pickup?: Point | null;
  dropoff?: Point | null;
}) {
  const map = useMap();
  useEffect(() => {
    const points: [number, number][] = path.map((p) => {
      const [lat, lng] = p as [number, number];
      return [lat, lng];
    });
    if (current) points.push([current.lat, current.lng]);
    if (pickup) points.push([pickup.lat, pickup.lng]);
    if (dropoff) points.push([dropoff.lat, dropoff.lng]);
    if (points.length === 0) return;
    const bounds = L.latLngBounds(points);
    map.fitBounds(bounds, { padding: [24, 24], maxZoom: 14 });
  }, [map, path, current, pickup, dropoff]);
  return null;
}

export function TripRouteMap({ encodedPolyline, current, pickup, dropoff, stops }: Props) {
  const path = useMemo<LatLngExpression[]>(() => {
    if (encodedPolyline == null) return [];
    if (Array.isArray(encodedPolyline)) {
      return encodedPolyline.map(([lng, lat]) => [lat, lng] as LatLngExpression);
    }
    try {
      return polyline.decode(encodedPolyline) as LatLngExpression[];
    } catch {
      return [];
    }
  }, [encodedPolyline]);

  const stopMarkers = useMemo<StopWithPosition[]>(() => {
    if (!stops || !stops.length || path.length < 2) return [];
    return stops.map((stop, index) => {
      const t = (index + 1) / (stops.length + 1);
      const idx = Math.min(path.length - 1, Math.floor(t * (path.length - 1)));
      const [lat, lng] = path[idx] as [number, number];
      return { ...stop, position: [lat, lng] };
    });
  }, [stops, path]);

  const center = useMemo(() => {
    const points: LatLngExpression[] = [...path];
    if (current) points.push([current.lat, current.lng]);
    if (pickup) points.push([pickup.lat, pickup.lng]);
    if (dropoff) points.push([dropoff.lat, dropoff.lng]);
    return points.length ? getBoundsCenter(points) : DEFAULT_CENTER;
  }, [path, current, pickup, dropoff]);

  return (
    <div className="map-panel">
      <MapContainer
        center={center}
        zoom={4}
        scrollWheelZoom={false}
        className="map"
      >
        <MapFitBounds path={path} current={current} pickup={pickup} dropoff={dropoff} />
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {path.length > 1 && (
          <Polyline positions={path} pathOptions={{ color: "#38bdf8", weight: 3 }} />
        )}
        {current && (
          <CircleMarker
            center={[current.lat, current.lng]}
            radius={6}
            pathOptions={{ color: "#22c55e" }}
          >
            <Popup>Current location</Popup>
          </CircleMarker>
        )}
        {pickup && (
          <CircleMarker
            center={[pickup.lat, pickup.lng]}
            radius={6}
            pathOptions={{ color: "#6366f1" }}
          >
            <Popup>Pickup</Popup>
          </CircleMarker>
        )}
        {dropoff && (
          <CircleMarker
            center={[dropoff.lat, dropoff.lng]}
            radius={6}
            pathOptions={{ color: "#f97316" }}
          >
            <Popup>Dropoff</Popup>
          </CircleMarker>
        )}
        {stopMarkers.map((stop, idx) => (
          <CircleMarker
            key={`${stop.type}-${idx}-${stop.position[0]}-${stop.position[1]}`}
            center={stop.position}
            radius={5}
            pathOptions={{ color: getStopColor(stop.type) }}
          >
            <Popup>
              <div className="popup">
                <div className="popup-title">{stop.type.replace("_", " ")}</div>
                {stop.description && <div>{stop.description}</div>}
                <div>{stop.duration_minutes} min</div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      <p className="map-legend">
        <span className="dot current" /> Current - &nbsp;
        <span className="dot pickup" /> Pickup - &nbsp;
        <span className="dot dropoff" /> Dropoff - &nbsp;
        <span className="dot fuel" /> Fuel stop - &nbsp;
        <span className="dot break" /> Rest break
      </p>
    </div>
  );
}

export default TripRouteMap;

