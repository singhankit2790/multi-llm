import type { BackendConnectionStatus } from "../hooks/useBackendHealth";

type BackendStatusProps = {
  status: BackendConnectionStatus;
};

const STATUS_DOT: Record<BackendConnectionStatus, string> = {
  checking: "bg-amber-400",
  connected: "bg-emerald-400",
  disconnected: "bg-rose-400",
};

export function BackendStatus({ status }: BackendStatusProps) {
  const label =
    status === "checking"
      ? "Checking"
      : status === "connected"
        ? "Connected"
        : "Offline";

  return (
    <div
      className="inline-flex shrink-0 items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900 px-2.5 py-1 text-xs text-zinc-300"
      role="status"
      aria-live="polite"
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[status]}`}
        aria-hidden="true"
      />
      <span>{label}</span>
    </div>
  );
}
