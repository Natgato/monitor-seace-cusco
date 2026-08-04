import { LoadDashboard } from './application/load-dashboard.js';
import { FilterContracts } from './application/filter-contracts.js';
import { GetContractDetail } from './application/get-contract-detail.js';
import { QueryContracts } from './application/query-contracts.js';
import { StaticDataRepository } from './infrastructure/static-data-repository.js';
import { DashboardView } from './presentation/dashboard-view.js';
import { DashboardController } from './presentation/dashboard-controller.js';

const repository = new StaticDataRepository({
  contractsUrl: '../data/contrataciones.csv',
  itemsUrl: '../data/items.csv',
  stateUrl: '../data/estado.json',
});

const controller = new DashboardController({
  loadDashboard: new LoadDashboard(repository),
  filterContracts: new FilterContracts(),
  getContractDetail: new GetContractDetail(),
  queryContracts: new QueryContracts(),
  view: new DashboardView(),
});

controller.start();
