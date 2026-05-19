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

const TIME_BLOCK_ORDER: TimeBlock[] = ["MORNING", "NOON", "AFTERNOON", "EVENING", "NIGHT"];

interface TimeBlockDisplay {
  label: string;
  icon: LucideIcon;
  color: string;
}

const TIME_BLOCK_CONFIG: Record<TimeBlock, TimeBlockDisplay> = {
  MORNING: { label: "Morning", icon: Sunrise, color: "bg-amber-100/70 border-amber-300 dark:bg-amber-900/30 dark:border-amber-600/40" },
  NOON: { label: "Noon", icon: Sun, color: "bg-sky-100/70 border-sky-300 dark:bg-sky-900/30 dark:border-sky-600/40" },
  AFTERNOON: { label: "Afternoon", icon: CloudSun, color: "bg-orange-100/70 border-orange-300 dark:bg-orange-900/30 dark:border-orange-600/40" },
  EVENING: { label: "Evening", icon: Sunset, color: "bg-violet-100/70 border-violet-300 dark:bg-violet-900/30 dark:border-violet-600/40" },
  NIGHT: { label: "Night", icon: Moon, color: "bg-slate-200/70 border-slate-300 dark:bg-slate-800/40 dark:border-slate-600/40" },
};

function sortActivities(activities: Activity[]): Activity[] {
  return [...activities].sort(
    (a, b) => TIME_BLOCK_ORDER.indexOf(a.timeBlock) - TIME_BLOCK_ORDER.indexOf(b.timeBlock)
  );
}

function ActivityCard({
  activity,
  tripId,
  dayId,
  onMutate,
}: {
  activity: Activity;
  tripId: string;
  dayId: string;
  onMutate: () => void;
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
        invalidates: [],
      },
      {
        onSuccess: () => {
          setEditing(false);
          setInstruction("");
          onMutate();
        },
        onSettled: () => setRegenerating(false),
      }
    );
  };

  const handleDelete = () => {
    deleteActivity(
      {
        resource: "activities",
        id: activity.id,
        meta: { tripId, dayId },
        invalidates: [],
      },
      { onSuccess: onMutate }
    );
  };

  return (
    <Card className={`${config.color} border transition-colors`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5">
              <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {config.label}
              </span>
              <span className="text-xs text-muted-foreground/70">·</span>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                {activity.durationMinutes} min
              </div>
            </div>
            <h4 className="font-semibold leading-tight">{activity.title}</h4>
            <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
              {activity.description}
            </p>
            {activity.tags && activity.tags.length > 0 && (
              <div className="flex gap-1.5 mt-2.5 flex-wrap">
                {activity.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs font-normal">
                    {tag.toLowerCase().replace("_", " ")}
                  </Badge>
                ))}
              </div>
            )}
          </div>
          <div className="flex flex-col gap-1 shrink-0">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              title="Regenerate activity"
              onClick={() => setEditing(!editing)}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-destructive"
              title="Delete activity"
              onClick={handleDelete}
            >
              <Trash2 className="h-4 w-4" />
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
              className="text-sm"
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

  const refetchTrip = () => {
    query.refetch();
  };

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

  const totalDays = trip.schedule.days.length;

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <Button variant="ghost" size="sm" className="gap-1.5 -ml-2 mb-3" onClick={() => list("trips")}>
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">{trip.destination}</h1>
          <Badge variant="outline" className="w-fit">{trip.vibe}</Badge>
        </div>
        <p className="text-sm text-muted-foreground mt-1.5">
          {trip.startDate} — {trip.endDate} · {totalDays} {totalDays === 1 ? "day" : "days"}
        </p>
      </div>

      {/* Schedule Grid */}
      <div className="grid gap-6 lg:gap-8 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
        {trip.schedule.days.map((day) => (
          <div key={day.id} className="space-y-3">
            <div className="flex items-baseline gap-2 pb-2 border-b">
              <h2 className="text-lg font-semibold">Day {day.dayNumber}</h2>
              <span className="text-xs text-muted-foreground">{day.date}</span>
            </div>
            <div className="space-y-2.5">
              {sortActivities(day.activities).map((activity) => (
                <ActivityCard
                  key={activity.id}
                  activity={activity}
                  tripId={trip.id}
                  dayId={day.id}
                  onMutate={refetchTrip}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
