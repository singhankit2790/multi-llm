export type ProviderName = "openai" | "claude" | "gemini";

export type ProviderInfo = {
  name: string;
  display_name: string;
  model: string;
  available: boolean;
};

export type ResponseStatus = "success" | "error";

export type MessageRole = "system" | "user" | "assistant";

export type Message = {
  role: MessageRole;
  content: string;
};

export type ComparisonResult = {
  provider: ProviderName | string;
  model: string;
  content: string | null;
  status: ResponseStatus;
  latency_ms: number;
  error: string | null;
};

export type CompareRequest = {
  prompt: string;
  session_id?: string;
};

export type CompareResponse = {
  request_id: string;
  session_id: string;
  prompt: string;
  results: ComparisonResult[];
  total_latency_ms: number;
};

export type ContinueRequest = {
  session_id: string;
  model: ProviderName;
  prompt: string;
};

export type ContinueResponse = {
  request_id: string;
  session_id: string;
  result: ComparisonResult;
};

export type SessionResponse = {
  session_id: string;
  created_at: string;
};

export type ConversationTurn = {
  role: "user" | "assistant";
  content: string;
  error?: string | null;
  latencyMs?: number;
};
