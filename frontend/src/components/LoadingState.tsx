type LoadingStateProps = {
  message?: string;
};

export function LoadingState({
  message = "Comparing 3 AI models...",
}: LoadingStateProps) {
  return (
    <p className="mt-0.5 text-xs text-zinc-500" role="status">
      {message}
    </p>
  );
}
