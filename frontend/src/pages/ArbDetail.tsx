import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { Card } from "../components/Card";
import type { ArbDetail as ArbDetailType, SportsEvent } from "../types";

export default function ArbDetail() {
  const { id } = useParams();
  const [arb, setArb] = useState<ArbDetailType | null>(null);
  const [event, setEvent] = useState<SportsEvent | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.get<ArbDetailType>(`/arbs/${id}`);
        setArb(data);
        const ev = await api.get<SportsEvent>(`/sports-events/${data.sports_event_id}`);
        setEvent(ev);
      } catch (e: any) {
        setError(e?.message || "Failed to load arbitrage opportunity");
      }
    };
    if (id) load();
  }, [id]);

  if (error) return <div className="text-sm text-rose-700">{error}</div>;
  if (!arb) return <div className="text-sm text-slate-600">Loading...</div>;

  return (
    <div className="space-y-4">
      <Card title="Arbitrage Summary">
        <div className="space-y-1 text-sm text-slate-700">
          <div>
            <span className="font-semibold">Event:</span> {event ? event.canonical_name : arb.sports_event_id}
          </div>
          <div>
            <span className="font-semibold">Type:</span> {arb.market_type} ({arb.outcome_group})
          </div>
          <div>
            <span className="font-semibold">Detected:</span> {new Date(arb.detected_at).toLocaleString()}
          </div>
          <div>
            <span className="font-semibold">Worst ROI:</span> {(arb.worst_case_roi * 100).toFixed(2)}%
          </div>
          <div>
            <span className="font-semibold">Stake:</span> ${arb.total_stake.toFixed(2)}
          </div>
          <div>
            <span className="font-semibold">PnL Range:</span> ${arb.worst_case_pnl.toFixed(2)} to $
            {arb.best_case_pnl.toFixed(2)}
          </div>
        </div>
      </Card>

      <Card title="Legs">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-600">
                <th className="px-2 py-2">Venue</th>
                <th className="px-2 py-2">Outcome</th>
                <th className="px-2 py-2">Stake (shares)</th>
                <th className="px-2 py-2">Price</th>
                <th className="px-2 py-2">Win PnL/share</th>
                <th className="px-2 py-2">Lose PnL/share</th>
              </tr>
            </thead>
            <tbody>
              {arb.legs.map((l, idx) => (
                <tr key={`${l.venue_id}-${idx}`} className="border-b border-slate-100">
                  <td className="px-2 py-2">{l.venue_id}</td>
                  <td className="px-2 py-2">{l.outcome_label}</td>
                  <td className="px-2 py-2">{l.stake_shares.toFixed(3)}</td>
                  <td className="px-2 py-2">{l.share_price.toFixed(3)}</td>
                  <td className="px-2 py-2">{l.win_pnl_per_share.toFixed(3)}</td>
                  <td className="px-2 py-2">{l.lose_pnl_per_share.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
