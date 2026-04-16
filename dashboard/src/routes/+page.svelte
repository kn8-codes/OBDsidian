<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	type PidEntry = { value: number; unit: string };
	type LiveData = Record<string, PidEntry>;

	let data = $state<LiveData>({});
	let status = $state<'connecting' | 'open' | 'closed' | 'error'>('connecting');

	const DISPLAY_PIDS = ['RPM', 'SPEED', 'COOLANT', 'INTAKE_T', 'THROTTLE', 'MISFIRE'];

	let ws: WebSocket | null = null;

	function connect() {
		ws = new WebSocket('ws://localhost:8000/ws');

		ws.onopen = () => {
			status = 'open';
		};

		ws.onmessage = (event) => {
			try {
				data = JSON.parse(event.data) as LiveData;
			} catch {
				// ignore malformed frames
			}
		};

		ws.onclose = () => {
			status = 'closed';
		};

		ws.onerror = () => {
			status = 'error';
		};
	}

	onMount(connect);

	onDestroy(() => {
		ws?.close();
	});
</script>

<main>
	<h1>OBDsidian</h1>
	<p class="status" data-status={status}>ws: {status}</p>

	{#if data.RPM}
		<div class="rpm">{data.RPM.value.toFixed(0)} <span class="unit">rpm</span></div>
	{:else}
		<div class="rpm waiting">-- rpm</div>
	{/if}

	<div class="pids">
		{#each DISPLAY_PIDS.filter((k) => k !== 'RPM' && data[k]) as pid}
			<div class="pid-card">
				<span class="label">{pid}</span>
				<span class="value">{data[pid].value.toFixed(1)}</span>
				<span class="unit">{data[pid].unit}</span>
			</div>
		{/each}
	</div>
</main>

<style>
	main {
		font-family: monospace;
		padding: 2rem;
		background: #0d0d0d;
		color: #e0e0e0;
		min-height: 100vh;
	}

	h1 {
		font-size: 1.25rem;
		margin: 0 0 0.5rem;
		color: #888;
	}

	.status {
		font-size: 0.75rem;
		margin: 0 0 2rem;
		color: #555;
	}

	.status[data-status='open'] { color: #4caf50; }
	.status[data-status='error'] { color: #f44336; }
	.status[data-status='closed'] { color: #ff9800; }

	.rpm {
		font-size: 5rem;
		font-weight: bold;
		letter-spacing: -2px;
		color: #fff;
		margin-bottom: 2rem;
	}

	.rpm.waiting {
		color: #333;
	}

	.rpm .unit {
		font-size: 1.5rem;
		color: #888;
	}

	.pids {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.pid-card {
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		padding: 0.75rem 1rem;
		min-width: 120px;
		display: flex;
		flex-direction: column;
	}

	.label {
		font-size: 0.65rem;
		color: #666;
		text-transform: uppercase;
		letter-spacing: 1px;
		margin-bottom: 0.25rem;
	}

	.value {
		font-size: 1.75rem;
		color: #e0e0e0;
	}

	.unit {
		font-size: 0.75rem;
		color: #555;
	}
</style>
