import { useList, useDelete, useNavigation } from "@refinedev/core";
import type { TripSummary } from "@/providers/data-provider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MapPin, Calendar, Plus, Trash2 } from "lucide-react";

export const TripList: React.FC = () => {
  const { result, query } = useList<TripSummary>({ resource: "trips" });
  const { mutate: deleteTrip } = useDelete();
  const { show, create } = useNavigation();

  const trips = result.data ?? [];

  if (query.isLoading) {
    return (
      <div className="p-8 text-center">
        <div className="animate-pulse text-muted-foreground">Loading trips...</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My Trips</h1>
          <p className="text-muted-foreground">
            Plan and manage your travel itineraries.
          </p>
        </div>
        <Button onClick={() => create("trips")} className="gap-2">
          <Plus className="h-4 w-4" />
          New Trip
        </Button>
      </div>

      {trips.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <MapPin className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No trips yet</h3>
            <p className="text-muted-foreground mb-4">
              Create your first trip to get started.
            </p>
            <Button onClick={() => create("trips")} className="gap-2">
              <Plus className="h-4 w-4" />
              Plan a Trip
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {trips.map((trip) => (
            <Card
              key={trip.id}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => show("trips", trip.id)}
            >
              <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                <CardTitle className="text-lg font-semibold">
                  {trip.destination}
                </CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteTrip({ resource: "trips", id: trip.id });
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  <span>
                    {trip.startDate} — {trip.endDate}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
