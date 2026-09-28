import { useEffect, useState } from "react";

import { getHealth } from "../services/api";

export type BackendConnectionStatus =
  | "checking"
  | "connected"
  | "disconnected";

export function useBackendHealth(): BackendConnectionStatus {
  const [status, setStatus] = useState<BackendConnectionStatus>("checking");

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const result = await getHealth();
        if (!cancelled) {
          setStatus(result.status === "ok" ? "connected" : "disconnected");
        }
      } catch {
        if (!cancelled) {
          setStatus("disconnected");
        }
      }
    }

    void checkHealth();

    return () => {
      cancelled = true;
    };
  }, []);

  return status;
}
