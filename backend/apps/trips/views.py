import os
import uuid
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.trips.models import TripLog
from services.hos_calculator import CYCLE_HOURS, calculate_trip_logs, validate_daily_logs_limits
from services.log_renderer import render_daily_logs
from services.routing_service import get_route

STATUS_LABELS = {
    "off_duty": "Off Duty",
    "sleeper_berth": "Sleeper Berth",
    "driving": "Driving",
    "on_duty": "On Duty",
    "pickup": "Pickup",
    "dropoff": "Dropoff",
    "fuel_stop": "Fuel Stop",
    "break": "Rest Break",
}


def _build_route_instructions(daily_logs: list[dict]) -> list[dict]:
    instructions = []
    seq = 1
    for day in daily_logs:
        for seg in day.get("segments") or []:
            seg_type = seg.get("type", "on_duty")
            dur = seg.get("duration_minutes", 0)
            desc = seg.get("description", "")
            label = STATUS_LABELS.get(seg_type, seg_type.replace("_", " ").title())
            if desc and desc != label.lower():
                text = f"{label} — {desc} ({dur} min)"
            else:
                text = f"{label} ({dur} min)"
            instructions.append({"sequence": seq, "instruction": text, "type": seg_type, "duration_minutes": dur})
            seq += 1
    return instructions


def _build_eld_log_entries(daily_logs: list[dict], trip_start) -> list[dict]:
    entries = []
    cursor = trip_start
    for day in daily_logs:
        day_index = day.get("day_index", 0)
        for seg in day.get("segments") or []:
            dur_min = seg.get("duration_minutes", 0)
            start_time = cursor
            end_time = cursor + timedelta(minutes=dur_min)
            entries.append({
                "day_index": day_index,
                "status": seg.get("type", "on_duty"),
                "status_label": STATUS_LABELS.get(seg.get("type", "on_duty"), seg.get("type", "on_duty").replace("_", " ").title()),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": dur_min,
                "description": seg.get("description", ""),
            })
            cursor = end_time
    return entries


def _build_stops(daily_logs: list[dict]) -> list[dict]:
    stop_types = {"pickup", "dropoff", "fuel_stop", "break"}
    stops = []
    for day in daily_logs:
        for seg in day.get("segments") or []:
            if seg.get("type") not in stop_types:
                continue
            stops.append({
                "type": seg["type"],
                "duration_minutes": seg.get("duration_minutes", 0),
                "description": seg.get("description", ""),
            })
    return stops


class PlanTripView(APIView):
    def post(self, request: Request) -> Response:
        try:
            body = request.data
            current = body.get("current_location") or {}
            pickup = body.get("pickup_location") or {}
            dropoff = body.get("dropoff_location") or {}
            current_cycle_used = float(body.get("current_cycle_used") or 0)
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid JSON: current_location, pickup_location, dropoff_location (lat, lng), current_cycle_used"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for name, point in [("current_location", current), ("pickup_location", pickup), ("dropoff_location", dropoff)]:
            if not isinstance(point, dict) or "lat" not in point or "lng" not in point:
                return Response(
                    {"error": f"{name} must be {{ lat, lng }}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            origin = (float(current["lng"]), float(current["lat"]))
            pickup_coord = (float(pickup["lng"]), float(pickup["lat"]))
            dropoff_coord = (float(dropoff["lng"]), float(dropoff["lat"]))
        except (TypeError, ValueError):
            return Response({"error": "lat and lng must be numbers"}, status=status.HTTP_400_BAD_REQUEST)

        waypoints = []
        for stop in (body.get("stops") or []):
            if not isinstance(stop, dict) or "lat" not in stop or "lng" not in stop:
                continue
            try:
                waypoints.append((float(stop["lng"]), float(stop["lat"])))
            except (TypeError, ValueError):
                continue

        try:
            route = get_route(origin, pickup_coord, dropoff_coord, waypoints=waypoints if waypoints else None)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Routing failed: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        distance_miles = route["distance_miles"]
        duration_hours = route["duration_hours"]
        polyline = route["polyline"]

        try:
            daily_logs = calculate_trip_logs(
                total_trip_miles=distance_miles,
                total_driving_hours=duration_hours,
                current_cycle_hours_used=current_cycle_used,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_daily_logs_limits(daily_logs)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if daily_logs:
            cycle_after = daily_logs[-1].get("cycle_hours_used_after", 0)
            if cycle_after > CYCLE_HOURS:
                available = max(0, CYCLE_HOURS - current_cycle_used)
                return Response(
                    {
                        "error": (
                            f"Trip would exceed 70-hour / 8-day cycle. "
                            f"Current cycle used: {current_cycle_used:.1f} hr. "
                            f"After this trip: {cycle_after:.1f} hr (limit {CYCLE_HOURS} hr). "
                            "Take a 34-hour restart before starting this trip, or reduce current cycle usage."
                        ),
                        "current_cycle_used": round(current_cycle_used, 2),
                        "cycle_hours_after": round(cycle_after, 2),
                        "cycle_limit": CYCLE_HOURS,
                        "available_hours": round(available, 2),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        trip_id = uuid.uuid4().hex
        output_dir = settings.MEDIA_ROOT / "trip_logs" / trip_id
        try:
            file_paths = render_daily_logs(daily_logs, output_dir=output_dir)
        except Exception as e:
            return Response({"error": f"Log render failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        base = request.build_absolute_uri(settings.MEDIA_URL.rstrip("/") + "/")
        daily_log_urls = [base + "trip_logs/" + trip_id + "/" + os.path.basename(p) for p in file_paths]

        stops = _build_stops(daily_logs)
        trip_start = timezone.now()
        route_instructions = _build_route_instructions(daily_logs)
        eld_log_entries = _build_eld_log_entries(daily_logs, trip_start)

        trip_log = TripLog.objects.create(
            trip_id=trip_id,
            route_instructions=route_instructions,
            eld_log_entries=eld_log_entries,
            daily_log_urls=daily_log_urls,
            total_distance_miles=distance_miles,
            total_duration_hours=duration_hours,
            trip_start=trip_start,
        )

        payload = {
            "route_polyline": polyline,
            "total_distance_miles": distance_miles,
            "total_duration_hours": duration_hours,
            "stops": stops,
            "daily_logs": daily_log_urls,
            "route_instructions": route_instructions,
            "eld_log_entries": eld_log_entries,
            "trip_start": trip_start.isoformat(),
            "trip_log_id": trip_log.id,
        }
        return Response(payload, status=status.HTTP_200_OK)


class TripLogListView(APIView):
    """List saved trip logs (ELD data), newest first."""

    def get(self, request: Request) -> Response:
        logs = TripLog.objects.all()[:100]
        data = [
            {
                "id": log.id,
                "trip_id": log.trip_id,
                "total_distance_miles": log.total_distance_miles,
                "total_duration_hours": log.total_duration_hours,
                "trip_start": log.trip_start.isoformat() if log.trip_start else None,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
        return Response(data)


class TripLogDetailView(APIView):
    """Get one saved trip log (full ELD data for /logs page)."""

    def get(self, request: Request, pk: int) -> Response:
        log = TripLog.objects.filter(pk=pk).first()
        if not log:
            return Response(status=status.HTTP_404_NOT_FOUND)
        data = {
            "route_instructions": log.route_instructions,
            "eld_log_entries": log.eld_log_entries,
            "daily_logs": log.daily_log_urls,
            "total_distance_miles": log.total_distance_miles,
            "total_duration_hours": log.total_duration_hours,
            "trip_start": log.trip_start.isoformat() if log.trip_start else None,
        }
        return Response(data)


class PlacesSearchView(APIView):
    """Proxy for OpenRouteService geocoding API to avoid CORS and keep API key secure."""

    def get(self, request: Request) -> Response:
        query = request.query_params.get("q", "").strip()
        if not query or len(query) < 3:
            return Response({"features": []})

        api_key = os.environ.get("OPENROUTE_SERVICE_API_KEY", "").strip()
        if not api_key:
            return Response(
                {"error": "Places API key not configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            url = "https://api.openrouteservice.org/geocode/search"
            resp = requests.get(
                url,
                params={"api_key": api_key, "text": query, "size": 5},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return Response(data)
        except requests.RequestException as e:
            return Response(
                {"error": f"Places API error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
