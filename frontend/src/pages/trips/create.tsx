import { useCreate, useNavigation } from "@refinedev/core";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { ArrowLeft, CalendarIcon, Loader2, Sparkles } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import type { Trip } from "@/providers/data-provider";

const MAX_TRIP_DAYS = 14;

const todayISO = () => toISO(new Date());

const toISO = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
    date.getDate()
  ).padStart(2, "0")}`;

const parseDate = (value: string) => {
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
};

const formatDisplay = (value: string) => {
  const date = parseDate(value);
  return date
    ? date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })
    : "Pick a date";
};

const tripSchema = z
  .object({
    destination: z.string().min(1, "Destination is required"),
    startDate: z.string().min(1, "Start date is required"),
    endDate: z.string().min(1, "End date is required"),
    vibe: z.string().min(1, "Vibe is required"),
  })
  .superRefine((values, ctx) => {
    const start = parseDate(values.startDate);
    const end = parseDate(values.endDate);
    if (!start || !end) return;

    const today = parseDate(todayISO())!;

    if (start < today) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["startDate"],
        message: "Start date cannot be in the past",
      });
    }

    if (end < start) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["endDate"],
        message: "End date must be on or after the start date",
      });
      return;
    }

    const dayMs = 1000 * 60 * 60 * 24;
    const totalDays = Math.round((end.getTime() - start.getTime()) / dayMs) + 1;
    if (totalDays > MAX_TRIP_DAYS) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["endDate"],
        message: `A trip can span at most ${MAX_TRIP_DAYS} days`,
      });
    }
  });

type TripFormValues = z.infer<typeof tripSchema>;

const VIBE_OPTIONS = [
  "Sporty and active",
  "Foodie",
  "Historic and cultural",
  "Relaxing",
  "Adventurous",
  "Party",
  "Family friendly",
];

export const TripCreate: React.FC = () => {
  const mutation = useCreate<Trip>();
  const { show, list } = useNavigation();
  const [isPending, setIsPending] = useState(false);

  const form = useForm<TripFormValues>({
    resolver: zodResolver(tripSchema),
    defaultValues: { destination: "", startDate: "", endDate: "", vibe: "" },
  });

  const today = todayISO();
  const startDate = form.watch("startDate");
  const endMin = startDate || today;
  const endMax = (() => {
    const start = parseDate(startDate);
    if (!start) return undefined;
    const max = new Date(start.getTime() + (MAX_TRIP_DAYS - 1) * 24 * 60 * 60 * 1000);
    return max.toISOString().split("T")[0];
  })();

  const onSubmit = (values: TripFormValues) => {
    setIsPending(true);
    mutation.mutate(
      { resource: "trips", values },
      {
        onSuccess: ({ data }) => {
          show("trips", data.id);
        },
        onSettled: () => setIsPending(false),
      }
    );
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-2xl mx-auto">
      <Button variant="ghost" size="sm" className="gap-1.5 -ml-2 mb-4" onClick={() => list("trips")}>
        <ArrowLeft className="h-4 w-4" />
        Back
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Plan a New Trip</CardTitle>
          <CardDescription>
            Describe where and when, pick a vibe, and AI generates your itinerary.
            Trips start today or later and can span up to {MAX_TRIP_DAYS} days.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
              <FormField
                control={form.control}
                name="destination"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Destination</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Munich, Beach vacation, Tokyo" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-2 gap-3">
                <FormField
                  control={form.control}
                  name="startDate"
                  render={({ field }) => (
                    <FormItem className="flex flex-col">
                      <FormLabel>Start Date</FormLabel>
                      <Popover>
                        <PopoverTrigger asChild>
                          <FormControl>
                            <Button
                              type="button"
                              variant="outline"
                              className={cn(
                                "justify-start text-left font-normal",
                                !field.value && "text-muted-foreground"
                              )}
                            >
                              <CalendarIcon className="mr-2 h-4 w-4" />
                              {field.value ? formatDisplay(field.value) : "Pick a date"}
                            </Button>
                          </FormControl>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0" align="start">
                          <Calendar
                            mode="single"
                            weekStartsOn={1}
                            selected={parseDate(field.value) ?? undefined}
                            onSelect={(date) => field.onChange(date ? toISO(date) : "")}
                            disabled={(date) => date < parseDate(today)!}
                            initialFocus
                          />
                        </PopoverContent>
                      </Popover>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="endDate"
                  render={({ field }) => (
                    <FormItem className="flex flex-col">
                      <FormLabel>End Date</FormLabel>
                      <Popover>
                        <PopoverTrigger asChild>
                          <FormControl>
                            <Button
                              type="button"
                              variant="outline"
                              className={cn(
                                "justify-start text-left font-normal",
                                !field.value && "text-muted-foreground"
                              )}
                            >
                              <CalendarIcon className="mr-2 h-4 w-4" />
                              {field.value ? formatDisplay(field.value) : "Pick a date"}
                            </Button>
                          </FormControl>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0" align="start">
                          <Calendar
                            mode="single"
                            weekStartsOn={1}
                            defaultMonth={parseDate(endMin) ?? undefined}
                            selected={parseDate(field.value) ?? undefined}
                            onSelect={(date) => field.onChange(date ? toISO(date) : "")}
                            disabled={(date) =>
                              date < parseDate(endMin)! ||
                              (endMax ? date > parseDate(endMax)! : false)
                            }
                            initialFocus
                          />
                        </PopoverContent>
                      </Popover>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="vibe"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Vibe</FormLabel>
                    <FormControl>
                      <div className="space-y-2.5">
                        <div className="flex flex-wrap gap-2">
                          {VIBE_OPTIONS.map((vibe) => (
                            <Button
                              key={vibe}
                              type="button"
                              variant={field.value === vibe ? "default" : "outline"}
                              size="sm"
                              className="text-xs"
                              onClick={() => field.onChange(vibe)}
                            >
                              {vibe}
                            </Button>
                          ))}
                        </div>
                        <Input
                          placeholder="Or type your own vibe..."
                          value={VIBE_OPTIONS.includes(field.value) ? "" : field.value}
                          onChange={(e) => field.onChange(e.target.value)}
                          className="text-sm"
                        />
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button type="submit" className="w-full gap-2" disabled={isPending}>
                {isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating itinerary...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Generate Trip
                  </>
                )}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
};
