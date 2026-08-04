export class DashboardController {
  constructor({ loadDashboard, filterContracts, getContractDetail, queryContracts, view, documentRef = document }) {
    Object.assign(this, { loadDashboard, filterContracts, getContractDetail, queryContracts, view, documentRef });
    this.dashboard = null;
  }

  start() {
    this.view.bind({
      reload: () => this.load(),
      filter: () => this.applyFilters(),
      clearFilters: () => { this.view.clearFilters(); this.applyFilters(); },
      openDetail: id => this.openDetail(id),
      toggleAssistant: () => this.view.toggleAssistant(),
      queryAssistant: question => this.ask(question),
    });
    this.documentRef.addEventListener('radar:detail', event => this.openDetail(event.detail));
    this.documentRef.addEventListener('assistant:detail', event => this.openDetail(event.detail));
    return this.load();
  }

  async load() {
    this.view.showLoading();
    try {
      this.dashboard = await this.loadDashboard.execute();
      this.view.renderDashboard(this.dashboard);
      this.applyFilters();
    } catch (error) { this.view.showError(error instanceof Error ? error : new Error(String(error))); }
  }

  applyFilters() {
    if (!this.dashboard) return;
    const contracts = this.filterContracts.execute(this.dashboard.contracts, this.view.filters(), this.dashboard.reference);
    this.view.renderContracts(contracts, this.dashboard);
  }

  openDetail(id) {
    if (!this.dashboard) return;
    try { this.view.showDetail(this.getContractDetail.execute(id, this.dashboard)); }
    catch (error) { this.view.showError(error); }
  }

  ask(question) {
    if (!this.dashboard || !question.trim()) return;
    this.view.appendAssistant(question, this.queryContracts.execute(question, this.dashboard));
  }
}
