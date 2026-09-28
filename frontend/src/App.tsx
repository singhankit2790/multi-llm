import { useState } from "react";

import { AppHeader } from "./components/AppHeader";
import { ComparisonPanel } from "./components/ComparisonPanel";
import { ContinuePanel } from "./components/ContinuePanel";
import { EmptyState } from "./components/EmptyState";
import { ErrorState } from "./components/ErrorState";
import { PromptInput } from "./components/PromptInput";
import { useBackendHealth } from "./hooks/useBackendHealth";
import { useChat } from "./hooks/useChat";

function App() {
  const backendStatus = useBackendHealth();
  const chat = useChat();
  const [prompt, setPrompt] = useState("");
  const [followUp, setFollowUp] = useState("");

  function handleCompare() {
    void chat.compare(prompt).then((ok) => {
      if (ok) {
        setPrompt("");
      }
    });
  }

  function handleFollowUp() {
    void chat.sendFollowUp(followUp).then((ok) => {
      if (ok) {
        setFollowUp("");
      }
    });
  }

  function handleNewComparison() {
    setPrompt("");
    setFollowUp("");
    chat.newComparison();
  }

  return (
    <div className="min-h-svh bg-zinc-950 text-zinc-200">
      <AppHeader backendStatus={backendStatus} />
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        {backendStatus === "disconnected" ? (
          <ErrorState message="Backend Offline. Please make sure the FastAPI server is running." />
        ) : null}
        {chat.error ? (
          <ErrorState message={chat.error} onDismiss={chat.clearError} />
        ) : null}

        {chat.mode === "idle" ? (
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 pt-2 sm:pt-6">
            <EmptyState onChooseExample={(example) => setPrompt(example)} />
            <PromptInput
              value={prompt}
              onChange={setPrompt}
              onSubmit={handleCompare}
              disabled={chat.isSubmitting || backendStatus === "disconnected"}
              submitLabel="Compare"
              loadingLabel="Comparing..."
              placeholder="Ask anything..."
              label="Ask your question"
            />
          </div>
        ) : null}

        {chat.mode === "comparing" || chat.mode === "comparison" ? (
          <div className="flex flex-col gap-5">
            <ComparisonPanel
              results={chat.results}
              loading={chat.mode === "comparing"}
              continueDisabled={chat.isSubmitting || !chat.sessionId}
              onContinue={chat.startContinuation}
              onNewComparison={
                chat.mode === "comparison" ? handleNewComparison : undefined
              }
              totalLatencyMs={chat.totalLatencyMs}
            />
            <PromptInput
              value={prompt}
              onChange={setPrompt}
              onSubmit={handleCompare}
              disabled={chat.isSubmitting || backendStatus === "disconnected"}
              submitLabel="Compare"
              loadingLabel="Comparing..."
              placeholder="Ask another comparison question..."
              label="Ask another comparison question"
              size="compact"
            />
          </div>
        ) : null}

        {chat.mode === "continuation" && chat.selectedProvider ? (
          <ContinuePanel
            provider={chat.selectedProvider}
            turns={chat.turns}
            prompt={followUp}
            onPromptChange={setFollowUp}
            onSubmit={handleFollowUp}
            onBack={() => {
              setFollowUp("");
              chat.backToComparison();
            }}
            onNewComparison={handleNewComparison}
            disabled={chat.isSubmitting}
            generating={chat.isSubmitting}
          />
        ) : null}
      </main>
    </div>
  );
}

export default App;
