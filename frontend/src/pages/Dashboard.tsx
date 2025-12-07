import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import type { MappingCandidate, ArbOpportunity, SportsEvent, Market } from "../types";

type Counts = {
  events: number;
  markets: number;
  pendingMappings: number;
  arbs: number;
};

const actionButtons = [
  { label: "Ingest Polymarket", path: "/ingest/polymarket" },
  { label: "Ingest Kalshi", path: "/ingest/kalshi" },
  { label: "Ingest Polymarket Quotes", path: "/ingest/polymarket/quotes" },
  { label: "Ingest Kalshi Quotes", path: "/ingest/kalshi/quotes" },
  { label: "Suggest Mappings", path: "/mapping-candidates/suggest" },
  { label: "Scan for Arbs", path: "/arbs/scan" },
];

export default function Dashboard() {
  const [counts, setCounts] = useState<Counts | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchCounts = async () => {
    setLoading(true);
    try {
      const [events, markets, mappings, arbs] = await Promise.all([
        api.get<SportsEvent[]>("/sports-events"),
        api.get<Market[]>("/markets"),
        api.get<MappingCandidate[]>("/mapping-candidates?status=pending&limit=500"),
        api.get<ArbOpportunity[]>("/arbs?limit=200"),
      ]);
      setCounts({
        events: events.length,
        markets: markets.length,
        pendingMappings: mappings.length,
        arbs: arbs.length,
      });
      setError(null);
    } catch (e: any) {
      setError(e?.message || "Failed to load counts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCounts();
  }, []);

  const handleAction = async (path: string) => {
    setMessage(null);
    setError(null);
    try {
      const resp = await api.post<{ [key: string]: any }>(path);
      setMessage(JSON.stringify(resp));
      fetchCounts();
    } catch (e: any) {
      setError(e?.message || "Action failed");
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card title="Events">{counts ? counts.events : "..."}</Card>
        <Card title="Markets">{counts ? counts.markets : "..."}</Card>
        <Card title="Pending mappings">{counts ? counts.pendingMappings : "..."}</Card>
        <Card title="Arbs">{counts ? counts.arbs : "..."}</Card>
      </div>

      <Card title="Actions">
        <div className="flex flex-wrap gap-2">
          {actionButtons.map((btn) => (
            <Button key={btn.path} onClick={() => handleAction(btn.path)}>
              {btn.label}
            </Button>
          ))}
        </div>
        {message && <div className="mt-3 rounded bg-green-50 p-2 text-sm text-green-800">{message}</div>}
        {error && <div className="mt-3 rounded bg-rose-50 p-2 text-sm text-rose-800">{error}</div>}
      </Card>

      {loading && <div className="text-sm text-slate-600">Loading...</div>}
    </div>
  );
}
