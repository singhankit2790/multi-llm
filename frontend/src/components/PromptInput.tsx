import type { FormEvent, KeyboardEvent } from "react";

import { MAX_PROMPT_LENGTH } from "../lib/constants";
import { btnPrimary, composerShell } from "../lib/ui";

type PromptInputProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled: boolean;
  submitLabel: string;
  loadingLabel?: string;
  placeholder: string;
  inputId?: string;
  label?: string;
  helperText?: string;
  size?: "default" | "compact";
};

export function PromptInput({
  value,
  onChange,
  onSubmit,
  disabled,
  submitLabel,
  loadingLabel = "Working...",
  placeholder,
  inputId = "prompt-input",
  label = "Ask your question",
  helperText = "Enter to compare · Shift+Enter for new line",
  size = "default",
}: PromptInputProps) {
  const compact = size === "compact";

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (disabled || !value.trim()) {
      return;
    }
    onSubmit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!disabled && value.trim()) {
        onSubmit();
      }
    }
  }

  return (
    <form onSubmit={handleSubmit} className={`${composerShell} p-4`}>
      <label
        htmlFor={inputId}
        className="mb-2.5 block text-sm font-medium text-zinc-200"
      >
        {label}
      </label>
      <div
        className="rounded-xl border border-zinc-800 bg-zinc-950 focus-within:border-zinc-500 focus-within:ring-2 focus-within:ring-zinc-400/70"
      >
        <textarea
          id={inputId}
          value={value}
          onChange={(event) =>
            onChange(event.target.value.slice(0, MAX_PROMPT_LENGTH))
          }
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={compact ? 3 : 5}
          maxLength={MAX_PROMPT_LENGTH}
          placeholder={placeholder}
          className={`w-full resize-y border-0 bg-transparent px-3.5 pt-3 text-[0.95rem] leading-7 text-zinc-100 placeholder:text-zinc-600 outline-none disabled:cursor-not-allowed disabled:opacity-60 ${
            compact ? "min-h-20" : "min-h-28"
          }`}
        />
        <div className="flex flex-col gap-3 px-3 pb-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-zinc-500">
            {helperText}
            <span className="ml-2 text-zinc-600">
              {value.length}/{MAX_PROMPT_LENGTH}
            </span>
          </p>
          <button
            type="submit"
            disabled={disabled || !value.trim()}
            className={`${btnPrimary} w-full sm:w-auto`}
          >
            {disabled ? loadingLabel : submitLabel}
          </button>
        </div>
      </div>
    </form>
  );
}
