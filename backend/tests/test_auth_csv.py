import unittest
from fastapi.testclient import TestClient
import pyotp
import io
from datetime import datetime

from backend.app.main import app, ACTIVE_SESSIONS
from backend.app.database import SessionLocal, engine
from backend.app.models import Base, User, Transacao

class TestAuthAndCSV(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Garante que as tabelas estejam criadas no banco de testes (ou banco local)
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        # Limpa usuários e transações de teste
        self.db.query(User).filter(User.username.like("testuser%")).delete(synchronize_session=False)
        self.db.query(Transacao).delete()
        self.db.commit()
        ACTIVE_SESSIONS.clear()

    def _criar_usuario_autenticado(self, username="testuser_projection"):
        user = User(
            username=username,
            password_hash="unused",
            totp_secret="unused",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        session_token = f"token_{username}"
        ACTIVE_SESSIONS[session_token] = username
        return user, {"Authorization": f"Bearer {session_token}"}

    def test_complete_auth_flow_and_csv_import_export(self):
        username = "testuser_1"
        password = "securepassword123"

        # 1. Registro de Novo Usuário
        reg_response = self.client.post(
            "/api/auth/register",
            json={"username": username, "password": password}
        )
        self.assertEqual(reg_response.status_code, 200)
        reg_data = reg_response.json()
        self.assertEqual(reg_data["username"], username)
        self.assertIn("totp_secret", reg_data)
        self.assertIn("totp_uri", reg_data)

        totp_secret = reg_data["totp_secret"]

        # 2. Login - Etapa 1
        login1_response = self.client.post(
            "/api/auth/login/step1",
            json={"username": username, "password": password}
        )
        self.assertEqual(login1_response.status_code, 200)
        self.assertTrue(login1_response.json()["success"])

        # 3. Login - Etapa 2 (2FA)
        totp = pyotp.TOTP(totp_secret)
        code = totp.now()

        login2_response = self.client.post(
            "/api/auth/login/step2",
            json={"username": username, "code": code}
        )
        self.assertEqual(login2_response.status_code, 200)
        login2_data = login2_response.json()
        self.assertTrue(login2_data["success"])
        self.assertIn("session_token", login2_data)
        
        session_token = login2_data["session_token"]
        self.assertIn(session_token, ACTIVE_SESSIONS)
        self.assertEqual(ACTIVE_SESSIONS[session_token], username)

        # 4. Exportar CSV (Sem dados ainda, deve retornar apenas cabeçalho)
        headers = {"Authorization": f"Bearer {session_token}"}
        export_response = self.client.get("/api/transacoes/download", headers=headers)
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("text/csv", export_response.headers["content-type"])
        self.assertIn("Data,Item,Tipo,Categoria,Valor,Pago", export_response.text)

        # 5. Importar CSV
        csv_content = (
            "Data,Item,Tipo,Categoria,Valor,Pago\n"
            "01/05/2026,Aluguel,Despesa,Moradia,1200.50,True\n"
            "02/05/2026,Salário,Receita,Trabalho,5000.00,False\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        
        upload_response = self.client.post(
            "/api/transacoes/upload",
            headers=headers,
            files={"file": ("transacoes.csv", csv_file, "text/csv")}
        )
        self.assertEqual(upload_response.status_code, 200)
        upload_data = upload_response.json()
        self.assertTrue(upload_data["success"])
        self.assertEqual(upload_data["count"], 2)

        # Verifica se as transações foram salvas no banco
        db_transacoes = self.db.query(Transacao).all()
        self.assertEqual(len(db_transacoes), 2)
        self.assertEqual(db_transacoes[0].item, "Aluguel")
        self.assertEqual(db_transacoes[0].valor, 1200.50)
        self.assertTrue(db_transacoes[0].pago)
        self.assertEqual(db_transacoes[0].ano, 2026)
        self.assertEqual(db_transacoes[0].mes, 5)

        self.assertEqual(db_transacoes[1].item, "Salário")
        self.assertEqual(db_transacoes[1].valor, 5000.00)
        self.assertFalse(db_transacoes[1].pago)

        # 6. Redefinição de Senha
        reset_code = totp.now()
        new_password = "evenmoreseriouspassword999"
        
        reset_response = self.client.post(
            "/api/auth/reset-password",
            json={"username": username, "code": reset_code, "new_password": new_password}
        )
        self.assertEqual(reset_response.status_code, 200)
        self.assertTrue(reset_response.json()["success"])

        # Tenta login passo 1 com senha antiga (deve falhar)
        login_fail = self.client.post(
            "/api/auth/login/step1",
            json={"username": username, "password": password}
        )
        self.assertEqual(login_fail.status_code, 401)

        # Tenta login passo 1 com nova senha (deve funcionar)
        login_success = self.client.post(
            "/api/auth/login/step1",
            json={"username": username, "password": new_password}
        )
        self.assertEqual(login_success.status_code, 200)

        # 7. Logout
        logout_response = self.client.post(
            "/api/auth/logout",
            cookies={"session_token": session_token}
        )
        self.assertEqual(logout_response.status_code, 200)
        self.assertNotIn(session_token, ACTIVE_SESSIONS)

    def test_future_year_empty_projects_only_previous_december_to_january(self):
        user, headers = self._criar_usuario_autenticado()
        ano_atual = datetime.now().year
        ano_futuro = ano_atual + 1
        dezembro = [
            Transacao(
                ano=ano_atual,
                mes=12,
                item="Salário",
                tipo="Receita",
                categoria="Trabalho",
                valor=5000.00,
                pago=True,
                owner_id=user.id,
            ),
            Transacao(
                ano=ano_atual,
                mes=12,
                item="Aluguel",
                tipo="Despesa",
                categoria="Moradia",
                valor=1200.00,
                pago=True,
                owner_id=user.id,
            ),
            Transacao(
                ano=ano_atual,
                mes=11,
                item="Internet",
                tipo="Despesa",
                categoria="Casa",
                valor=100.00,
                pago=True,
                owner_id=user.id,
            ),
        ]
        self.db.add_all(dezembro)
        self.db.commit()

        response = self.client.get(f"/api/transacoes?ano={ano_futuro}", headers=headers)

        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertEqual(len(dados), 2)
        self.assertEqual({tx["mes"] for tx in dados}, {1})
        self.assertEqual({tx["item"] for tx in dados}, {"Salário", "Aluguel"})
        self.assertTrue(all(tx["ano"] == ano_futuro for tx in dados))
        self.assertTrue(all(tx["pago"] is False for tx in dados))
        self.assertEqual(self.db.query(Transacao).filter(Transacao.ano == ano_futuro).count(), 0)

    def test_future_year_with_saved_transactions_does_not_auto_project(self):
        user, headers = self._criar_usuario_autenticado()
        ano_atual = datetime.now().year
        ano_futuro = ano_atual + 1
        self.db.add_all([
            Transacao(
                ano=ano_atual,
                mes=12,
                item="Salário",
                tipo="Receita",
                categoria="Trabalho",
                valor=5000.00,
                pago=True,
                owner_id=user.id,
            ),
            Transacao(
                ano=ano_futuro,
                mes=3,
                item="Viagem",
                tipo="Despesa",
                categoria="Lazer",
                valor=800.00,
                pago=False,
                owner_id=user.id,
            ),
        ])
        self.db.commit()

        response = self.client.get(f"/api/transacoes?ano={ano_futuro}", headers=headers)

        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["mes"], 3)
        self.assertEqual(dados[0]["item"], "Viagem")

if __name__ == "__main__":
    unittest.main()
