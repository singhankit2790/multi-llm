import type { ProviderName } from "../types/chat";

export const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400/80 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950";

export const transition = "transition-colors duration-150";

export const btnBase = `inline-flex cursor-pointer items-center justify-center rounded-lg px-3.5 py-2 text-sm font-medium ${transition} ${focusRing} disabled:cursor-not-allowed`;

export const btnPrimary = `${btnBase} bg-zinc-100 text-zinc-950 hover:bg-white active:bg-zinc-200 disabled:bg-zinc-800 disabled:text-zinc-500`;

export const btnSecondary = `${btnBase} border border-zinc-800 bg-zinc-950 text-zinc-200 hover:border-zinc-600 hover:bg-zinc-900 active:bg-zinc-800 disabled:opacity-50`;

export const btnGhost = `${btnBase} text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100 disabled:opacity-50`;

export const btnQuiet = `${btnBase} px-2 py-1 text-xs font-normal text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 disabled:opacity-40`;

export const composerShell =
  "rounded-2xl border border-zinc-800 bg-zinc-900/80 shadow-[0_0_0_1px_rgba(255,255,255,0.02)]";

export const PROVIDER_SURFACE: Record<
  ProviderName,
  { border: string; bar: string; badge: string }
> = {
  openai: {
    border: "border-zinc-800 hover:border-emerald-800/70",
    bar: "bg-emerald-500/75",
    badge: "border-emerald-800/80 bg-emerald-950/80 text-emerald-300",
  },
  claude: {
    border: "border-zinc-800 hover:border-amber-800/70",
    bar: "bg-amber-500/75",
    badge: "border-amber-800/80 bg-amber-950/80 text-amber-300",
  },
  gemini: {
    border: "border-zinc-800 hover:border-sky-800/70",
    bar: "bg-sky-500/75",
    badge: "border-sky-800/80 bg-sky-950/80 text-sky-300",
  },
};
