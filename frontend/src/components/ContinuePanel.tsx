import { PROVIDER_LABELS } from "../lib/constants";
import { formatLatency } from "../lib/format";
import { PROVIDER_SURFACE, btnGhost, btnSecondary } from "../lib/ui";
import type { ConversationTurn, ProviderName } from "../types/chat";
import { CopyButton } from "./CopyButton";
import { MarkdownContent } from "./MarkdownContent";
import { PromptInput } from "./PromptInput";
import { ProviderBadge } from "./ProviderBadge";

type ContinuePanelProps = {
  provider: ProviderName;
  turns: ConversationTurn[];
  prompt: string;
  onPromptChange: (value: string) => void;
  onSubmit: () => void;
  onBack: () => void;
  onNewComparison: () => void;
  disabled: boolean;
  generating?: boolean;
};

export function ContinuePanel({
  provider,
  turns,
  prompt,
  onPromptChange,
  onSubmit,
  onBack,
  onNewComparison,
  disabled,
  generating = false,
}: ContinuePanelProps) {
  const label = PROVIDER_LABELS[provider];
  const surface = PROVIDER_SURFACE[provider];

  return (
    <section className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <div className={`overflow-hidden rounded-2xl border bg-zinc-900/70 ${surface.border}`}>
        <span className={`block h-0.5 w-full ${surface.bar}`} aria-hidden="true" />
        <div className="flex items-start gap-3 px-4 py-4">
          <ProviderBadge provider={provider} size="md" />
          <div>
            <p className="text-[11px] font-medium tracking-[0.12em] text-zinc-500 uppercase">
              {label}
            </p>
            <h2 className="mt-0.5 text-lg font-semibold tracking-tight text-zinc-50">
              Continuing with {label}
            </h2>
            <p className="mt-1 text-sm text-zinc-400">
              Your follow-up messages will be sent only to {label}.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {turns.map((turn, index) => (
          <article
            key={`${turn.role}-${index}`}
            className={`rounded-xl border px-4 py-3.5 ${
              turn.role === "user"
                ? "border-zinc-800 bg-zinc-900/50"
                : "border-zinc-800/80 bg-zinc-950"
            }`}
          >
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="text-[11px] font-medium tracking-[0.12em] text-zinc-500 uppercase">
                {turn.role === "user" ? "You" : label}
              </p>
              {turn.role === "assistant" && turn.content ? (
                <CopyButton text={turn.content} />
              ) : null}
            </div>
            {turn.role === "assistant" && turn.error ? (
              <p className="text-sm text-zinc-300">
                {label} could not generate a response.
              </p>
            ) : turn.role === "assistant" ? (
              <MarkdownContent text={turn.content} />
            ) : (
              <p className="whitespace-pre-wrap text-sm leading-7 text-zinc-200">
                {turn.content}
              </p>
            )}
            {turn.role === "assistant" && turn.latencyMs != null && !turn.error ? (
              <p className="mt-2 text-xs text-zinc-500">
                {formatLatency(turn.latencyMs)}
              </p>
            ) : null}
          </article>
        ))}
        {generating ? (
          <div
            className="space-y-2.5 rounded-xl border border-zinc-800 px-4 py-3.5"
            role="status"
          >
            <p className="text-[11px] font-medium tracking-[0.12em] text-zinc-500 uppercase">
              {label}
            </p>
            <p className="text-sm text-zinc-400">Generating...</p>
            <div className="shimmer h-3 rounded" />
            <div className="shimmer h-3 w-2/3 rounded" />
          </div>
        ) : null}
      </div>

      <PromptInput
        value={prompt}
        onChange={onPromptChange}
        onSubmit={onSubmit}
        disabled={disabled}
        submitLabel="Send"
        loadingLabel="Sending..."
        placeholder={`Ask ${label} a follow-up...`}
        inputId="follow-up-input"
        label="Follow-up"
        helperText="Enter to send · Shift+Enter for new line"
        size="compact"
      />

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <button type="button" onClick={onBack} className={btnGhost}>
          Back to results
        </button>
        <button type="button" onClick={onNewComparison} className={btnSecondary}>
          New Comparison
        </button>
      </div>
    </section>
  );
}
