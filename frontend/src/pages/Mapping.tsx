import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import type { MappingCandidate } from "../types";

export default function Mapping() {
  const [candidates, setCandidates] = useState<MappingCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [minConfidence, setMinConfidence] = useState(0);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.get<MappingCandidate[]>(`/mapping-candidates?status=pending&limit=200`);
      setCandidates(data);
      setError(null);
    } catch (e: any) {
      setError(e?.message || "Failed to load candidates");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const act = async (id: number, action: "accept" | "reject") => {
    try {
      await api.post(`/mapping-candidates/${id}/${action}`);
      setCandidates((prev) => prev.filter((c) => c.id !== id));
    } catch (e: any) {
      setError(e?.message || "Action failed");
    }
  };

  const filtered = candidates.filter((c) => c.confidence_score >= minConfidence);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button onClick={load} variant="secondary">
          Refresh
        </Button>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          Min confidence
          <input
            type="number"
            step="0.1"
            min={0}
            max={1}
            value={minConfidence}
            onChange={(e) => setMinConfidence(Number(e.target.value))}
            className="w-20 rounded border border-slate-300 px-2 py-1 text-sm"
          />
        </label>
      </div>

      {error && <div className="rounded bg-rose-50 p-2 text-sm text-rose-800">{error}</div>}
      {loading && <div className="text-sm text-slate-600">Loading...</div>}

      <Card title={`Pending candidates (${filtered.length})`}>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-600">
                <th className="px-2 py-2">Confidence</th>
                <th className="px-2 py-2">Venue</th>
                <th className="px-2 py-2">Question</th>
                <th className="px-2 py-2">Parsed</th>
                <th className="px-2 py-2">Candidate event</th>
                <th className="px-2 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id} className="border-b border-slate-100">
                  <td className="px-2 py-2">{c.confidence_score.toFixed(2)}</td>
                  <td className="px-2 py-2">{c.market.venue_id}</td>
                  <td className="px-2 py-2 max-w-xs truncate">{c.market.question_text}</td>
                  <td className="px-2 py-2 text-slate-600">
                    {c.market.parsed_sport} | {c.market.parsed_home_team} @ {c.market.parsed_away_team}
                  </td>
                  <td className="px-2 py-2 text-slate-600">
                    {c.sports_event.home_team} @ {c.sports_event.away_team}
                    {c.sports_event.event_start_time_utc ? ` (${c.sports_event.event_start_time_utc})` : ""}
                  </td>
                  <td className="px-2 py-2 space-x-2">
                    <Button onClick={() => act(c.id, "accept")}>Accept</Button>
                    <Button variant="secondary" onClick={() => act(c.id, "reject")}>
                      Reject
                    </Button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td className="px-2 py-4 text-slate-600" colSpan={6}>
                    No candidates match the filter.
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
