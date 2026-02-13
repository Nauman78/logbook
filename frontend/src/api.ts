import axios from "axios";
import { env } from "./config/env";

const client = axios.create({
  baseURL: env.API_BASE_URL,
  timeout: 20000,
});

export interface PlanTripRequest {
  current_location: { lat: number; lng: number };
  pickup_location: { lat: number; lng: number };
  dropoff_location: { lat: number; lng: number };
  current_cycle_used: number;
  stops?: { lat: number; lng: number }[];
}

export type RoutePolyline = [number, number][] | string;

export interface PlanTripResponse {
  route_polyline: RoutePolyline;
  total_distance_miles: number;
  total_duration_hours: number;
  stops: { type: string; duration_minutes: number; description: string }[];
  daily_logs: string[];
  route_instructions: {
    sequence: number;
    instruction: string;
    type: string;
    duration_minutes: number;
  }[];
  eld_log_entries: {
    day_index: number;
    status: string;
    status_label: string;
    start_time: string;
    end_time: string;
    duration_minutes: number;
    description: string;
  }[];
  trip_start: string;
  trip_log_id: number;
}

export interface TripLogSummary {
  id: number;
  trip_id: string;
  total_distance_miles: number;
  total_duration_hours: number;
  trip_start: string | null;
  created_at: string;
}

export interface TripLogDetail {
  route_instructions: PlanTripResponse["route_instructions"];
  eld_log_entries: PlanTripResponse["eld_log_entries"];
  daily_logs: string[];
  total_distance_miles: number;
  total_duration_hours: number;
  trip_start: string | null;
}

export async function planTrip(body: PlanTripRequest) {
  const res = await client.post<PlanTripResponse>("/plan-trip/", body);
  return res.data;
}

export async function listTripLogs() {
  const res = await client.get<TripLogSummary[]>("/trip-logs/");
  return res.data;
}

export async function getTripLog(id: number) {
  const res = await client.get<TripLogDetail>(`/trip-logs/${id}/`);
  return res.data;
}
