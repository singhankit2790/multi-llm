import { APP_NAME, APP_TAGLINE } from "../lib/constants";
import { BackendStatus } from "./BackendStatus";
import type { BackendConnectionStatus } from "../hooks/useBackendHealth";

type AppHeaderProps = {
  backendStatus: BackendConnectionStatus;
};

export function AppHeader({ backendStatus }: AppHeaderProps) {
  return (
    <header className="border-b border-zinc-800/80 bg-zinc-950/90">
      <div className="mx-auto flex max-w-7xl items-start justify-between gap-4 px-4 py-4 sm:items-center sm:px-6 lg:px-8">
        <div className="min-w-0">
          <p className="text-[11px] font-medium tracking-[0.14em] text-zinc-500 uppercase">
            IIT Patna AI/ML
          </p>
          <h1 className="mt-1 text-[1.35rem] leading-tight font-semibold tracking-tight text-zinc-50 sm:text-[1.75rem]">
            {APP_NAME}
          </h1>
          <p className="mt-1 text-sm text-zinc-400">{APP_TAGLINE}</p>
        </div>
        <BackendStatus status={backendStatus} />
      </div>
    </header>
  );
}
