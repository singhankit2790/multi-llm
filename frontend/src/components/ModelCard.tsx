import { PROVIDER_LABELS } from "../lib/constants";
import { formatLatency } from "../lib/format";
import { PROVIDER_SURFACE, btnSecondary, transition } from "../lib/ui";
import type { ComparisonResult, ProviderName } from "../types/chat";
import { CopyButton } from "./CopyButton";
import { MarkdownContent } from "./MarkdownContent";
import { ProviderBadge } from "./ProviderBadge";

type ModelCardProps = {
  result?: ComparisonResult;
  provider: ProviderName;
  loading?: boolean;
  continueDisabled?: boolean;
  onContinue?: (provider: ProviderName) => void;
};

export function ModelCard({
  result,
  provider,
  loading = false,
  continueDisabled = false,
  onContinue,
}: ModelCardProps) {
  const label = PROVIDER_LABELS[provider];
  const surface = PROVIDER_SURFACE[provider];

  return (
    <article
      className={`flex min-h-80 min-w-0 flex-col overflow-hidden rounded-2xl border bg-zinc-900/80 ${surface.border} ${transition}`}
    >
      <span className={`h-0.5 w-full ${surface.bar}`} aria-hidden="true" />
      <header className="flex items-start justify-between gap-3 px-4 pt-3.5 pb-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <ProviderBadge provider={provider} />
          <div className="min-w-0">
            <h3 className="text-[1.05rem] leading-tight font-medium text-zinc-50">
              {label}
            </h3>
            <p className="mt-0.5 truncate text-xs text-zinc-500">
              {loading ? "Waiting for model" : result?.model || "Unknown model"}
            </p>
          </div>
        </div>
        {result?.status === "success" && result.content ? (
          <CopyButton text={result.content} />
        ) : null}
      </header>

      <div className="min-h-44 flex-1 overflow-y-auto overflow-x-hidden border-y border-zinc-800/80 px-4 py-3 lg:max-h-72">
        {loading ? (
          <div className="space-y-2.5" aria-live="polite">
            <p className="text-sm text-zinc-400">Generating...</p>
            <div className="shimmer h-3 rounded" />
            <div className="shimmer h-3 w-5/6 rounded" />
            <div className="shimmer h-3 w-2/3 rounded" />
          </div>
        ) : result?.status === "success" && result.content ? (
          <MarkdownContent text={result.content} />
        ) : (
          <div className="space-y-1.5">
            <p className="text-sm font-medium text-zinc-200">
              {isConfigError(result?.error)
                ? "Not available / Configuration required"
                : "Unable to generate a response"}
            </p>
            <p className="text-sm leading-6 text-zinc-500">
              {friendlyProviderError(label, result?.error)}
            </p>
          </div>
        )}
      </div>

      <footer className="mt-auto space-y-3 px-4 py-3">
        <div className="flex items-center justify-between gap-2 text-xs">
          <StatusLabel loading={loading} status={result?.status} />
          <span className="text-zinc-500">
            {loading || !result ? "—" : formatLatency(result.latency_ms)}
          </span>
        </div>
        {onContinue ? (
          <button
            type="button"
            disabled={continueDisabled || loading}
            onClick={() => onContinue(provider)}
            className={`${btnSecondary} w-full`}
          >
            Continue with {label}
          </button>
        ) : null}
      </footer>
    </article>
  );
}

function StatusLabel({
  loading,
  status,
}: {
  loading: boolean;
  status?: "success" | "error";
}) {
  if (loading) {
    return (
      <span className="inline-flex items-center gap-1.5 text-amber-300">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
        Generating
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="inline-flex items-center gap-1.5 text-rose-300">
        <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
        Error
      </span>
    );
  }
  if (status === "success") {
    return (
      <span className="inline-flex items-center gap-1.5 text-emerald-300">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
        Success
      </span>
    );
  }
  return <span className="text-zinc-500">—</span>;
}

function isConfigError(error: string | null | undefined): boolean {
  return Boolean(error?.toLowerCase().includes("api key is not configured"));
}

function friendlyProviderError(
  label: string,
  error: string | null | undefined,
): string {
  if (!error) {
    return `${label} could not generate a response.`;
  }
  if (error.toLowerCase().includes("api key is not configured")) {
    return `${label} is not configured on the backend.`;
  }
  if (error.toLowerCase().includes("timed out")) {
    return `${label} timed out.`;
  }
  if (error.toLowerCase().includes("rejected the request")) {
    return error;
  }
  return `${label} could not generate a response.`;
}
