import type { Confidence } from '$lib/api';

export function formatDecimal(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits
  }).format(value);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return `${(value * 100).toFixed(1)}%`;
}

export function formatSignedPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}%`;
}

export function formatCompact(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1
  }).format(value);
}

export function formatTimestamp(value: string | null): string {
  if (!value) return 'Not yet updated';
  return new Date(value).toLocaleString();
}

export function confidenceClass(value: Confidence): string {
  return value;
}
