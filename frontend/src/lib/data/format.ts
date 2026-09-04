import type { ComparisonNode, HierarchyNode } from './types';

export const months: string[] = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export type MoneyScaleChoice = 'auto' | 'units' | 'thousands' | 'millions' | 'billions';
export type MoneyScale = Exclude<MoneyScaleChoice, 'auto'>;

export const moneyScaleOptions: { value: MoneyScaleChoice; label: string }[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'units', label: 'Units' },
  { value: 'thousands', label: 'Thousands' },
  { value: 'millions', label: 'Millions' },
  { value: 'billions', label: 'Billions' },
];

const scaleDivisor: Record<MoneyScale, number> = {
  units: 1,
  thousands: 1_000,
  millions: 1_000_000,
  billions: 1_000_000_000,
};

const scaleSuffix: Record<MoneyScale, string> = {
  units: '',
  thousands: 'k',
  millions: 'm',
  billions: 'bn',
};

export function resolveMoneyScale(choice: MoneyScaleChoice, values: number[]): MoneyScale {
  if (choice !== 'auto') return choice;
  const largest = values.reduce((max, value) => (Number.isFinite(value) ? Math.max(max, Math.abs(value)) : max), 0);
  if (largest >= 1_000_000_000) return 'billions';
  if (largest >= 1_000_000) return 'millions';
  if (largest >= 1_000) return 'thousands';
  return 'units';
}

export function scaledMoney(value: number, scale: MoneyScale): number {
  return value / scaleDivisor[scale];
}

function withThousands(value: number): string {
  return value.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

export function formatMoneyNumber(value: number, scale: MoneyScale): string {
  return withThousands(scaledMoney(value, scale));
}

export function formatStatementMoney(value: number, scale: MoneyScale): string {
  const text = withThousands(Math.abs(scaledMoney(value, scale)));
  return value < 0 && value !== 0 ? `(${text})` : text;
}

export function formatMoney(value: number, currency: string, scale: MoneyScale): string {
  return `${currency} ${formatMoneyNumber(value, scale)}${scaleSuffix[scale]}`;
}

export function moneyCaption(currency: string, scale: MoneyScale): string {
  return scale === 'units' ? currency : `${currency} ${scale}`;
}

export function moneyScaleControlLabel(choice: MoneyScaleChoice, resolved: MoneyScale): string {
  const resolvedLabel = resolved[0].toUpperCase() + resolved.slice(1);
  return choice === 'auto' ? `Auto (${resolvedLabel})` : resolvedLabel;
}

export function hierarchyMoneyValues(tree: Record<string, HierarchyNode>, rootId?: string): number[] {
  const values: number[] = [];
  const seen = new Set<string>();
  const visit = (node: HierarchyNode | undefined): void => {
    if (!node || seen.has(node.id)) return;
    seen.add(node.id);
    if (node.unit === 'money' || node.unit === 'currency-per-day' || node.unit === 'currency-per-month') {
      values.push(node.actual, node.budget, node.priorYear, ...node.monthlyActual, ...node.monthlyPriorYear);
    }
    for (const childId of node.childIds) visit(tree[childId]);
  };
  if (rootId) visit(tree[rootId]);
  else for (const node of Object.values(tree)) visit(node);
  return values;
}

export function comparisonMoneyValues(tree: Record<string, ComparisonNode>, rootId?: string): number[] {
  const values: number[] = [];
  const seen = new Set<string>();
  const visit = (node: ComparisonNode | undefined): void => {
    if (!node || seen.has(node.id)) return;
    seen.add(node.id);
    if (node.unit === 'money' || node.unit === 'currency-per-day' || node.unit === 'currency-per-month') {
      values.push(node.valueA, node.valueB, node.delta);
    }
    for (const childId of node.childIds) visit(tree[childId]);
  };
  if (rootId) visit(tree[rootId]);
  else for (const node of Object.values(tree)) visit(node);
  return values;
}

export function pct(actual: number, base: number): number {
  if (base === 0) return 0;
  return Number((((actual - base) / base) * 100).toFixed(1));
}

export function formatVar(varPct: number): string {
  const sign = varPct > 0 ? '+' : varPct < 0 ? '' : '±';
  return `${sign}${varPct}%`;
}

export function cumulative(values: number[]): number[] {
  let running = 0;
  return values.map((v) => {
    running += v;
    return Number(running.toFixed(2));
  });
}
