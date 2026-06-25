const path = require('path');
const Database = require('better-sqlite3');

const dbPath = path.resolve(__dirname, '../../../data/controle-financeiro.sqlite');
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

console.log('Migration carteira de investimento aplicada com sucesso.');
