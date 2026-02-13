from django.db import models


class TripLog(models.Model):

    trip_id = models.CharField(max_length=64, unique=True, db_index=True)
    route_instructions = models.JSONField(default=list)
    eld_log_entries = models.JSONField(default=list)
    daily_log_urls = models.JSONField(default=list)
    total_distance_miles = models.FloatField(null=True, blank=True)
    total_duration_hours = models.FloatField(null=True, blank=True)
    trip_start = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
