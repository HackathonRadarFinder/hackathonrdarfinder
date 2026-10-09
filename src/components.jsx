import React from "react";
import { Link } from "react-router-dom";
import { Bookmark, CalendarDays, MapPin, Award } from "lucide-react";
import { useUser } from "./UserContext";

export const logoText = (event) =>
  event.organizer.split(" ").map((x) => x[0]).slice(0, 2).join("");

export function StatusBadge({ status }) {
  return (
    <span className={`status ${status.toLowerCase()}`}>
      <span className="status-dot" />{status}
    </span>
  );
}

export function EventCard({ event }) {
  const { isSaved, toggleSaved } = useUser();
  const saved = isSaved(event.id);
  return (
    <article className="event-card">
      <div className={`event-logo ${event.color}`}>{logoText(event)}</div>
      <div className="event-card-body">
        <div className="card-top">
          <StatusBadge status={event.status} />
          <button
            className={saved ? "save-btn saved" : "save-btn"}
            onClick={() => toggleSaved(event.id)}
            title={saved ? "Remove from saved" : "Save event"}
          >
            <Bookmark size={17} fill={saved ? "currentColor" : "none"} />
          </button>
        </div>
        <Link to={`/event/${event.id}`} className="event-title">{event.title}</Link>
        <p className="organizer-name">{event.organizer}</p>
        <div className="event-meta">
          <span><CalendarDays size={15} />{event.date}</span>
          <span><MapPin size={15} />{event.location}</span>
          <span><Award size={15} />{event.prize}</span>
        </div>
        <div className="tags">{event.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
      </div>
    </article>
  );
}
