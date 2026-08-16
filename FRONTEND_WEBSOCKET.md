# Unified Frontend WebSocket

Use one socket for backend health, model availability, audio upload, processing progress, errors, and the finished viseme timeline.

```ts
export type BackendSocketMessage =
    | { type: "health"; health: { status: "ok"; version: string } }
    | { type: "models"; models: WhisperModel[] }
    | { type: "upload_ready" }
    | { type: "accepted"; job: JobStatus }
    | { type: "status"; job: JobStatus }
    | { type: "result"; job_id: string; result: AnalysisResult }
    | { type: "error"; error: string; job?: JobStatus };

export interface UnifiedBackendSocket {
    analyze(file: File, config: {
        model: string;
        language: string;
        interval: number;
        smoothing: boolean;
        device?: string;
    }): void;
    close(): void;
}

export function connectBackend(
    onMessage: (message: BackendSocketMessage) => void,
    onOffline: () => void,
): UnifiedBackendSocket {
    const socketUrl = getBaseUrl().replace(/^http/, "ws");
    const socket = new WebSocket(`${socketUrl}/api/ws`);
    let upload: File | null = null;

    socket.onmessage = (event) => {
        const message: BackendSocketMessage = JSON.parse(event.data);
        if (message.type === "upload_ready") {
            if (!upload) {
                onMessage({ type: "error", error: "No audio file is waiting to upload." });
                return;
            }
            socket.send(upload);
            upload = null;
        }
        onMessage(message);
    };
    socket.onerror = () => onOffline();
    socket.onclose = () => onOffline();

    return {
        analyze(file, config) {
            if (socket.readyState !== WebSocket.OPEN) {
                onMessage({ type: "error", error: "The backend socket is not connected." });
                return;
            }
            upload = file;
            socket.send(JSON.stringify({
                type: "analyze",
                file_name: file.name,
                model: config.model,
                language: config.language,
                interval: config.interval,
                smoothing: config.smoothing,
                device: config.device || "Auto",
            }));
        },
        close() {
            socket.close();
        },
    };
}
```

## Usage

Create one connection when the app loads:

```ts
const backend = connectBackend(
    (message) => {
        switch (message.type) {
            case "health":
                setBackendOnline(true);
                break;
            case "models":
                setModels(message.models);
                break;
            case "accepted":
            case "status":
                setJob(message.job);
                break;
            case "result":
                setResult(message.result);
                break;
            case "error":
                setError(message.error);
                break;
        }
    },
    () => setBackendOnline(false),
);
```

Start an analysis using the same connection:

```ts
backend.analyze(file, config);
```

Protocol order:

```text
server -> health
server -> models
client -> { type: "analyze", file_name, model, language, interval, smoothing, device }
server -> upload_ready
client -> binary audio file
server -> accepted
server -> status (as stages change)
server -> result | error
```

The connection stays open after `result`, so it continues to send health heartbeats and model-cache changes and can process another file. The server sends health every three seconds. If `onclose` or `onerror` occurs unexpectedly, mark the backend offline and reconnect.

`interval` may be sent as `40` for 40 ms or `0.04` for 0.04 seconds. Final `result.visemes` entries always use seconds and contain only state changes: consecutive frames with the same viseme are merged into one entry.
