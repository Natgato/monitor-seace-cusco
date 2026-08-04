export class ContractItem {
  constructor(raw) {
    if (!raw?.idContrato) throw new TypeError('El ítem necesita idContrato');
    this.contractId = String(raw.idContrato);
    this.id = String(raw.idItem || `${raw.numero_item || ''}-${raw.codigo_cubso || ''}`);
    this.number = raw.numero_item || null;
    this.cubso = raw.codigo_cubso || null;
    this.description = raw.descripcion_item || 'Descripción no informada';
    this.quantity = raw.cantidad || null;
    this.unit = raw.unidad_medida || null;
    this.currency = raw.moneda || null;
    this.amount = raw.monto || null;
    Object.freeze(this);
  }
}
