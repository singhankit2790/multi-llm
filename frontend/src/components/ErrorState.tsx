import { btnQuiet } from "../lib/ui";

type ErrorStateProps = {
  message: string;
  onDismiss?: () => void;
};

export function ErrorState({ message, onDismiss }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex items-start justify-between gap-3 rounded-xl border border-amber-900/50 bg-amber-950/25 px-3.5 py-2.5 text-sm text-amber-100"
    >
      <p>{message}</p>
      {onDismiss ? (
        <button type="button" onClick={onDismiss} className={`${btnQuiet} shrink-0`}>
          Dismiss
        </button>
      ) : null}
    </div>
  );
}
