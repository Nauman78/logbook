import json
from dataclasses import dataclass, field
from typing import Any

MAX_DRIVING_HOURS_PER_SHIFT = 11
WINDOW_HOURS = 14
BREAK_AFTER_DRIVING_HOURS = 8
BREAK_DURATION_HOURS = 0.5
OFF_DUTY_HOURS_BETWEEN_SHIFTS = 10
CYCLE_HOURS = 70
CYCLE_DAYS = 8
FUEL_STOP_MILES = 1000
FUEL_STOP_DURATION_HOURS = 0.5
PICKUP_DURATION_HOURS = 1
DROPOFF_DURATION_HOURS = 1


@dataclass
class Segment:
    type: str
    duration_minutes: int
    description: str = ""
    miles: float = 0

    def to_dict(self) -> dict[str, Any]:
        out = {"type": self.type, "duration_minutes": self.duration_minutes}
        if self.description:
            out["description"] = self.description
        if self.miles > 0:
            out["miles"] = round(self.miles, 2)
        return out


@dataclass
class DayLog:
    day_index: int
    segments: list[Segment] = field(default_factory=list)
    total_driving_minutes: int = 0
    total_on_duty_minutes: int = 0
    total_off_duty_minutes: int = 0
    cycle_hours_used_after: float = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "day_index": self.day_index,
            "segments": [s.to_dict() for s in self.segments],
            "total_driving_minutes": self.total_driving_minutes,
            "total_on_duty_minutes": self.total_on_duty_minutes,
            "total_off_duty_minutes": self.total_off_duty_minutes,
            "cycle_hours_used_after": round(self.cycle_hours_used_after, 2),
        }


def _build_driving_and_fuel_blocks(
    total_trip_miles: float,
    total_driving_hours: float,
) -> list[tuple[str, float, float]]:
    blocks: list[tuple[str, float, float]] = []
    if total_driving_hours <= 0 or total_trip_miles <= 0:
        return blocks
    mph = total_trip_miles / total_driving_hours
    miles_done = 0.0
    hours_done = 0.0
    while miles_done < total_trip_miles - 1e-6:
        miles_to_next_fuel = min(
            FUEL_STOP_MILES - (miles_done % FUEL_STOP_MILES),
            total_trip_miles - miles_done,
        )
        if miles_done > 0 and miles_done % FUEL_STOP_MILES < 1e-6:
            miles_to_next_fuel = min(FUEL_STOP_MILES, total_trip_miles - miles_done)
        segment_miles = min(miles_to_next_fuel, total_trip_miles - miles_done)
        if segment_miles <= 0:
            break
        segment_hours = segment_miles / mph
        blocks.append(("driving", segment_hours, segment_miles))
        miles_done += segment_miles
        hours_done += segment_hours
        if miles_done < total_trip_miles and miles_done >= 1e-6 and int(miles_done // FUEL_STOP_MILES) > int((miles_done - segment_miles) // FUEL_STOP_MILES):
            blocks.append(("fuel_stop", FUEL_STOP_DURATION_HOURS, 0))
    return blocks


def _hours_to_minutes(h: float) -> int:
    return int(round(h * 60))


def calculate_trip_logs(
    total_trip_miles: float,
    total_driving_hours: float,
    current_cycle_hours_used: float = 0,
) -> list[dict[str, Any]]:
    if total_trip_miles < 0 or total_driving_hours < 0:
        raise ValueError("total_trip_miles and total_driving_hours must be non-negative")
    if total_driving_hours > 0 and total_trip_miles <= 0:
        raise ValueError("total_trip_miles must be positive when total_driving_hours > 0")

    driving_fuel_blocks = _build_driving_and_fuel_blocks(total_trip_miles, total_driving_hours)
    block_index = 0
    day_index = 0
    cycle_hours = current_cycle_hours_used
    day_logs: list[DayLog] = []

    while block_index < len(driving_fuel_blocks) or day_index == 0:
        day = DayLog(day_index=day_index)
        driving_minutes_this_day = 0
        window_minutes_used = 0
        window_limit_minutes = _hours_to_minutes(WINDOW_HOURS)
        driving_limit_minutes = _hours_to_minutes(MAX_DRIVING_HOURS_PER_SHIFT)
        break_used_this_day = False

        if day_index > 0:
            off_min = _hours_to_minutes(OFF_DUTY_HOURS_BETWEEN_SHIFTS)
            day.segments.append(
                Segment("off_duty", off_min, "10 hr off between shifts")
            )
            day.total_off_duty_minutes += off_min

        if day_index == 0:
            day.segments.append(
                Segment("on_duty", _hours_to_minutes(PICKUP_DURATION_HOURS), "pickup")
            )
            day.total_on_duty_minutes += _hours_to_minutes(PICKUP_DURATION_HOURS)
            window_minutes_used += _hours_to_minutes(PICKUP_DURATION_HOURS)

        while block_index < len(driving_fuel_blocks):
            kind, block_hours, block_miles = driving_fuel_blocks[block_index]
            block_min = _hours_to_minutes(block_hours)

            if kind == "fuel_stop":
                if window_minutes_used + block_min > window_limit_minutes:
                    break
                day.segments.append(
                    Segment("fuel_stop", block_min, "fuel stop (30 min)")
                )
                day.total_on_duty_minutes += block_min
                window_minutes_used += block_min
                block_index += 1
                continue

            assert kind == "driving"
            driving_remaining_today = driving_limit_minutes - driving_minutes_this_day
            if driving_remaining_today <= 0:
                break
            if not break_used_this_day and driving_minutes_this_day >= _hours_to_minutes(BREAK_AFTER_DRIVING_HOURS):
                day.segments.append(
                    Segment("break", _hours_to_minutes(BREAK_DURATION_HOURS), "30 min break after 8 hr driving")
                )
                day.total_on_duty_minutes += _hours_to_minutes(BREAK_DURATION_HOURS)
                window_minutes_used += _hours_to_minutes(BREAK_DURATION_HOURS)
                break_used_this_day = True

            if not break_used_this_day and driving_minutes_this_day + block_min > _hours_to_minutes(BREAK_AFTER_DRIVING_HOURS):
                before_break = _hours_to_minutes(BREAK_AFTER_DRIVING_HOURS) - driving_minutes_this_day
                if before_break > 0:
                    before_break_miles = block_miles * (before_break / block_min) if block_min else 0
                    day.segments.append(Segment("driving", before_break, "driving", before_break_miles))
                    driving_minutes_this_day += before_break
                    window_minutes_used += before_break
                    day.total_driving_minutes += before_break
                    block_miles -= before_break_miles
                    block_hours -= before_break / 60
                    block_min = _hours_to_minutes(block_hours)
                    driving_fuel_blocks[block_index] = ("driving", block_hours, block_miles)
                day.segments.append(
                    Segment("break", _hours_to_minutes(BREAK_DURATION_HOURS), "30 min break after 8 hr driving")
                )
                day.total_on_duty_minutes += _hours_to_minutes(BREAK_DURATION_HOURS)
                window_minutes_used += _hours_to_minutes(BREAK_DURATION_HOURS)
                break_used_this_day = True
                continue

            chunk_min = min(block_min, driving_remaining_today, window_limit_minutes - window_minutes_used)
            if chunk_min <= 0:
                break
            chunk_hours = chunk_min / 60
            chunk_miles = block_miles * (chunk_min / block_min) if block_min else 0
            day.segments.append(Segment("driving", chunk_min, "driving", chunk_miles))
            driving_minutes_this_day += chunk_min
            window_minutes_used += chunk_min
            day.total_driving_minutes += chunk_min

            if chunk_min >= block_min:
                block_index += 1
            else:
                remaining_hours = block_hours - chunk_hours
                remaining_miles = block_miles - chunk_miles
                driving_fuel_blocks[block_index] = ("driving", remaining_hours, remaining_miles)

        remaining_blocks = block_index < len(driving_fuel_blocks)
        is_last_day = not remaining_blocks

        if is_last_day:
            day.segments.append(
                Segment("on_duty", _hours_to_minutes(DROPOFF_DURATION_HOURS), "dropoff")
            )
            day.total_on_duty_minutes += _hours_to_minutes(DROPOFF_DURATION_HOURS)

        day_total_on_duty = day.total_driving_minutes + day.total_on_duty_minutes
        cycle_hours += day_total_on_duty / 60
        day.cycle_hours_used_after = cycle_hours
        day_logs.append(day)
        day_index += 1

        if not remaining_blocks:
            break

    return [d.to_dict() for d in day_logs]


def validate_daily_logs_limits(daily_logs: list[dict[str, Any]]) -> None:
    max_drive_min = int(MAX_DRIVING_HOURS_PER_SHIFT * 60)
    max_window_min = int(WINDOW_HOURS * 60)
    break_required_after_min = int(BREAK_AFTER_DRIVING_HOURS * 60)

    for day in daily_logs:
        day_idx = day.get("day_index", 0)
        drive = day.get("total_driving_minutes", 0)
        on_duty = day.get("total_on_duty_minutes", 0)
        window_min = drive + on_duty

        if drive > max_drive_min:
            raise ValueError(
                f"Day {day_idx + 1} exceeds 11-hour driving limit: {drive} minutes driving. "
                "FMCSA property-carrying rule allows max 11 hours driving per shift."
            )
        if window_min > max_window_min:
            raise ValueError(
                f"Day {day_idx + 1} exceeds 14-hour on-duty window: {window_min} minutes total. "
                "FMCSA rule requires all driving and on-duty work within 14 hours of first on-duty."
            )

        if drive >= break_required_after_min:
            segments = day.get("segments") or []
            has_break = any(seg.get("type") == "break" for seg in segments)
            if not has_break:
                raise ValueError(
                    f"Day {day_idx + 1} requires a 30-minute break after 8 hours of driving. "
                    f"Driving total is {drive} minutes with no break segment."
                )


def calculate_trip_logs_json(
    total_trip_miles: float,
    total_driving_hours: float,
    current_cycle_hours_used: float = 0,
    indent: int | None = 2,
) -> str:
    logs = calculate_trip_logs(
        total_trip_miles=total_trip_miles,
        total_driving_hours=total_driving_hours,
        current_cycle_hours_used=current_cycle_hours_used,
    )
    return json.dumps(logs, indent=indent)
