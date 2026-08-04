const LIMA_OFFSET = '-05:00';

export class Contract {
  constructor(raw) {
    if (!raw?.idContrato) throw new TypeError('La contratación necesita idContrato');
    this.id = String(raw.idContrato);
    this.code = raw.codigo_contratacion || 'Código no informado';
    this.status = (raw.estado || 'No informado').trim();
    this.objectType = raw.objeto_contratacion || 'No informado';
    this.entity = raw.entidad || 'Entidad no informada';
    this.taxId = raw.ruc_entidad || null;
    this.department = raw.departamento || null;
    this.province = raw.provincia || null;
    this.district = raw.distrito || null;
    this.publishedAt = parseDate(raw.fecha_publicacion);
    this.expiresAt = parseDate(raw.fecha_vencimiento);
    this.expiresRaw = raw.fecha_vencimiento_raw || null;
    this.currency = raw.moneda || null;
    this.amount = toNumber(raw.monto_referencial);
    this.description = raw.descripcion || 'Descripción no informada';
    this.publicUrl = raw.enlace_publico || null;
    this.updatedAt = parseDate(raw.fecha_ultima_actualizacion);
    Object.freeze(this);
  }

  isActive() { return this.status.toLocaleLowerCase('es').includes('vigente'); }
  hoursRemaining(reference = new Date()) { return this.expiresAt ? (this.expiresAt - reference) / 3_600_000 : null; }
  expiresWithin(hours, reference = new Date()) { const value = this.hoursRemaining(reference); return value !== null && value >= 0 && value <= hours; }
  matches(text) {
    const query = normalize(text);
    return !query || normalize([this.code, this.description, this.entity, this.province, this.district, this.objectType].join(' ')).includes(query);
  }
}

export function parseDate(value) {
  if (!value) return null;
  const text = String(value).trim();
  const iso = /^\d{4}-\d{2}-\d{2}T/.test(text) && !/[zZ]|[+-]\d\d:\d\d$/.test(text) ? `${text}${LIMA_OFFSET}` : text;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function normalize(value) {
  return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es').trim();
}

function toNumber(value) {
  if (value === '' || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
