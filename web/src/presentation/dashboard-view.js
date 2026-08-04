const DATE = new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima' });
const NUMBER = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 2 });

export class DashboardView {
  constructor(documentRef = document) { this.document = documentRef; }

  bind(handlers) {
    const byId = id => this.document.getElementById(id);
    byId('reloadButton').addEventListener('click', handlers.reload);
    byId('retryButton').addEventListener('click', handlers.reload);
    byId('filterForm').addEventListener('input', handlers.filter);
    byId('clearFilters').addEventListener('click', handlers.clearFilters);
    byId('contractRows').addEventListener('click', event => {
      const button = event.target.closest('[data-contract-id]');
      if (button) handlers.openDetail(button.dataset.contractId);
    });
    byId('closeDetail').addEventListener('click', () => byId('detailDialog').close());
    byId('detailDialog').addEventListener('click', event => { if (event.target === byId('detailDialog')) byId('detailDialog').close(); });
    byId('assistantButton').addEventListener('click', handlers.toggleAssistant);
    byId('closeAssistant').addEventListener('click', handlers.toggleAssistant);
    byId('assistantForm').addEventListener('submit', event => { event.preventDefault(); handlers.queryAssistant(byId('assistantInput').value); });
    this.document.querySelectorAll('[data-query]').forEach(button => button.addEventListener('click', () => handlers.queryAssistant(button.dataset.query)));
    byId('menuButton').addEventListener('click', () => {
      const open = byId('sidebar').classList.toggle('open');
      byId('menuButton').setAttribute('aria-expanded', String(open));
    });
  }

  filters() {
    return { query: value('searchInput'), status: value('statusFilter'), province: value('provinceFilter'), urgentOnly: this.document.getElementById('urgentFilter').checked };
  }

  clearFilters() {
    this.document.getElementById('filterForm').reset();
  }

  showLoading() { this.#state('loadingState'); this.document.getElementById('reloadButton').disabled = true; }
  showError(error) { this.#state('errorState'); this.document.getElementById('errorMessage').textContent = error.message; this.document.getElementById('reloadButton').disabled = false; }

  renderDashboard(dashboard) {
    this.document.getElementById('reloadButton').disabled = false;
    text('totalMetric', dashboard.metrics.total);
    text('newMetric', dashboard.metrics.newCount);
    text('urgentMetric', dashboard.metrics.urgent);
    text('entityMetric', dashboard.metrics.entities);
    text('lastUpdate', dashboard.state.lastSuccess ? `Última actualización correcta: ${DATE.format(dashboard.state.lastSuccess)}` : 'El monitor todavía no registra una ejecución completa');
    this.#health(dashboard.state);
    this.#provinces(dashboard.contracts);
    this.#radar(dashboard.radar, dashboard.reference);
  }

  renderContracts(contracts, dashboard) {
    text('resultCount', `${contracts.length} resultado${contracts.length === 1 ? '' : 's'}`);
    if (!contracts.length) { this.#state('emptyState'); return; }
    const rows = this.document.getElementById('contractRows');
    rows.replaceChildren(...contracts.map(contract => this.#row(contract, dashboard)));
    this.#state('tableContainer');
  }

  showDetail({ contract, items }) {
    text('detailCode', contract.code);
    const content = this.document.getElementById('detailContent');
    content.replaceChildren(this.#detail(contract, items));
    this.document.getElementById('detailDialog').showModal();
  }

  toggleAssistant() { this.document.querySelector('.shell').classList.toggle('assistant-open'); }

  appendAssistant(question, result) {
    const container = this.document.getElementById('assistantMessages');
    const user = element('div', 'user-message', question);
    const answer = element('div', 'assistant-message');
    answer.append(element('div', '', result.text));
    result.contracts.forEach(contract => {
      const button = element('button', 'assistant-result', `${contract.code} · ${contract.entity}`);
      button.type = 'button'; button.dataset.contractId = contract.id;
      answer.append(button);
    });
    answer.addEventListener('click', event => {
      const button = event.target.closest('[data-contract-id]');
      if (button) this.document.dispatchEvent(new CustomEvent('assistant:detail', { detail: button.dataset.contractId }));
    });
    container.append(user, answer);
    this.document.getElementById('assistantInput').value = '';
    container.scrollTop = container.scrollHeight;
  }

  #state(activeId) {
    ['loadingState','emptyState','errorState','tableContainer'].forEach(id => this.document.getElementById(id).classList.toggle('hidden', id !== activeId));
  }

  #health(state) {
    const dot = this.document.getElementById('statusDot');
    dot.className = `status-dot ${state.health === 'healthy' ? 'ok' : state.health === 'error' ? 'error' : ''}`;
    text('statusLabel', state.health === 'healthy' ? 'Monitor operativo' : state.health === 'error' ? 'Monitor con errores' : 'Pendiente de inicializar');
  }

  #provinces(contracts) {
    const select = this.document.getElementById('provinceFilter');
    const current = select.value;
    const provinces = [...new Set(contracts.map(c => c.province).filter(Boolean))].sort((a,b) => a.localeCompare(b,'es'));
    select.replaceChildren(option('', 'Todas las provincias'), ...provinces.map(name => option(name, name)));
    select.value = current;
  }

  #radar(contracts, reference) {
    const track = this.document.getElementById('radarTrack'); track.replaceChildren();
    contracts.forEach(contract => {
      const hours = contract.hoursRemaining(reference);
      const pin = element('button', `radar-pin ${hours <= 12 ? 'urgent' : hours <= 24 ? 'soon' : ''}`);
      pin.type = 'button'; pin.style.left = `${Math.max(1, Math.min(99, hours / 72 * 100))}%`;
      pin.title = `${contract.code}: ${remaining(contract, reference)}`;
      pin.setAttribute('role', 'listitem'); pin.dataset.contractId = contract.id;
      pin.addEventListener('click', () => this.document.dispatchEvent(new CustomEvent('radar:detail', { detail: contract.id })));
      track.append(pin);
    });
  }

  #row(contract, dashboard) {
    const row = this.document.createElement('tr');
    const hours = contract.hoursRemaining(dashboard.reference);
    row.append(
      cell(pill(contract, hours)),
      cell(element('span','mono',contract.code)),
      cell(contractTitle(contract)),
      cell(element('span','mono',formatDate(contract.expiresAt))),
      cell(element('span',`mono ${hours !== null && hours <= 24 ? 'warning-text' : ''}`,remaining(contract,dashboard.reference))),
      cell(element('span','mono',String(dashboard.itemCount.get(contract.id) || 0))),
      cell(action(contract.id)),
    );
    return row;
  }

  #detail(contract, items) {
    const body = element('div','detail-body');
    body.append(element('p','detail-description',contract.description));
    const grid = element('div','detail-grid');
    [['Estado',contract.status],['Entidad',contract.entity],['Objeto',contract.objectType],['Ubicación',[contract.department,contract.province,contract.district].filter(Boolean).join(' / ') || 'No informada'],['Publicación',formatDate(contract.publishedAt)],['Vencimiento',formatDate(contract.expiresAt)],['Monto',contract.amount === null ? 'No informado' : `${contract.currency || ''} ${NUMBER.format(contract.amount)}`],['Ítems',String(items.length)]].forEach(([label,value]) => {
      const field=element('div','detail-field'); field.append(element('span','',label),element('strong','',value)); grid.append(field);
    });
    body.append(grid);
    if (items.length) {
      const heading=element('h3','',`Ítems (${items.length})`); body.append(heading);
      const table=element('table','detail-items'); const tbody=element('tbody');
      items.forEach(item => { const row=element('tr'); row.append(cell(item.number || '—'),cell(item.cubso || 'Sin CUBSO'),cell(item.description),cell(`${item.quantity || '—'} ${item.unit || ''}`)); tbody.append(row); });
      table.append(tbody); body.append(table);
    }
    if (contract.publicUrl) { const link=element('a','external-link','Abrir en SEACE ↗'); link.href=contract.publicUrl; link.target='_blank'; link.rel='noopener noreferrer'; body.append(link); }
    return body;
  }
}

function value(id){ return document.getElementById(id).value.trim(); }
function text(id,value){ document.getElementById(id).textContent=String(value); }
function element(tag,className='',content){ const node=document.createElement(tag); if(className) node.className=className; if(content!==undefined) node.textContent=content; return node; }
function cell(content){ const node=element('td'); node.append(content instanceof Node ? content : document.createTextNode(String(content))); return node; }
function option(value,label){ const node=element('option','',label); node.value=value; return node; }
function formatDate(value){ return value ? DATE.format(value) : 'No informada'; }
function remaining(contract,reference){ const hours=contract.hoursRemaining(reference); if(hours===null) return 'No informado'; if(hours<0) return 'Vencido'; if(hours<1) return 'Menos de 1 h'; const total=Math.floor(hours),days=Math.floor(total/24); return days ? `${days} d, ${total%24} h` : `${total} h`; }
function pill(contract,hours){ const cls=!contract.isActive()?'red':hours!==null&&hours<=24?'amber':'green'; return element('span',`pill ${cls}`,contract.status); }
function contractTitle(contract){ const wrapper=element('div','contract-title'); wrapper.append(element('strong','',contract.description),element('small','',contract.entity)); return wrapper; }
function action(id){ const button=element('button','row-action','Ver detalle →'); button.type='button'; button.dataset.contractId=id; return button; }
