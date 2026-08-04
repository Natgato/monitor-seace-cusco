export class GetContractDetail {
  execute(contractId, dashboard) {
    const contract = dashboard.contracts.find(candidate => candidate.id === String(contractId));
    if (!contract) throw new Error('La contratación solicitada ya no está disponible');
    return { contract, items: dashboard.items.filter(item => item.contractId === contract.id) };
  }
}
