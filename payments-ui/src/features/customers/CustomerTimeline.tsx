import { Card } from "../../components/ui";
import { formatDate } from "../../lib/format";
import "./CustomerTimeline.css";

export interface TimelineEvent {
  id: string;
  date: string;
  title: string;
  kind: "contract" | "subscription" | "payment";
}

export function CustomerTimeline({ events }: { events: TimelineEvent[] }) {
  return (
    <Card>
      <ul className="timeline">
        {events.map((event) => (
          <li key={event.id}>
            <div className="timeline-date">{formatDate(event.date)}</div>
            <div className="timeline-title">{event.title}</div>
          </li>
        ))}
        {events.length === 0 && <li className="state-message">No timeline events yet.</li>}
      </ul>
    </Card>
  );
}
