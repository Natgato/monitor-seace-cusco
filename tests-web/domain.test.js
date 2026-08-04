import test from 'node:test';
import assert from 'node:assert/strict';
import { Contract } from '../web/src/domain/contract.js';
import { FilterContracts } from '../web/src/application/filter-contracts.js';
import { QueryContracts } from '../web/src/application/query-contracts.js';
import { parseCsv } from '../web/src/infrastructure/csv-parser.js';

const reference = new Date('2026-08-05T10:00:00-05:00');
const contract = new Contract({
  idContrato: '1', codigo_contratacion: 'CM-1', estado: 'Vigente', entidad: 'Municipalidad del Cusco',
  descripcion: 'Adquisición de material afirmado', provincia: 'Cusco', fecha_vencimiento: '2026-08-05T20:00:00-05:00',
});

test('la entidad calcula vencimientos sin depender de la vista', () => {
  assert.equal(contract.isActive(), true);
  assert.equal(contract.isOpen(reference), true);
  assert.equal(contract.expiresWithin(24, reference), true);
});

test('el estado efectivo no confunde Vigente de SEACE con un plazo vencido', () => {
  const expired = new Contract({ idContrato: '2', estado: 'Vigente', fecha_vencimiento: '2026-08-04T20:00:00-05:00' });
  assert.equal(expired.isOpen(reference), false);
  assert.equal(expired.effectiveStatus(reference), 'Plazo vencido');
});

test('el caso de uso filtra texto sin depender de tildes', () => {
  const result = new FilterContracts().execute([contract], { query: 'adquisicion', status: 'open', province: '', urgentOnly: false }, reference);
  assert.equal(result.length, 1);
});

test('el asistente local consulta los datos del dominio', () => {
  const result = new QueryContracts().execute('material afirmado', { contracts: [contract], reference });
  assert.equal(result.contracts[0].id, '1');
});

test('el parser CSV respeta comas y comillas', () => {
  assert.deepEqual(parseCsv('id,nombre\n1,"Cusco, Perú"\n'), [{ id: '1', nombre: 'Cusco, Perú' }]);
});
