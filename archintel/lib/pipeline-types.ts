export type PipelineStatus = 'idle' | 'running' | 'complete' | 'error';

export interface CostBreakdownItem {
  name: string;
  type: string;
  description?: string;
  count?: number;
  computeCost?: number;
  dataCost?: number;
  monthlyCost: number;
  note?: string;
}

export interface CostResults {
  text: string;
  breakdown: CostBreakdownItem[];
  totalMonthlyCost: number;
  annualEstimate: number;
}
