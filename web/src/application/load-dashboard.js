export class LoadDashboard {
  constructor(repository, clock = () => new Date()) { this.repository = repository; this.clock = clock; }

  async execute() {
    const [{ contracts, items }, state] = await Promise.all([
      this.repository.getContractsWithItems(),
      this.repository.getMonitorState(),
    ]);
    const reference = this.clock();
    const active = contracts.filter(contract => contract.isActive());
    const itemCount = new Map();
    for (const item of items) itemCount.set(item.contractId, (itemCount.get(item.contractId) || 0) + 1);
    return {
      contracts,
      items,
      state,
      reference,
      itemCount,
      metrics: {
        total: active.length,
        newCount: active.filter(contract => state.recentIds.has(contract.id)).length,
        urgent: active.filter(contract => contract.expiresWithin(24, reference)).length,
        entities: new Set(active.map(contract => contract.entity)).size,
      },
      radar: active.filter(contract => contract.expiresWithin(72, reference)).sort((a, b) => a.expiresAt - b.expiresAt),
    };
  }
}
