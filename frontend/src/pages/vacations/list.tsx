import React from "react";
import { useTable, HttpError } from "@refinedev/core";
import { Vacation } from "@/interfaces.ts";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

export const VacationList: React.FC = () => {
  const { result } = useTable<Vacation, HttpError>({
    pagination: { mode: "off" },
  });

  const vacations = result?.data ?? [];

  if (result.isLoading) {
    return <div className="p-8 text-center animate-pulse">Loading trips...</div>;
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">My Vacations</h1>
        <p className="text-muted-foreground">
          View and manage your upcoming travel itineraries.
        </p>
      </div>

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[250px]">Trip Name</TableHead>
              <TableHead>Destination</TableHead>
              <TableHead>Start Date</TableHead>
              <TableHead>End Date</TableHead>
              <TableHead className="text-right">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {vacations.map((vacation) => (
              <TableRow key={vacation.id}>
                <TableCell className="font-medium">{vacation.name}</TableCell>
                <TableCell>
                  <Badge variant="secondary" className="font-normal">
                    📍 {vacation.destination}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {new Date(vacation.startTime).toLocaleDateString()}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {new Date(vacation.endTime).toLocaleDateString()}
                </TableCell>
                <TableCell className="text-right">
                  <Badge variant="outline" className="text-green-600 border-green-200 bg-green-50">
                    Confirmed
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};
