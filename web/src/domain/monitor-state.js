import { parseDate } from './contract.js';

export class MonitorState {
  constructor(raw = {}) {
    this.initialized = Boolean(raw.initialized);
    this.lastRun = parseDate(raw.ultima_ejecucion);
    this.lastSuccess = parseDate(raw.ultima_ejecucion_exitosa);
    this.lastError = raw.ultimo_error || null;
    this.consecutiveFailures = Number(raw.fallos_consecutivos || 0);
    this.totalContracts = Number(raw.total_contratos || 0);
    this.knownIds = new Set((raw.contratos_conocidos || []).map(String));
    this.recentIds = new Set((raw.ultimos_contratos_nuevos || []).map(String));
  }

  get health() {
    if (!this.initialized) return 'not_initialized';
    if (this.lastError || this.consecutiveFailures > 0) return 'error';
    return 'healthy';
  }
}
