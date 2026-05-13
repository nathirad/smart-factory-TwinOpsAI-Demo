import { useEffect, useState } from "react";
import {
  LiveTelemetry,
  TelemetryStreamPayload,
  subscribeTelemetryStream,
} from "../api/client";

export function useTelemetryStream(baseUrl: string) {
  const [latestTelemetry, setLatestTelemetry] =
    useState<LiveTelemetry | null>(null);

  const [telemetryHistory, setTelemetryHistory] = useState<LiveTelemetry[]>([]);

  const [streamStatus, setStreamStatus] =
    useState<TelemetryStreamPayload["status"]>("waiting");

  const [streamMessage, setStreamMessage] = useState("Connecting...");

  useEffect(() => {
    const unsubscribe = subscribeTelemetryStream(
      baseUrl,
      (data) => {
        setLatestTelemetry(data);
        setTelemetryHistory((prev) => [...prev.slice(-29), data]);
      },
      (payload) => {
        setStreamStatus(payload.status);
        setStreamMessage(payload.message ?? payload.status);
      },
      () => {
        setStreamStatus("error");
        setStreamMessage("Stream connection error");
      }
    );

    return unsubscribe;
  }, [baseUrl]);

  return {
    latestTelemetry,
    telemetryHistory,
    streamStatus,
    streamMessage,
  };
}
