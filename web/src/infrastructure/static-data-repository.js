import { Contract } from '../domain/contract.js';
import { ContractItem } from '../domain/item.js';
import { MonitorState } from '../domain/monitor-state.js';
import { parseCsv } from './csv-parser.js';

export class StaticDataRepository {
  constructor({ contractsUrl, itemsUrl, stateUrl, fetcher = (...args) => globalThis.fetch(...args) }) {
    this.urls = { contractsUrl, itemsUrl, stateUrl };
    this.fetcher = fetcher;
  }

  async getContractsWithItems() {
    const [contractsText, itemsText] = await Promise.all([
      this.#read(this.urls.contractsUrl, 'text'),
      this.#read(this.urls.itemsUrl, 'text'),
    ]);
    return {
      contracts: parseCsv(contractsText).map(row => new Contract(row)),
      items: parseCsv(itemsText).map(row => new ContractItem(row)),
    };
  }

  async getMonitorState() { return new MonitorState(await this.#read(this.urls.stateUrl, 'json')); }

  async #read(url, format) {
    const response = await this.fetcher(url, { cache: 'no-store' });
    if (!response.ok) throw new Error(`No se pudo cargar ${url} (HTTP ${response.status})`);
    return format === 'json' ? response.json() : response.text();
  }
}
