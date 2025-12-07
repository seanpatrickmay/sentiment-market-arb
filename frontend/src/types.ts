export type SportsEvent = {
  id: number;
  sport: string;
  league?: string | null;
  home_team: string;
  away_team: string;
  event_start_time_utc?: string | null;
  canonical_name: string;
  status: string;
};

export type Market = {
  id: number;
  venue_id: string;
  sports_event_id?: number | null;
  venue_market_key: string;
  market_type: string;
  question_text: string;
  status: string;
};

export type MappingCandidate = {
  id: number;
  market_id: number;
  candidate_sports_event_id?: number | null;
  confidence_score: number;
  status: string;
  market: {
    id: number;
    venue_id: string;
    question_text: string;
    parsed_sport?: string | null;
    parsed_home_team?: string | null;
    parsed_away_team?: string | null;
  };
  sports_event: {
    id?: number | null;
    sport?: string | null;
    home_team?: string | null;
    away_team?: string | null;
    event_start_time_utc?: string | null;
  };
  features: Record<string, any>;
};

export type ArbOpportunity = {
  id: number;
  sports_event_id: number;
  market_type: string;
  outcome_group?: string | null;
  detected_at: string;
  num_outcomes: number;
  total_stake: number;
  worst_case_pnl: number;
  best_case_pnl: number;
  worst_case_roi: number;
  status: string;
};

export type ArbDetail = ArbOpportunity & {
  legs: ArbLeg[];
};

export type ArbLeg = {
  venue_id: string;
  market_outcome_id: number;
  outcome_label: string;
  stake_shares: number;
  share_price: number;
  win_pnl_per_share: number;
  lose_pnl_per_share: number;
  source_quote_id?: number | null;
};

export type QuoteSummary = {
  quote_id: number;
  timestamp: string;
  venue_id: string;
  market_id: number;
  market_outcome_id: number;
  outcome_label: string;
  raw_price?: number | null;
  price_format: string;
  share_price?: number | null;
  win_pnl?: number | null;
  lose_pnl?: number | null;
};

