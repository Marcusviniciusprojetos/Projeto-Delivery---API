import os
import sqlite3
from dotenv import load_dotenv

# 1. Ativa a leitura do arquivo .env único da raiz
load_dotenv()

# 2. Puxa o nome do banco do .env ou usa o valor padrão de fallback
DB_NAME = os.getenv("DATABASE_URL", "banco_de_dados_Usuários.db").replace("sqlite:///", "")

def conectar():
    # Abre a conexão com o arquivo do banco de dados SQLite
    conn = sqlite3.connect(DB_NAME)
    # Configura para retornar as linhas como dicionários (permite acessar por nome de coluna)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_banco():
    with conectar() as conexao:
        cursor = conexao.cursor()
        
        # Criação da tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                cpf TEXT PRIMARY KEY,
                nome_usuario TEXT NOT NULL,
                senha TEXT NOT NULL
            )
        ''')
        
        # Criação da tabela do cardápio
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                quantidade INTEGER NOT NULL
            )
        ''')
        
        # Criação da tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpf_cliente TEXT NOT NULL,
                nome_prato TEXT NOT NULL,
                quantidade_pedida INTEGER NOT NULL,
                valor_total REAL NOT NULL
            )
        ''')

        # Verifica se o cardápio está vazio para inserir os produtos iniciais
        cursor.execute("SELECT * FROM cardapio")
        if not cursor.fetchall():
            pratos_iniciais = [
                ("Hambúrguer", 29.90, 10),
                ("Pizza", 45.00, 10),
                ("Lasanha", 38.50, 10)
            ]
            cursor.executemany("INSERT INTO cardapio (nome, preco, quantidade) VALUES (?, ?, ?)", pratos_iniciais)
            conexao.commit()

        # --- MECANISMO INTERNO DE VERIFICAÇÃO E CORREÇÃO DE IDs ---
        
        # Busca produtos no cardápio com ID nulo, vazio ou zerado
        cursor.execute("SELECT rowid, nome FROM cardapio WHERE id IS NULL OR id = '' OR id = 0")
        produtos_sem_id = cursor.fetchall()
        
        if produtos_sem_id:
            for produto in produtos_sem_id:
                # Usa o rowid físico do SQLite para gerar e salvar um ID definitivo
                id_seguro_e_fixo = produto["rowid"]
                cursor.execute('''
                    UPDATE cardapio 
                    SET id = ? 
                    WHERE rowid = ?
                ''', (id_seguro_e_fixo, id_seguro_e_fixo))
            conexao.commit()

        # Busca pedidos com ID nulo, vazio ou zerado
        cursor.execute("SELECT rowid FROM pedidos WHERE id IS NULL OR id = '' OR id = 0")
        pedidos_sem_id = cursor.fetchall()
        
        if pedidos_sem_id:
            for pedido in pedidos_sem_id:
                id_pedido_fixo = pedido["rowid"]
                cursor.execute('''
                    UPDATE pedidos 
                    SET id = ? 
                    WHERE rowid = ?
                ''', (id_pedido_fixo, id_pedido_fixo))
            conexao.commit()

def fiscal_validar_seguranca_cadastro(cpf_usuario):
    # Remove espaços em branco nas pontas do texto do CPF
    cpf_limpo = cpf_usuario.strip()
    
    # Valida se o CPF possui exatamente 11 caracteres numéricos
    if len(cpf_limpo) != 11 or not cpf_limpo.isdigit():
        raise ValueError("erro-cpf-formato")
        
    with conectar() as conexao:
        cursor = conexao.cursor()
        # Busca se o CPF informado já existe na tabela de usuários
        cursor.execute('SELECT cpf FROM usuarios WHERE cpf = ?', (cpf_limpo,))
        if cursor.fetchone() is not None:
            raise ValueError("erro-cpf-duplicado")
            
    return cpf_limpo

def operario_salvar_usuario_no_banco(cpf, nome, senha):
    with conectar() as conexao:
        cursor = conexao.cursor()
        # Insere o novo usuário de forma definitiva no banco de dados
        cursor.execute('''
            INSERT INTO usuarios (cpf, nome_usuario, senha) VALUES (?, ?, ?)
        ''', (cpf, nome, senha))
        conexao.commit()

def fiscal_validar_login(login_cpf, login_user, login_senha):
    with conectar() as conexao:
        cursor = conexao.cursor()
        # Valida a autenticidade cruzando o CPF, usuário e senha informados
        cursor.execute('''
            SELECT cpf FROM usuarios WHERE cpf = ? AND nome_usuario = ? AND senha = ?
        ''', (login_cpf.strip(), login_user.strip(), login_senha.strip()))
        usuario = cursor.fetchone()
        
        if usuario is None:
            raise ValueError("erro-login-incorreto")
            
        return usuario["cpf"]

def buscar_nome_usuario(cpf_cliente):
    with conectar() as conexao:
        cursor = conexao.cursor()
        # Busca o nome cadastrado para o CPF fornecido
        cursor.execute("SELECT nome_usuario FROM usuarios WHERE cpf = ?", (cpf_cliente,))
        resultado = cursor.fetchone()
        return resultado["nome_usuario"] if resultado else "Cliente"

def extrair_catalogo_cardapio():
    with conectar() as conexao:
        cursor = conexao.cursor()
        # Retorna todos os itens disponíveis no cardápio
        cursor.execute("SELECT id, nome, preco, quantidade FROM cardapio")
        return [dict(row) for row in cursor.fetchall()]

def obter_preco_do_prato(id_prato):
    with conectar() as conexao:
        cursor = conexao.cursor()
        # Busca isolada do preço unitário de um prato pelo ID
        cursor.execute("SELECT preco FROM cardapio WHERE id = ?", (id_prato,))
        preco_prato = cursor.fetchone()
        
        if preco_prato is None:
            raise ValueError("erro-prato-inexistente")
            
        return preco_prato["preco"] 

def fiscal_validar_estoque_pedido(id_prato, qtd_desejada):
    # Bloqueia tentativas de pedidos com quantidades negativas ou zeradas
    if qtd_desejada <= 0:
        raise ValueError("erro-quantidade-negativa")
        
    with conectar() as conexao:
        cursor = conexao.cursor()
        # Busca na tabela cardapio usando o ID do produto que veio da Web
        cursor.execute("SELECT id, nome as nome_prato, quantidade FROM cardapio WHERE id = ?", (id_prato,))
        prato = cursor.fetchone()
        
        if prato is None:
            raise ValueError("erro-prato-inexistente")
            
    # Valida se a quantidade disponível no cardápio atende o pedido
    if prato["quantidade"] < qtd_desejada:
        raise ValueError("erro-estoque-insuficiente")
        
    return dict(prato)

def operario_gravar_pedido_e_abater_estoque(prato, preco_prato):
    # Extrai os dados de dentro do dicionário envelopado vindo de rotas
    nome_prato = prato["nome_prato"]
    qtd_prato_disponível = prato["quantidade"] # Mapeado da coluna quantidade do cardápio
    id_prato = prato["id"]
    cpf_cliente = prato["cpf_cliente"]
    qtd_prato_pedido = prato["quantidade_pedida"] 
    valor_prato = preco_prato

    # Faz os cálculos matemáticos financeiros e de estoque
    valor_total_item = valor_prato * qtd_prato_pedido
    nova_quantidade_estoque = qtd_prato_disponível - qtd_prato_pedido
     
    with conectar() as conexao:
        cursor = conexao.cursor()
        # Grava a nova linha de registro na tabela de pedidos
        cursor.execute('''
            INSERT INTO pedidos (cpf_cliente, nome_prato, quantidade_pedida, valor_total)
            VALUES (?, ?, ?, ?)
        ''', (cpf_cliente, nome_prato, qtd_prato_pedido, valor_total_item))
        
        # Executa a baixa de estoque real na tabela do cardápio
        cursor.execute('UPDATE cardapio SET quantidade = ? WHERE id = ?', (nova_quantidade_estoque, id_prato))
        conexao.commit()
        
    return valor_total_item

def puxar_soma_total_pedidos(cpf_cliente):
    with conectar() as conexao:
        cursor = conexao.cursor()
        # Faz o cálculo agregado de todos os gastos históricos do cliente
        cursor.execute("SELECT SUM(valor_total) as total FROM pedidos WHERE cpf_cliente = ?", (cpf_cliente,))
        resultado_soma = cursor.fetchone()
        return resultado_soma["total"] if resultado_soma["total"] is not None else 0.0
