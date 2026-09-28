import { useCallback, useRef, useState } from "react";

import { comparePrompt, continueWithModel } from "../services/api";
import { toUserFacingError } from "../lib/errors";
import { PROVIDER_ORDER } from "../lib/constants";
import type {
  ComparisonResult,
  ConversationTurn,
  ProviderName,
} from "../types/chat";

export type ChatMode = "idle" | "comparing" | "comparison" | "continuation";

function sortResults(results: ComparisonResult[]): ComparisonResult[] {
  const rank = new Map(PROVIDER_ORDER.map((name, index) => [name, index]));
  return [...results].sort((left, right) => {
    const leftRank = rank.get(left.provider as ProviderName) ?? 99;
    const rightRank = rank.get(right.provider as ProviderName) ?? 99;
    return leftRank - rightRank;
  });
}

export function useChat() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [mode, setMode] = useState<ChatMode>("idle");
  const [results, setResults] = useState<ComparisonResult[]>([]);
  const [comparePromptText, setComparePromptText] = useState<string | null>(null);
  const [totalLatencyMs, setTotalLatencyMs] = useState<number | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<ProviderName | null>(
    null,
  );
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inFlight = useRef(false);
  const hasResults = useRef(false);

  const compare = useCallback(async (prompt: string): Promise<boolean> => {
    const trimmed = prompt.trim();
    if (!trimmed || inFlight.current) {
      return false;
    }
    inFlight.current = true;
    setIsSubmitting(true);
    setError(null);
    setMode("comparing");
    setSelectedProvider(null);
    setTurns([]);
    try {
      const response = await comparePrompt({
        prompt: trimmed,
        ...(sessionId ? { session_id: sessionId } : {}),
      });
      const ordered = sortResults(response.results);
      setSessionId(response.session_id);
      setComparePromptText(response.prompt);
      setResults(ordered);
      setTotalLatencyMs(response.total_latency_ms);
      hasResults.current = ordered.length > 0;
      setMode("comparison");
      return true;
    } catch (caught) {
      const message = toUserFacingError(caught);
      console.warn("Compare request failed:", message);
      setError(message);
      // Keep the comparison panel visible so Compare never snaps back to empty.
      setMode("comparison");
      return false;
    } finally {
      inFlight.current = false;
      setIsSubmitting(false);
    }
  }, [sessionId]);

  const startContinuation = useCallback((provider: ProviderName) => {
    const card = results.find((item) => item.provider === provider);
    if (!card || !sessionId || !comparePromptText) {
      return;
    }
    setSelectedProvider(provider);
    setTurns([
      { role: "user", content: comparePromptText },
      {
        role: "assistant",
        content: card.content ?? "",
        error: card.status === "error" ? card.error : null,
        latencyMs: card.latency_ms,
      },
    ]);
    setError(null);
    setMode("continuation");
  }, [comparePromptText, results, sessionId]);

  const sendFollowUp = useCallback(async (prompt: string): Promise<boolean> => {
    const trimmed = prompt.trim();
    if (!trimmed || !sessionId || !selectedProvider || inFlight.current) {
      return false;
    }
    inFlight.current = true;
    setIsSubmitting(true);
    setError(null);
    setTurns((current) => [...current, { role: "user", content: trimmed }]);
    try {
      const response = await continueWithModel({
        session_id: sessionId,
        model: selectedProvider,
        prompt: trimmed,
      });
      setSessionId(response.session_id);
      setTurns((current) => [
        ...current,
        {
          role: "assistant",
          content: response.result.content ?? "",
          error:
            response.result.status === "error" ? response.result.error : null,
          latencyMs: response.result.latency_ms,
        },
      ]);
      return true;
    } catch (caught) {
      const message = toUserFacingError(caught);
      console.warn("Continue request failed:", message);
      setError(message);
      return false;
    } finally {
      inFlight.current = false;
      setIsSubmitting(false);
    }
  }, [selectedProvider, sessionId]);

  const backToComparison = useCallback(() => {
    setSelectedProvider(null);
    setTurns([]);
    setError(null);
    setMode(results.length > 0 ? "comparison" : "idle");
  }, [results.length]);

  const newComparison = useCallback(() => {
    inFlight.current = false;
    hasResults.current = false;
    setSessionId(null);
    setMode("idle");
    setResults([]);
    setComparePromptText(null);
    setTotalLatencyMs(null);
    setSelectedProvider(null);
    setTurns([]);
    setError(null);
    setIsSubmitting(false);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    sessionId,
    mode,
    results,
    comparePromptText,
    totalLatencyMs,
    selectedProvider,
    turns,
    error,
    isSubmitting,
    compare,
    startContinuation,
    sendFollowUp,
    backToComparison,
    newComparison,
    clearError,
  };
}
