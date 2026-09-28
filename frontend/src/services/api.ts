import { API_BASE_URL } from "../lib/constants";
import { ApiError } from "../lib/errors";
import type {
  CompareRequest,
  CompareResponse,
  ContinueRequest,
  ContinueResponse,
  ProviderInfo,
  SessionResponse,
} from "../types/chat";
import type { HealthResponse } from "../types/health";

export async function getHealth(): Promise<HealthResponse> {
  const data = await requestJson<HealthResponse>("/health", {
    method: "GET",
  });
  if (!data || typeof data.status !== "string") {
    throw new ApiError("Health check returned an invalid response");
  }
  return data;
}

export async function getProviders(): Promise<ProviderInfo[]> {
  const data = await requestJson<{ providers: ProviderInfo[] }>(
    "/api/providers",
    { method: "GET" },
  );
  return data.providers;
}

export async function createSession(): Promise<SessionResponse> {
  return requestJson<SessionResponse>("/api/session", {
    method: "POST",
  });
}

export async function deleteSession(sessionId: string): Promise<void> {
  await requestJson(`/api/session/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
}

export async function comparePrompt(
  payload: CompareRequest,
): Promise<CompareResponse> {
  const body: CompareRequest = { prompt: payload.prompt };
  if (payload.session_id) {
    body.session_id = payload.session_id;
  }
  return requestJson<CompareResponse>("/api/chat/compare", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function continueWithModel(
  payload: ContinueRequest,
): Promise<ContinueResponse> {
  return requestJson<ContinueResponse>("/api/chat/continue", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.method && init.method !== "GET"
          ? { "Content-Type": "application/json" }
          : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Unable to reach the backend. Please make sure the server is running.",
      0,
    );
  }

  if (!response.ok) {
    throw await parseApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function parseApiError(response: Response): Promise<ApiError> {
  let detail: unknown;
  try {
    const payload = (await response.json()) as { detail?: unknown };
    detail = payload.detail;
  } catch {
    detail = undefined;
  }

  if (response.status === 404) {
    return new ApiError(
      "Your session expired. Please start a new comparison.",
      404,
    );
  }

  const message = formatDetail(detail);
  if (message) {
    return new ApiError(message, response.status);
  }

  if (response.status >= 500) {
    return new ApiError("The backend could not complete this request.", response.status);
  }

  return new ApiError("The request could not be processed.", response.status);
}

function formatDetail(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          const msg = (item as { msg: unknown }).msg;
          return typeof msg === "string" ? msg : null;
        }
        return null;
      })
      .filter((item): item is string => Boolean(item));
    if (messages.length > 0) {
      return messages.join(" ");
    }
  }
  return null;
}
