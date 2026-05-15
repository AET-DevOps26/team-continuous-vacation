import { useShow, useUpdate, useDelete, useNavigation } from "@refinedev/core";
import type { Trip, Activity } from "@/providers/data-provider";
import type { components } from "@/lib/api-types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ArrowLeft,
  Clock,
  RefreshCw,
  Trash2,
  Sun,
  Sunrise,
  Sunset,
  Moon,
  CloudSun,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

type TimeBlock = components["schemas"]["TimeBlock"];

interface TimeBlockDisplay {
  label: string;
  icon: LucideIcon;
  color: string;
}

const TIME_BLOCK_CONFIG: Record<TimeBlock, TimeBlockDisplay> = {
  MORNING: { label: "Morning", icon: Sunrise, color: "bg-amber-50 border-amber-200" },
  NOON: { label: "Noon", icon: Sun, color: "bg-yellow-50 border-yellow-200" },
  AFTERNOON: { label: "Afternoon", icon: CloudSun, color: "bg-orange-50 border-orange-200" },
  EVENING: { label: "Evening", icon: Sunset, color: "bg-indigo-50 border-indigo-200" },
  NIGHT: { label: "Night", icon: Moon, color: "bg-slate-50 border-slate-200" },
};

function ActivityCard({
  activity,
  tripId,
  dayId,
}: {
  activity: Activity;
  tripId: string;
  dayId: string;
}) {
  const [editing, setEditing] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [regenerating, setRegenerating] = useState(false);
  const regenerateMutation = useUpdate();
  const { mutate: deleteActivity } = useDelete();

  const config = TIME_BLOCK_CONFIG[activity.timeBlock];
  const Icon = config.icon;

  const handleRegenerate = () => {
    if (!instruction.trim()) return;
    setRegenerating(true);
    regenerateMutation.mutate(
      {
        resource: "activities",
        id: activity.id,
        values: { instruction },
        meta: { tripId, dayId },
      },
      {
        onSuccess: () => {
          setEditing(false);
          setInstruction("");
        },
        onSettled: () => setRegenerating(false),
      }
    );
  };

  return (
    <Card className={`${config.color} border`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Icon className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs font-medium text-muted-foreground uppercase">
                {config.label}
              </span>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                {activity.durationMinutes} min
              </div>
            </div>
            <h4 className="font-semibold">{activity.title}</h4>
            <p className="text-sm text-muted-foreground mt-1">
              {activity.description}
            </p>
            {activity.tags && activity.tags.length > 0 && (
              <div className="flex gap-1 mt-2 flex-wrap">
                {activity.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag.toLowerCase().replace("_", " ")}
                  </Badge>
                ))}
              </div>
            )}
          </div>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setEditing(!editing)}
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-destructive"
              onClick={() =>
                deleteActivity({
                  resource: "activities",
                  id: activity.id,
                  meta: { tripId, dayId },
                })
              }
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
        {editing && (
          <div className="mt-3 flex gap-2">
            <Input
              placeholder="e.g. Make this an indoor activity"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleRegenerate()}
              disabled={regenerating}
            />
            <Button
              size="sm"
              onClick={handleRegenerate}
              disabled={regenerating || !instruction.trim()}
            >
              {regenerating ? "..." : "Go"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const TripShow: React.FC = () => {
  const { query } = useShow<Trip>({ resource: "trips" });
  const { list } = useNavigation();
  const trip = query?.data?.data;

  if (query?.isLoading) {
    return (
      <div className="p-8 text-center">
        <div className="animate-pulse text-muted-foreground">Loading trip...</div>
      </div>
    );
  }

  if (!trip) {
    return (
      <div className="p-8 text-center text-muted-foreground">Trip not found.</div>
    );
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <Button variant="ghost" className="gap-2 mb-4" onClick={() => list("trips")}>
          <ArrowLeft className="h-4 w-4" />
          Back to trips
        </Button>
        <div className="flex items-baseline gap-3">
          <h1 className="text-3xl font-bold">{trip.destination}</h1>
          <Badge variant="outline">{trip.vibe}</Badge>
        </div>
        <p className="text-muted-foreground mt-1">
          {trip.startDate} — {trip.endDate}
        </p>
      </div>

      <div className="space-y-8">
        {trip.schedule.days.map((day) => (
          <div key={day.id}>
            <div className="flex items-center gap-3 mb-3">
              <h2 className="text-xl font-semibold">Day {day.dayNumber}</h2>
              <span className="text-sm text-muted-foreground">{day.date}</span>
            </div>
            <div className="grid gap-3">
              {day.activities.map((activity) => (
                <ActivityCard
                  key={activity.id}
                  activity={activity}
                  tripId={trip.id}
                  dayId={day.id}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
