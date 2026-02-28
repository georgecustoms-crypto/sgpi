import flet as ft
import sqlite3
import shutil
from datetime import datetime
import os
from openpyxl import load_workbook

# ================= CONFIG =================
APP_FOLDER = os.path.join(os.environ["LOCALAPPDATA"], "SGPI")
os.makedirs(APP_FOLDER, exist_ok=True)
DB_NAME = os.path.join(APP_FOLDER, "sgpi.db")

# ================= BANCO =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS salas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proprietario TEXT,
            andar TEXT,
            sala TEXT,
            empresa TEXT,
            tipo_escritorio TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            senha TEXT,
            nivel TEXT
        )
    """)

    cursor.execute("SELECT * FROM usuarios WHERE usuario='admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (usuario, senha, nivel) VALUES (?, ?, ?)",
            ("admin", "123", "admin")
        )

    conn.commit()
    conn.close()

# ================= FUNÇÕES BANCO =================
def verificar_login(usuario, senha):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT nivel FROM usuarios WHERE usuario=? AND senha=?", (usuario, senha))
    resultado = cursor.fetchone()
    conn.close()
    return resultado

def listar_usuarios():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, usuario, nivel FROM usuarios")
    dados = cursor.fetchall()
    conn.close()
    return dados

def adicionar_usuario(usuario, senha, nivel):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO usuarios (usuario, senha, nivel) VALUES (?, ?, ?)", (usuario, senha, nivel))
    conn.commit()
    conn.close()

def excluir_usuario(uid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id=?", (uid,))
    conn.commit()
    conn.close()

def inserir_sala(p, a, s, e, t):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO salas (proprietario, andar, sala, empresa, tipo_escritorio)
        VALUES (?, ?, ?, ?, ?)
    """, (p, a, s, e, t))
    conn.commit()
    conn.close()

def buscar_salas(termo=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT proprietario, andar, sala, empresa, tipo_escritorio
        FROM salas
        WHERE empresa LIKE ? OR sala LIKE ? OR proprietario LIKE ?
    """, (f"%{termo}%", f"%{termo}%", f"%{termo}%"))
    dados = cursor.fetchall()
    conn.close()
    return dados

def realizar_backup():
    try:
        nome = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        caminho = os.path.join(APP_FOLDER, nome)
        shutil.copy2(DB_NAME, caminho)
        return caminho
    except:
        return None

def importar_salas_excel(caminho):
    if not os.path.exists(caminho):
        return 0

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    wb = load_workbook(caminho)
    sheet = wb.active

    total = 0
    for row in sheet.iter_rows(min_row=2, values_only=True):
        cursor.execute("""
            INSERT INTO salas (proprietario, andar, sala, empresa, tipo_escritorio)
            VALUES (?, ?, ?, ?, ?)
        """, row)
        total += 1

    conn.commit()
    conn.close()
    return total

# ================= APP =================
def main(page: ft.Page):

    page.title = "SGPI – Sistema de Gestão Predial Inteligente"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1100
    page.window_height = 750
    page.window_center()

    usuario_logado = {"nivel": None, "nome": ""}

    # ================= LOGIN =================
    def tela_login():
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        usuario = ft.TextField(label="Usuário", prefix_icon=ft.icons.PERSON, width=350)
        senha = ft.TextField(label="Senha", password=True, prefix_icon=ft.icons.LOCK, width=350)
        mensagem = ft.Text("")

        def entrar(e):
            resultado = verificar_login(usuario.value, senha.value)
            if resultado:
                usuario_logado["nivel"] = resultado[0]
                usuario_logado["nome"] = usuario.value
                dashboard()
            else:
                mensagem.value = "Usuário ou senha inválidos"
                mensagem.color = ft.colors.RED
                page.update()

        page.add(
            ft.Card(
                content=ft.Container(
                    padding=40,
                    width=450,
                    content=ft.Column([
                        ft.Text("Bem-vindo ao SGPI", size=24, weight="bold"),
                        ft.Text("Faça login para continuar"),
                        usuario,
                        senha,
                        ft.ElevatedButton("Entrar", icon=ft.icons.LOGIN, on_click=entrar),
                        mensagem
                    ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                )
            )
        )

    # ================= DASHBOARD =================
    def dashboard():
        page.clean()

        # ---------- TABELA SALAS ----------
        tabela = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Proprietário")),
                ft.DataColumn(ft.Text("Andar")),
                ft.DataColumn(ft.Text("Sala")),
                ft.DataColumn(ft.Text("Empresa")),
                ft.DataColumn(ft.Text("Tipo")),
            ],
            rows=[]
        )

        def atualizar(termo=""):
            tabela.rows.clear()
            for r in buscar_salas(termo):
                tabela.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(c))) for c in r]))
            page.update()

        campo_busca = ft.TextField(
            label="Buscar",
            prefix_icon=ft.icons.SEARCH,
            on_change=lambda e: atualizar(e.control.value)
        )

        # ---------- IMPORTAÇÃO ----------
        file_picker = ft.FilePicker()
        page.overlay.append(file_picker)

        def arquivo_escolhido(e):
            if e.files:
                total = importar_salas_excel(e.files[0].path)
                atualizar()
                page.snack_bar = ft.SnackBar(ft.Text(f"{total} registros importados!"))
                page.snack_bar.open = True
                page.update()

        file_picker.on_result = arquivo_escolhido

        # ---------- CADASTRO SALA ----------
        def abrir_cadastro(e):
            p = ft.TextField(label="Proprietário")
            a = ft.TextField(label="Andar")
            s = ft.TextField(label="Sala")
            em = ft.TextField(label="Empresa")
            t = ft.TextField(label="Tipo Escritório")

            def salvar(e):
                inserir_sala(p.value, a.value, s.value, em.value, t.value)
                dialog.open = False
                atualizar()
                page.update()

            dialog.content = ft.Column([p, a, s, em, t])
            dialog.actions = [ft.ElevatedButton("Salvar", on_click=salvar)]
            dialog.open = True
            page.update()

        dialog = ft.AlertDialog(modal=True)
        page.dialog = dialog

        # ---------- USUÁRIOS ----------
        tabela_usuarios = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Usuário")),
                ft.DataColumn(ft.Text("Nível")),
                ft.DataColumn(ft.Text("Excluir")),
            ],
            rows=[]
        )

        def atualizar_usuarios():
            tabela_usuarios.rows.clear()
            for uid, usuario, nivel in listar_usuarios():
                tabela_usuarios.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(usuario)),
                        ft.DataCell(ft.Text(nivel)),
                        ft.DataCell(ft.IconButton(
                            icon=ft.icons.DELETE,
                            on_click=lambda e, id=uid: deletar_usuario(id)
                        ))
                    ])
                )
            page.update()

        def deletar_usuario(uid):
            excluir_usuario(uid)
            atualizar_usuarios()

        def novo_usuario(e):
            u = ft.TextField(label="Usuário")
            s = ft.TextField(label="Senha")
            n = ft.Dropdown(label="Nível", options=[
                ft.dropdown.Option("admin"),
                ft.dropdown.Option("operador")
            ])

            def salvar(e):
                adicionar_usuario(u.value, s.value, n.value)
                dialog.open = False
                atualizar_usuarios()
                page.update()

            dialog.content = ft.Column([u, s, n])
            dialog.actions = [ft.ElevatedButton("Salvar", on_click=salvar)]
            dialog.open = True
            page.update()

        atualizar()
        atualizar_usuarios()

        tabs = [
            ft.Tab(text="Consulta", content=ft.Column([campo_busca, tabela])),
            ft.Tab(text="Admin Salas", content=ft.Column([
                ft.ElevatedButton("Cadastrar Sala", on_click=abrir_cadastro),
                ft.ElevatedButton("Importar Excel", on_click=lambda e: file_picker.pick_files(allowed_extensions=["xlsx"])),
                ft.ElevatedButton("Gerar Backup", on_click=lambda e: realizar_backup())
            ]))
        ]

        if usuario_logado["nivel"] == "admin":
            tabs.append(
                ft.Tab(text="Usuários", content=ft.Column([
                    ft.ElevatedButton("Novo Usuário", on_click=novo_usuario),
                    tabela_usuarios
                ]))
            )

        page.add(
            ft.AppBar(
                title=ft.Text("SGPI – Sistema de Gestão Predial Inteligente"),
                actions=[
                    ft.Text(f"Olá, {usuario_logado['nome']}"),
                    ft.IconButton(icon=ft.icons.LOGOUT, on_click=lambda e: tela_login())
                ]
            ),
            ft.Tabs(tabs=tabs)
        )

    tela_login()


if __name__ == "__main__":
    init_db()
    ft.app(
        target=main,
        view=ft.WEB_BROWSER,
        host="0.0.0.0",
        port=10000
    )