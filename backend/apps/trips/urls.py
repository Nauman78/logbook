from django.urls import path
from apps.trips.views import PlanTripView, TripLogDetailView, TripLogListView, PlacesSearchView

urlpatterns = [
    path("plan-trip/", PlanTripView.as_view()),
    path("trip-logs/", TripLogListView.as_view()),
    path("trip-logs/<int:pk>/", TripLogDetailView.as_view()),
    path("places-search/", PlacesSearchView.as_view()),
]
