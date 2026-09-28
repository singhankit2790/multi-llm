import { PROVIDER_SURFACE } from "../lib/ui";
import type { ProviderName } from "../types/chat";

const MARK: Record<ProviderName, string> = {
  openai: "O",
  claude: "C",
  gemini: "G",
};

type ProviderBadgeProps = {
  provider: ProviderName;
  size?: "sm" | "md";
};

export function ProviderBadge({ provider, size = "sm" }: ProviderBadgeProps) {
  const box = size === "md" ? "h-8 w-8 text-sm" : "h-6 w-6 text-[11px]";

  return (
    <span
      className={`inline-flex ${box} items-center justify-center rounded-md border font-semibold ${PROVIDER_SURFACE[provider].badge}`}
      aria-hidden="true"
    >
      {MARK[provider]}
    </span>
  );
}
