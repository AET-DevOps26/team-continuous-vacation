import { useList, useDelete, useNavigation } from "@refinedev/core";
import type { TripSummary } from "@/providers/data-provider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MapPin, Calendar, Plus, Trash2, Plane } from "lucide-react";

export const TripList: React.FC = () => {
  const { result, query } = useList<TripSummary>({ resource: "trips" });
  const { mutate: deleteTrip } = useDelete();
  const { show, create } = useNavigation();

  const trips = result.data ?? [];

  if (query.isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-muted-foreground">Loading trips...</div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">My Trips</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Plan and manage your travel itineraries.
          </p>
        </div>
        <Button onClick={() => create("trips")} className="gap-2">
          <Plus className="h-4 w-4" />
          <span className="hidden sm:inline">New Trip</span>
        </Button>
      </div>

      {trips.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <div className="rounded-full bg-muted p-4 mb-4">
              <Plane className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-medium mb-1">No trips yet</h3>
            <p className="text-sm text-muted-foreground mb-5 text-center max-w-sm">
              Create your first trip and let AI generate a personalized itinerary.
            </p>
            <Button onClick={() => create("trips")} className="gap-2">
              <Plus className="h-4 w-4" />
              Plan a Trip
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">
          {trips.map((trip) => (
            <Card
              key={trip.id}
              className="cursor-pointer group hover:border-primary/50 transition-colors"
              onClick={() => show("trips", trip.id)}
            >
              <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                <CardTitle className="text-base font-semibold leading-tight pr-2">
                  {trip.destination}
                </CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteTrip({ resource: "trips", id: trip.id });
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Calendar className="h-3.5 w-3.5 shrink-0" />
                  <span>{trip.startDate} — {trip.endDate}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1.5">
                  <MapPin className="h-3.5 w-3.5 shrink-0" />
                  <span>Click to view schedule</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
