import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { Card } from "../components/Card";
import type { SportsEvent, Market, QuoteSummary } from "../types";

export default function EventDetail() {
  const { id } = useParams();
  const [event, setEvent] = useState<SportsEvent | null>(null);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [quotes, setQuotes] = useState<QuoteSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const ev = await api.get<SportsEvent>(`/sports-events/${id}`);
        setEvent(ev);
        const mkts = await api.get<Market[]>(`/markets?sport=${ev.sport}`);
        const q = await api.get<QuoteSummary[]>(`/quotes?sports_event_id=${id}`);
        setMarkets(mkts.filter((m) => m.sports_event_id === ev.id));
        setQuotes(q);
      } catch (e: any) {
        setError(e?.message || "Failed to load event");
      }
    };
    if (id) load();
  }, [id]);

  if (error) return <div className="text-sm text-rose-700">{error}</div>;
  if (!event) return <div className="text-sm text-slate-600">Loading...</div>;

  return (
    <div className="space-y-4">
      <Card title="Event">
        <div className="text-sm text-slate-700 space-y-1">
          <div className="font-semibold">
            {event.home_team} vs {event.away_team}
          </div>
          <div>Sport: {event.sport}</div>
          <div>Status: {event.status}</div>
          <div>Start: {event.event_start_time_utc ? new Date(event.event_start_time_utc).toLocaleString() : "?"}</div>
        </div>
      </Card>

      <Card title={`Markets (${markets.length})`}>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-600">
                <th className="px-2 py-2">ID</th>
                <th className="px-2 py-2">Venue</th>
                <th className="px-2 py-2">Type</th>
                <th className="px-2 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {markets.map((m) => (
                <tr key={m.id} className="border-b border-slate-100">
                  <td className="px-2 py-2">{m.id}</td>
                  <td className="px-2 py-2">{m.venue_id}</td>
                  <td className="px-2 py-2">{m.market_type}</td>
                  <td className="px-2 py-2">{m.status}</td>
                </tr>
              ))}
              {markets.length === 0 && (
                <tr>
                  <td className="px-2 py-4 text-slate-600" colSpan={4}>
                    No markets attached.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title={`Latest Quotes (${quotes.length})`}>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-600">
                <th className="px-2 py-2">Venue</th>
                <th className="px-2 py-2">Outcome</th>
                <th className="px-2 py-2">Raw</th>
                <th className="px-2 py-2">Share</th>
                <th className="px-2 py-2">Win PnL</th>
                <th className="px-2 py-2">Lose PnL</th>
                <th className="px-2 py-2">Time</th>
              </tr>
            </thead>
            <tbody>
              {quotes.map((q) => (
                <tr key={q.quote_id} className="border-b border-slate-100">
                  <td className="px-2 py-2">{q.venue_id}</td>
                  <td className="px-2 py-2">{q.outcome_label}</td>
                  <td className="px-2 py-2">{q.raw_price ?? "-"}</td>
                  <td className="px-2 py-2">{q.share_price?.toFixed(3)}</td>
                  <td className="px-2 py-2">{q.win_pnl?.toFixed(3)}</td>
                  <td className="px-2 py-2">{q.lose_pnl?.toFixed(3)}</td>
                  <td className="px-2 py-2">{new Date(q.timestamp).toLocaleTimeString()}</td>
                </tr>
              ))}
              {quotes.length === 0 && (
                <tr>
                  <td className="px-2 py-4 text-slate-600" colSpan={7}>
                    No quotes found.
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
