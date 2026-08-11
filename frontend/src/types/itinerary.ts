export interface ActivitySchema {
  title: string;
  description: string;
  approximate_time: string;
  location?: string | null;
}

export interface DaySchema {
  date: string;
  activities: ActivitySchema[];
}

export interface ItinerarySchema {
  trip_summary: string;
  days: DaySchema[];
}
