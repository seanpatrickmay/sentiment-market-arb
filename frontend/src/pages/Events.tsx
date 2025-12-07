import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Card } from "../components/Card";
import type { SportsEvent } from "../types";

export default function Events() {
  const [events, setEvents] = useState<SportsEvent[]>([]);
  const [sport, setSport] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const query = sport ? `?sport=${sport}` : "";
      const data = await api.get<SportsEvent[]>(`/sports-events${query}`);
      setEvents(data);
      setError(null);
    } catch (e: any) {
      setError(e?.message || "Failed to load events");
    }
  };

  useEffect(() => {
    load();
  }, [sport]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <label className="text-sm text-slate-700">
          Sport:
          <select
            className="ml-2 rounded border border-slate-300 px-2 py-1 text-sm"
            value={sport}
            onChange={(e) => setSport(e.target.value)}
          >
            <option value="">All</option>
            <option value="NBA">NBA</option>
            <option value="NFL">NFL</option>
            <option value="MLB">MLB</option>
            <option value="NHL">NHL</option>
          </select>
        </label>
      </div>
      {error && <div className="rounded bg-rose-50 p-2 text-sm text-rose-800">{error}</div>}
      <Card title={`Events (${events.length})`}>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-600">
                <th className="px-2 py-2">ID</th>
                <th className="px-2 py-2">Sport</th>
                <th className="px-2 py-2">Matchup</th>
                <th className="px-2 py-2">Start</th>
                <th className="px-2 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {events.map((ev) => (
                <tr key={ev.id} className="border-b border-slate-100">
                  <td className="px-2 py-2">
                    <Link className="text-slate-900 underline" to={`/events/${ev.id}`}>
                      {ev.id}
                    </Link>
                  </td>
                  <td className="px-2 py-2">{ev.sport}</td>
                  <td className="px-2 py-2">
                    {ev.home_team} vs {ev.away_team}
                  </td>
                  <td className="px-2 py-2">
                    {ev.event_start_time_utc ? new Date(ev.event_start_time_utc).toLocaleString() : "?"}
                  </td>
                  <td className="px-2 py-2">{ev.status}</td>
                </tr>
              ))}
              {events.length === 0 && (
                <tr>
                  <td className="px-2 py-4 text-slate-600" colSpan={5}>
                    No events found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
