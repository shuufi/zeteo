export const months: string[] = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function pct(actual: number, base: number): number {
  if (base === 0) return 0;
  return Number((((actual - base) / base) * 100).toFixed(1));
}

export function formatRm(value: number): string {
  return `RM${value.toFixed(1)}m`;
}

export function formatRmAuto(value: number): string {
  if (Math.abs(value) >= 1000) return `RM${(value / 1000).toFixed(2)}bn`;
  return formatRm(value);
}

export function formatVar(varPct: number): string {
  const sign = varPct > 0 ? '+' : varPct < 0 ? '' : '±';
  return `${sign}${varPct}%`;
}

export function cumulative(values: number[]): number[] {
  let running = 0;
  return values.map((v) => {
    running += v;
    return Number(running.toFixed(1));
  });
}
