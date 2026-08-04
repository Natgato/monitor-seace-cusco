import { normalize } from '../domain/contract.js';

export class QueryContracts {
  execute(question, dashboard) {
    const query = normalize(question);
    if (!query) return { text: 'Escribe una entidad, provincia, producto o plazo para buscar.', contracts: [] };

    if (query.includes('entidad') && (query.includes('mas') || query.includes('mayor'))) {
      const counts = new Map();
      dashboard.contracts.filter(c => c.isActive()).forEach(c => counts.set(c.entity, (counts.get(c.entity) || 0) + 1));
      const leaders = [...counts].sort((a, b) => b[1] - a[1]).slice(0, 5);
      return { text: leaders.length ? `Entidades con más oportunidades: ${leaders.map(([name, count]) => `${name} (${count})`).join(', ')}.` : 'No hay entidades disponibles todavía.', contracts: [] };
    }

    let matches;
    if (query.includes('24 hora') || query.includes('vence hoy')) {
      matches = dashboard.contracts.filter(c => c.isActive() && c.expiresWithin(24, dashboard.reference));
    } else if (query.includes('semana') || query.includes('7 dia')) {
      matches = dashboard.contracts.filter(c => c.isActive() && c.expiresWithin(168, dashboard.reference));
    } else {
      const stopWords = new Set(['que','cuales','hay','los','las','de','del','en','contratos','contrataciones','muestrame','buscar','busca']);
      const terms = query.split(/\s+/).filter(term => term.length > 2 && !stopWords.has(term));
      matches = dashboard.contracts.filter(c => terms.length && terms.every(term => c.matches(term)));
    }
    matches = matches.slice(0, 6);
    return { text: matches.length ? `Encontré ${matches.length} coincidencia${matches.length === 1 ? '' : 's'} en los datos actuales.` : 'No encontré coincidencias en las contrataciones recopiladas.', contracts: matches };
  }
}
