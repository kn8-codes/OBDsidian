import { writable } from 'svelte/store';

export const connected = writable(false);

/**
 * data shape: { [pid]: { value: number, unit: string } }
 * e.g. { RPM: { value: 850, unit: "rpm" }, SPEED: { value: 45, unit: "mph" } }
 */
export const data = writable({});

let ws = null;
let reconnectTimer = null;
const RECONNECT_MS = 3000;

function connect(url) {
  ws = new WebSocket(url);

  ws.onopen = () => {
    connected.set(true);
  };

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);

    if (msg.snapshot) {
      // Full state snapshot sent on initial connect
      data.set(msg.snapshot);
    } else if (msg.pid !== undefined) {
      // Incremental per-PID update
      data.update((d) => ({
        ...d,
        [msg.pid]: { value: msg.value, unit: msg.unit },
      }));
    }
  };

  ws.onclose = () => {
    connected.set(false);
    reconnectTimer = setTimeout(() => connect(url), RECONNECT_MS);
  };

  ws.onerror = () => {
    // onclose fires after onerror, so reconnect is handled there
    ws.close();
  };
}

/**
 * Call from onMount. Returns a cleanup function for onDestroy.
 */
export function startTelemetry(url = 'ws://localhost:8000/ws') {
  connect(url);
  return () => {
    clearTimeout(reconnectTimer);
    ws?.close();
    ws = null;
  };
}
