import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import type { ArbOpportunity } from "../types";

export default function Arbs() {
  const [arbs, setArbs] = useState<ArbOpportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [minRoi, setMinRoi] = useState<number | undefined>();

  const load = async () => {
    setLoading(true);
    try {
      const query = minRoi !== undefined ? `?min_roi=${minRoi}` : "";
      const data = await api.get<ArbOpportunity[]>(`/arbs${query}`);
      setArbs(data);
      setError(null);
    } catch (e: any) {
      setError(e?.message || "Failed to load arbs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [minRoi]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button onClick={load} variant="secondary">
          Refresh
        </Button>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          Min ROI
          <input
            type="number"
            step="0.001"
            value={minRoi ?? ""}
            onChange={(e) => setMinRoi(e.target.value === "" ? undefined : Number(e.target.value))}
            className="w-24 rounded border border-slate-300 px-2 py-1 text-sm"
          />
        </label>
      </div>
      {error && <div className="rounded bg-rose-50 p-2 text-sm text-rose-800">{error}</div>}
      {loading && <div className="text-sm text-slate-600">Loading...</div>}

      <Card title={`Arbitrage opportunities (${arbs.length})`}>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-600">
                <th className="px-2 py-2">ID</th>
                <th className="px-2 py-2">Event</th>
                <th className="px-2 py-2">Type</th>
                <th className="px-2 py-2">Detected</th>
                <th className="px-2 py-2">Worst ROI</th>
                <th className="px-2 py-2">Stake</th>
              </tr>
            </thead>
            <tbody>
              {arbs.map((a) => (
                <tr key={a.id} className="border-b border-slate-100">
                  <td className="px-2 py-2">
                    <Link className="text-slate-900 underline" to={`/arbs/${a.id}`}>
                      {a.id}
                    </Link>
                  </td>
                  <td className="px-2 py-2">{a.sports_event_id}</td>
                  <td className="px-2 py-2">{a.market_type}</td>
                  <td className="px-2 py-2">{new Date(a.detected_at).toLocaleString()}</td>
                  <td className="px-2 py-2">{(a.worst_case_roi * 100).toFixed(2)}%</td>
                  <td className="px-2 py-2">${a.total_stake.toFixed(2)}</td>
                </tr>
              ))}
              {arbs.length === 0 && (
                <tr>
                  <td className="px-2 py-4 text-slate-600" colSpan={6}>
                    No arbs found.
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
