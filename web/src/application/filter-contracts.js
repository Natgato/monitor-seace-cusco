export class FilterContracts {
  execute(contracts, filters, reference = new Date()) {
    return contracts.filter(contract => {
      if (!contract.matches(filters.query)) return false;
      if (filters.status === 'open' && !contract.isOpen(reference)) return false;
      if (filters.status === 'expired' && !contract.isExpired(reference)) return false;
      if (filters.province && contract.province !== filters.province) return false;
      if (filters.urgentOnly && !contract.expiresWithin(24, reference)) return false;
      return true;
    }).sort((a, b) => {
      if (!a.expiresAt) return 1;
      if (!b.expiresAt) return -1;
      return a.expiresAt - b.expiresAt;
    });
  }
}
