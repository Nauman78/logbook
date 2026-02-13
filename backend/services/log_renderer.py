"""
Render FMCSA-style daily log sheets from day log data.
Uses a blank sheet image or creates one with official layout proportions.
"""
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

DEFAULT_BLANK_PATH = "/mnt/data/blank-paper-log.png"
DATE_COL_WIDTH = 72
LOCATION_COL_WIDTH = 96
HOUR_COL_WIDTH = 36
GRID_HOURS = 24
DUTY_ROWS = ("Off Duty", "Sleeper Berth", "Driving", "On Duty")
STATUS_ROW_INDEX = {"off_duty": 0, "sleeper_berth": 1, "driving": 2, "on_duty": 3, "break": 3, "fuel_stop": 3}
ROW_HEIGHT = 44
HEADER_HEIGHT = 56
MARGIN_TOP = 24
MARGIN_LEFT = 24
FONT_SIZE = 10
GRID_LINE = 1
HOUR_TICK_INTERVAL = 4


def _blank_path() -> Path:
    env_path = os.environ.get("FMCSA_BLANK_LOG_IMAGE")
    if env_path:
        return Path(env_path)
    return Path(DEFAULT_BLANK_PATH)


def _create_blank_sheet() -> Image.Image:
    total_width = MARGIN_LEFT + DATE_COL_WIDTH + LOCATION_COL_WIDTH + GRID_HOURS * HOUR_COL_WIDTH
    total_height = MARGIN_TOP + HEADER_HEIGHT + len(DUTY_ROWS) * ROW_HEIGHT
    img = Image.new("RGB", (total_width, total_height), color=(255, 255, 255))
    return img


def _load_base_image(path: Path) -> Image.Image:
    if path.is_file():
        return Image.open(path).convert("RGB")
    return _create_blank_sheet()


def _get_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Try common system font paths (Linux, macOS, Windows)
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "DejaVuSans.ttf",
        "Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, FONT_SIZE)
        except (OSError, TypeError):
            continue
    return ImageFont.load_default()


def _draw_grid(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    left = MARGIN_LEFT + DATE_COL_WIDTH + LOCATION_COL_WIDTH
    top = MARGIN_TOP + HEADER_HEIGHT
    grid_width = GRID_HOURS * HOUR_COL_WIDTH
    grid_height = len(DUTY_ROWS) * ROW_HEIGHT
    black = (0, 0, 0)
    gray = (200, 200, 200)

    for row in range(len(DUTY_ROWS) + 1):
        y = top + row * ROW_HEIGHT
        draw.line([(left, y), (left + grid_width, y)], fill=black, width=GRID_LINE)
    for col in range(GRID_HOURS + 1):
        x = left + col * HOUR_COL_WIDTH
        draw.line([(x, top), (x, top + grid_height)], fill=gray if col % HOUR_TICK_INTERVAL else black, width=GRID_LINE)
    for col in range(0, GRID_HOURS + 1, HOUR_TICK_INTERVAL):
        x = left + col * HOUR_COL_WIDTH
        draw.line([(x, top), (x, top + grid_height)], fill=black, width=GRID_LINE)


def _draw_duty_labels(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> None:
    left = MARGIN_LEFT
    top = MARGIN_TOP + HEADER_HEIGHT
    for i, label in enumerate(DUTY_ROWS):
        y = top + i * ROW_HEIGHT + (ROW_HEIGHT - FONT_SIZE) // 2
        draw.text((left + 8, y), label, fill=(0, 0, 0), font=font)


def _draw_time_headers(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> None:
    left = MARGIN_LEFT + DATE_COL_WIDTH + LOCATION_COL_WIDTH
    top = MARGIN_TOP + 8
    for hour in range(0, GRID_HOURS, 2):
        x = left + hour * HOUR_COL_WIDTH + HOUR_COL_WIDTH // 2 - 6
        draw.text((x, top), f"{hour:02d}", fill=(0, 0, 0), font=font)


def _draw_segment(
    draw: ImageDraw.ImageDraw,
    row_index: int,
    start_minutes: int,
    duration_minutes: int,
    left: int,
    top: int,
    fill_color: tuple[int, int, int],
) -> None:
    x1 = left + (start_minutes / 60) * HOUR_COL_WIDTH
    x2 = left + ((start_minutes + duration_minutes) / 60) * HOUR_COL_WIDTH
    y1 = top + row_index * ROW_HEIGHT + 2
    y2 = top + (row_index + 1) * ROW_HEIGHT - 2
    draw.rectangle([x1, y1, x2, y2], fill=fill_color, outline=(0, 0, 0), width=1)


def _draw_location_marker(
    draw: ImageDraw.ImageDraw,
    minute_offset: int,
    location_text: str,
    left: int,
    top: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    loc_x = MARGIN_LEFT + DATE_COL_WIDTH + 4
    grid_left = left
    x_center = grid_left + (minute_offset / 60) * HOUR_COL_WIDTH + (HOUR_COL_WIDTH / 2)
    y = max(0, top - 14)
    draw.line([(x_center, top), (x_center, y)], fill=(80, 80, 80), width=1)
    draw.text((loc_x, y), location_text[:20], fill=(0, 0, 0), font=font)


def _render_one_day(
    day_data: dict[str, Any],
    output_path: Path,
    blank_path: Path,
    day_label: str | None = None,
) -> Path:
    img = _load_base_image(blank_path)
    draw = ImageDraw.Draw(img)
    font = _get_font()
    width, height = img.size
    left = MARGIN_LEFT + DATE_COL_WIDTH + LOCATION_COL_WIDTH
    top = MARGIN_TOP + HEADER_HEIGHT

    _draw_grid(draw, width, height)
    _draw_duty_labels(draw, font)
    _draw_time_headers(draw, font)

    if day_label:
        title = f"Daily Log Sheet — {day_label}"
        draw.text((MARGIN_LEFT + 8, MARGIN_TOP + 8), title, fill=(0, 0, 0), font=font)

    segments = day_data.get("segments") or []
    colors = {
        "off_duty": (230, 230, 230),
        "sleeper_berth": (200, 220, 255),
        "driving": (255, 220, 180),
        "on_duty": (255, 240, 200),
        "break": (255, 240, 200),
        "fuel_stop": (255, 240, 200),
    }
    minute_cursor = 0
    location_index = 0
    locations = ("Origin", "Pickup", "En route", "Fuel stop", "Break", "Dropoff", "Destination")

    for seg in segments:
        seg_type = seg.get("type", "on_duty")
        duration_minutes = int(seg.get("duration_minutes", 0))
        if duration_minutes <= 0:
            continue
        row_index = STATUS_ROW_INDEX.get(seg_type, 3)
        color = colors.get(seg_type, colors["on_duty"])
        _draw_segment(draw, row_index, minute_cursor, duration_minutes, left, top, color)
        loc_label = seg.get("description") or locations[min(location_index % len(locations), len(locations) - 1)]
        _draw_location_marker(draw, minute_cursor, loc_label, left, top, font)
        location_index += 1
        minute_cursor += duration_minutes

    os.makedirs(output_path.parent, exist_ok=True)
    img.save(str(output_path), "PNG")
    return output_path


def render_daily_logs(
    daily_logs: list[dict[str, Any]],
    output_dir: str | Path,
    blank_sheet_path: str | Path | None = None,
    date_prefix: str | None = None,
) -> list[str]:
    """
    Draw duty status, time grid, and location markers for each day.
    Returns list of saved image file paths (one per day).
    """
    output_dir = Path(output_dir)
    blank_path = Path(blank_sheet_path) if blank_sheet_path else _blank_path()
    paths: list[str] = []

    for i, day_data in enumerate(daily_logs):
        day_index = day_data.get("day_index", i)
        day_label = f"Day {day_index + 1}"
        if date_prefix:
            day_label = f"{date_prefix} - {day_label}"
        filename = f"log_day_{day_index + 1}.png"
        out_path = output_dir / filename
        _render_one_day(day_data, out_path, blank_path, day_label=day_label)
        paths.append(str(out_path.resolve()))

    return paths
