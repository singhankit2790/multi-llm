export function formatLatency(latencyMs: number): string {
  if (latencyMs < 1000) {
    return `${latencyMs} ms`;
  }
  return `${(latencyMs / 1000).toFixed(1)}s`;
}
