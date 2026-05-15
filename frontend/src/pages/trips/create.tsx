import { useCreate, useNavigation } from "@refinedev/core";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Loader2 } from "lucide-react";
import type { Trip } from "@/providers/data-provider";

const tripSchema = z.object({
  destination: z.string().min(1, "Destination is required"),
  startDate: z.string().min(1, "Start date is required"),
  endDate: z.string().min(1, "End date is required"),
  vibe: z.string().min(1, "Vibe is required"),
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
  const { show } = useNavigation();
  const [isPending, setIsPending] = useState(false);

  const form = useForm<TripFormValues>({
    resolver: zodResolver(tripSchema),
    defaultValues: { destination: "", startDate: "", endDate: "", vibe: "" },
  });

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
    <div className="p-8 max-w-2xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Plan a New Trip</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
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

              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="startDate"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Start Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="endDate"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>End Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
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
                      <div className="space-y-3">
                        <div className="flex flex-wrap gap-2">
                          {VIBE_OPTIONS.map((vibe) => (
                            <Button
                              key={vibe}
                              type="button"
                              variant={field.value === vibe ? "default" : "outline"}
                              size="sm"
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
                        />
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button type="submit" className="w-full" disabled={isPending}>
                {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isPending ? "Generating itinerary..." : "Generate Trip"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
};
