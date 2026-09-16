import { Card } from "../../components/ui";
import { formatDate } from "../../lib/format";
import type { TimelineEvent } from "../../api/types";
import "./CustomerTimeline.css";

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
      </ul>
    </Card>
  );
}
