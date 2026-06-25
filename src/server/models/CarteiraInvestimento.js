const path = require('path');
const Database = require('better-sqlite3');

const dbPath = path.resolve(__dirname, '../../data/controle-financeiro.sqlite');
const db = new Database(dbPath);

db.exec(`
CREATE TABLE IF NOT EXISTS portfolio_investimentos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  empresa TEXT NOT NULL,
  ativo TEXT NOT NULL UNIQUE,
  quantidade INTEGER NOT NULL,
  meta REAL NOT NULL,
  ramo TEXT,
  grupo TEXT,
  criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_auditoria (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  evento TEXT NOT NULL,
  detalhe TEXT,
  criado_em TEXT DEFAULT CURRENT_TIMESTAMP
);
`);

function normalizeRow(row) {
  return {
    id: row.id,
    empresa: row.empresa,
    ativo: row.ativo,
    quantidade: Number(row.quantidade),
    meta: Number(row.meta),
    ramo: row.ramo,
    grupo: row.grupo,
    criado_em: row.criado_em,
    atualizado_em: row.atualizado_em,
  };
}

function all() {
  return db
    .prepare('SELECT * FROM portfolio_investimentos ORDER BY quantidade DESC, ativo ASC')
    .all()
    .map(normalizeRow);
}

function upsert(asset) {
  const stmt = db.prepare(`
    INSERT INTO portfolio_investimentos (empresa, ativo, quantidade, meta, ramo, grupo)
    VALUES (@empresa, @ativo, @quantidade, @meta, @ramo, @grupo)
    ON CONFLICT(ativo) DO UPDATE SET
      empresa=excluded.empresa,
      quantidade=excluded.quantidade,
      meta=excluded.meta,
      ramo=excluded.ramo,
      grupo=excluded.grupo,
      atualizado_em=CURRENT_TIMESTAMP
  `);
  stmt.run(asset);
}

function clearPortfolio() {
  db.prepare('DELETE FROM portfolio_investimentos').run();
  recordAudit('import', 'Carteira de investimento reiniciada durante importação CSV');
}

function importCsv(csv) {
  const lines = csv
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  if (lines.length <= 1) {
    throw new Error('CSV deve ter cabeçalho e pelo menos uma linha de ativo.');
  }

  const [header, ...rows] = lines;
  const columns = header
    .split(',')
    .map((value) => value.trim().toLowerCase());

  const expectedHeader = ['empresa', 'ativo', 'quantidade', 'meta', 'ramo', 'grupo'];
  if (columns.length !== expectedHeader.length) {
    throw new Error('CSV com formato inválido.');
  }

  clearPortfolio();

  const insertStmt = db.prepare(`
    INSERT INTO portfolio_investimentos (empresa, ativo, quantidade, meta, ramo, grupo)
    VALUES (?, ?, ?, ?, ?, ?)
  `);

  const tx = db.transaction((rowsData) => {
    rowsData.forEach((line) => {
      const [empresa, ativo, quantidade, meta, ramo, grupo] = line
        .split(',')
        .map((value) => value.trim());
      if (!ativo || !quantidade || !meta) return;
      insertStmt.run(
        empresa,
        ativo,
        Number(quantidade),
        Number(meta),
        ramo,
        grupo
      );
    });
  });

  tx(rows);
  recordAudit('import', 'Dados importados do CSV e substituíram a carteira existente');
}

function exportCsv() {
  const rows = all();
  const header = 'Empresa,Ativo,Quantidade,Meta,Ramo,Grupo';
  const data = rows
    .map((asset) =>
      [asset.empresa, asset.ativo, asset.quantidade, asset.meta, asset.ramo, asset.grupo]
        .map((value) => `"${String(value || '').replace(/"/g, '""')}"`)
        .join(',')
    )
    .join('\n');
  return `${header}\n${data}`;
}

function recordAudit(evento, detalhe) {
  db.prepare(`
    INSERT INTO portfolio_auditoria (evento, detalhe)
    VALUES (?, ?)
  `).run(evento, detalhe || '');
}

function allAudit() {
  return db
    .prepare('SELECT * FROM portfolio_auditoria ORDER BY criado_em DESC LIMIT 100')
    .all();
}

function updateQuantities(updates) {
  const stmt = db.prepare(`
    UPDATE portfolio_investimentos
    SET quantidade = @quantidade,
        atualizado_em = CURRENT_TIMESTAMP
    WHERE ativo = @ativo
  `);

  const tx = db.transaction((rows) => {
    rows.forEach((row) => stmt.run(row));
  });

  tx(updates);
  recordAudit('investimento', `Confirmação de investimento aplicada em ${updates.length} ativos`);
}

module.exports = {
  all,
  upsert,
  importCsv,
  exportCsv,
  recordAudit,
  allAudit,
  updateQuantities,
};
