import { formatLatency } from "../lib/format";
import { btnSecondary } from "../lib/ui";
import { PROVIDER_ORDER } from "../lib/constants";
import type { ComparisonResult, ProviderName } from "../types/chat";
import { LoadingState } from "./LoadingState";
import { ModelCard } from "./ModelCard";

type ComparisonPanelProps = {
  results: ComparisonResult[];
  loading: boolean;
  continueDisabled?: boolean;
  onContinue?: (provider: ProviderName) => void;
  onNewComparison?: () => void;
  totalLatencyMs?: number | null;
};

export function ComparisonPanel({
  results,
  loading,
  continueDisabled = false,
  onContinue,
  onNewComparison,
  totalLatencyMs,
}: ComparisonPanelProps) {
  const resultMap = new Map(results.map((item) => [item.provider, item]));

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-base font-medium tracking-tight text-zinc-100">
            Comparison
          </h2>
          {totalLatencyMs != null && !loading ? (
            <p className="mt-0.5 text-xs text-zinc-500">
              3 models · {formatLatency(totalLatencyMs)}
            </p>
          ) : loading ? (
            <LoadingState />
          ) : (
            <p className="mt-0.5 text-xs text-zinc-500">
              OpenAI · Claude · Gemini
            </p>
          )}
        </div>
        {onNewComparison && !loading ? (
          <button type="button" onClick={onNewComparison} className={btnSecondary}>
            New Comparison
          </button>
        ) : null}
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 lg:items-stretch">
        {PROVIDER_ORDER.map((provider) => (
          <ModelCard
            key={provider}
            provider={provider}
            result={resultMap.get(provider)}
            loading={loading}
            continueDisabled={continueDisabled}
            onContinue={onContinue}
          />
        ))}
      </div>
    </section>
  );
}
