// frontend/src/interfaces.ts

export interface Vacation {
  id: number;
  name: string;
  destination: string;
  startTime: string; // ISO 8601 format (e.g., "2026-12-20T09:00:00")
  endTime: string;
}
