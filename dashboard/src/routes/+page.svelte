<script>
  import { onMount } from 'svelte';
  import { connected, data, startTelemetry } from '$lib/telemetry.js';

  onMount(() => startTelemetry());

  // PID display config: label, unit override, max (for progress bar), color
  const FAST = [
    { pid: 'RPM',      label: 'RPM',      max: 7000, color: '#e84040' },
    { pid: 'SPEED',    label: 'Speed',    max: 120,  color: '#4096e8' },
    { pid: 'THROTTLE', label: 'Throttle', max: 100,  color: '#40c87a' },
  ];

  const SLOW = [
    { pid: 'COOLANT_T', label: 'Coolant',    warnAbove: 220 },
    { pid: 'INTAKE_T',  label: 'Intake Air', warnAbove: null },
    { pid: 'SHORT_FT',  label: 'Short FT',   warnAbove: null, signed: true },
    { pid: 'LONG_FT',   label: 'Long FT',    warnAbove: null, signed: true },
  ];

  function pct(value, max) {
    return Math.min(100, Math.max(0, (value / max) * 100)).toFixed(1);
  }

  function fmtValue(entry, pidData) {
    if (!pidData) return '—';
    const v = pidData.value;
    return entry.signed && v > 0 ? `+${v}` : `${v}`;
  }
</script>

<svelte:head>
  <title>OBDsidian</title>
</svelte:head>

<main>
  <header>
    <h1>OBDsidian</h1>
    <span class="status" class:live={$connected}>
      {$connected ? '● Live' : '○ Disconnected'}
    </span>
  </header>

  <!-- Fast PIDs -->
  <section class="fast-grid">
    {#each FAST as entry}
      {@const pid = $data[entry.pid]}
      <div class="gauge-card">
        <div class="gauge-label">{entry.label}</div>
        <div class="gauge-value" style="color: {entry.color}">
          {pid ? pid.value : '—'}
          <span class="gauge-unit">{pid ? pid.unit : ''}</span>
        </div>
        <div class="bar-track">
          <div
            class="bar-fill"
            style="width: {pid ? pct(pid.value, entry.max) : 0}%; background: {entry.color}"
          ></div>
        </div>
      </div>
    {/each}
  </section>

  <!-- Slow PIDs -->
  <section class="slow-grid">
    {#each SLOW as entry}
      {@const pid = $data[entry.pid]}
      <div class="small-card" class:warn={entry.warnAbove && pid && pid.value > entry.warnAbove}>
        <div class="small-label">{entry.label}</div>
        <div class="small-value">
          {fmtValue(entry, pid)}
          <span class="small-unit">{pid ? pid.unit : ''}</span>
        </div>
      </div>
    {/each}
  </section>

  <!-- Misfire -->
  {#if $data['MISFIRE']}
    <section class="misfire">
      <span class="small-label">Misfire / DTC flags</span>
      <span class="small-value">{$data['MISFIRE'].value}</span>
    </section>
  {/if}
</main>

<style>
  :global(*, *::before, *::after) {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  :global(body) {
    background: #0d0d0f;
    color: #e8e8e8;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }

  main {
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  /* ── Header ── */
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  h1 {
    font-size: 1.4rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #fff;
  }

  .status {
    font-size: 0.8rem;
    letter-spacing: 0.06em;
    color: #555;
    transition: color 0.3s;
  }

  .status.live {
    color: #40c87a;
  }

  /* ── Fast PIDs ── */
  .fast-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }

  .gauge-card {
    background: #161619;
    border: 1px solid #222;
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .gauge-label {
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #666;
  }

  .gauge-value {
    font-size: 2.4rem;
    font-weight: 600;
    line-height: 1;
  }

  .gauge-unit {
    font-size: 0.9rem;
    font-weight: 400;
    color: #888;
    margin-left: 0.25rem;
  }

  .bar-track {
    height: 4px;
    background: #2a2a2e;
    border-radius: 2px;
    overflow: hidden;
    margin-top: 0.25rem;
  }

  .bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.12s ease-out;
  }

  /* ── Slow PIDs ── */
  .slow-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
  }

  .small-card {
    background: #161619;
    border: 1px solid #222;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    transition: border-color 0.3s;
  }

  .small-card.warn {
    border-color: #e84040;
  }

  .small-label {
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #666;
  }

  .small-value {
    font-size: 1.5rem;
    font-weight: 500;
  }

  .small-unit {
    font-size: 0.75rem;
    color: #888;
    margin-left: 0.2rem;
  }

  /* ── Misfire ── */
  .misfire {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: #161619;
    border: 1px solid #222;
    border-radius: 8px;
    padding: 0.75rem 1.25rem;
  }

  /* ── Responsive ── */
  @media (max-width: 600px) {
    .fast-grid {
      grid-template-columns: 1fr;
    }
    .slow-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
