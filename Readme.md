# 🍕🛵 Delivery RESTAURANTE - API

Uma API de alta confiabilidade para gerenciamento de usuários, catálogo e pedidos de um Restaurante. Desenvolvido em **FastAPI** e **SQLite**, o projeto aplica conceitos avançados de engenharia de software, tratamento de erros robusto e manipulação eficiente de banco de dados.

---

## 🎯 As Grandes Sacadas de Engenharia do Projeto

O grande destaque deste projeto foi o foco no design da arquitetura, resolvendo problemas de acoplamento e complexidade através de soluções inteligentes de modelagem de código:

*   **Separação de Responsabilidades (Fiscais vs. Operários):** Funções especializadas em validar dados antes de qualquer alteração física, enquanto os Operários cuidam unicamente da escrita atômica.
*   **Abstração Inteligente de Parâmetros (*Parameter Object*):** Encapsulamento de dados em uma única "sacola" dinâmica (`prato`), evitando assinaturas engessadas e funções com parâmetros gigantescos.
*   **A Técnica dos "Retângulos Dinâmicos" (*Data Enrichment*):** Expansão de dicionários em tempo de execução na memória do Python para unificar dados sem sobrecarregar o banco com consultas repetitivas.
*   **Segurança com `.env`:** Isolamento completo de credenciais e caminhos de banco de dados seguindo o padrão *The Twelve-Factor App*.

---

## 🗺️ Mapa de Navegação do Código Fonte

Clique em qualquer uma das funções abaixo para ir direto para a explicação e o código correspondente:

### ⚙️ Camada de Serviço e Infraestrutura (`service/database.py`)
1.  [**`[F01] conectar()`**](#f01-conectar) — Gerenciador de conexão com o banco.
2.  [**`[F02] inicializar_banco()`**](#f02-inicializar_banco) — Criação de tabelas, carga inicial e autocorreção de IDs.
3.  [**`[F03] fiscal_validar_seguranca_cadastro()`**](#f03-fiscal_validar_seguranca_cadastro) — Validação de integridade do CPF.
4.  [**`[F04] operario_salvar_usuario_no_banco()`**](#f04-operario_salvar_usuario_no_banco) — Gravação física do novo usuário.
5.  [**`[F05] fiscal_validar_login()`**](#f05-fiscal_validar_login) — Auditoria de credenciais de acesso.
6.  [**`[F06] buscar_nome_usuario()`**](#f06-buscar_nome_usuario) — Recuperação nominal do cliente pelo CPF.
7.  [**`[F07] extrair_catalogo_cardapio()`**](#f07-extrair_catalogo_cardapio) — Listagem em formato de dicionário do menu visual.
8.  [**`[F08] obter_preco_do_prato()`**](#f08-obter_preco_do_prato) — Busca isolada do valor unitário por ID.
9.  [**`[F09] fiscal_validar_estoque_pedido()`**](#f09-fiscal_validar_estoque_pedido) — Verificação do estoque na esteira de pedidos com busca uma na tabela cardapio usando o ID do produto que veio da Web.
10. [**`[F10] operario_gravar_pedido_e_abater_estoque()`**](#f10-operario_gravar_pedido_e_abater_estoque) — Fechamento financeiro e baixa atômica de insumos.
11. [**`[F11] puxar_soma_total_pedidos()`**](#f11-puxar_soma_total_pedidos) — Agregação financeira histórica do cliente.

### 🌐 Camada de Rotas Web (`app/routes.py`)
12. [**`[R01] rota_cadastro()`**](#r01-rota_cadastro) — Endpoint HTTP para registro de clientes.
13. [**`[R02] rota_login()`**](#r02-rota_login) — Endpoint HTTP para autenticação.
14. [**`[R03] rota_listar_cardapio()`**](#r03-rota_listar_cardapio) — Endpoint HTTP para exibição do menu.
15. [**`[R04] rota_realizar_pedido()`**](#r04-rota_realizar_pedido) — Endpoint HTTP que orquestra a compra.

---

## 💾 Código Fonte Completo e Documentado

### ⚙️ MÓDULO 1: `service/database.py`

#### <a name="f01-conectar"></a> 1. `[F01] conectar()`
* **O que faz:** Abre a conexão com o banco SQLite usando variáveis do `.env` e ativa a otimização `sqlite3.Row` para ler colunas pelo nome e não por números.
```python
def conectar():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn
```

#### <a name="f02-inicializar_banco"></a> 2. `[F02] inicializar_banco()`
* **O que faz:** Cria a estrutura de tabelas (`usuarios`, `cardapio`, `pedidos`), insere a carga inicial de produtos e executa o **Mecanismo de Autocorreção Interno** que busca e preenche permanentemente qualquer ID nulo ou quebrado usando o `rowid` do SQLite.
```python
def inicializar_banco():
    with conectar() as conexao:
        cursor = conexao.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                cpf TEXT PRIMARY KEY,
                nome_usuario TEXT NOT NULL,
                senha TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                quantidade INTEGER NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpf_cliente TEXT NOT NULL,
                nome_prato TEXT NOT NULL,
                quantidade_pedida INTEGER NOT NULL,
                valor_total REAL NOT NULL
            )
        ''')

        cursor.execute("SELECT * FROM cardapio")
        if not cursor.fetchall():
            pratos_iniciais = [
                ("Hambúrguer", 29.90, 10),
                ("Pizza", 45.00, 10),
                ("Lasanha", 38.50, 10)
            ]
            cursor.executemany("INSERT INTO cardapio (nome, preco, quantidade) VALUES (?, ?, ?)", pratos_iniciais)
            conexao.commit()

        # Verificação e correção de IDs nulos na tabela do cardápio
        cursor.execute("SELECT rowid, nome FROM cardapio WHERE id IS NULL OR id = '' OR id = 0")
        produtos_sem_id = cursor.fetchall()
        
        if produtos_sem_id:
            for produto in produtos_sem_id:
                id_seguro_e_fixo = produto["rowid"]
                cursor.execute('''
                    UPDATE cardapio 
                    SET id = ? 
                    WHERE rowid = ?
                ''', (id_seguro_e_fixo, id_seguro_e_fixo))
            conexao.commit()

        # Verificação e correção de IDs nulos na tabela de pedidos
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
```

#### <a name="f03-fiscal_validar_seguranca_cadastro"></a> 3. `[F03] fiscal_validar_seguranca_cadastro(cpf_usuario)`
* **O que faz:** Fiscal de segurança. Limpa espaços, garante que o CPF tem exatamente 11 dígitos numéricos e impede cadastros duplicados no sistema.
```python
def fiscal_validar_seguranca_cadastro(cpf_usuario):
    cpf_limpo = cpf_usuario.strip()
    if len(cpf_limpo) != 11 or not cpf_limpo.isdigit():
        raise ValueError("erro-cpf-formato")
    with conectar() as conexao:
        cursor = conexao.cursor()
        cursor.execute('SELECT cpf FROM usuarios WHERE cpf = ?', (cpf_limpo,))
        if cursor.fetchone() is not None:
            raise ValueError("erro-cpf-duplicado")
    return cpf_limpo
```

#### <a name="f04-operario_salvar_usuario_no_banco"></a> 4. `[F04] operario_salvar_usuario_no_banco(cpf, nome, senha)`
* **O que faz:** Operário puro. Recebe o sinal verde do fiscal de cadastro e executa o salvamento definitivo do cliente na tabela `usuarios`.
```python
def operario_salvar_usuario_no_banco(cpf, nome, senha):
    with conectar() as conexao:
        cursor = conexao.cursor()
        cursor.execute('INSERT INTO usuarios (cpf, nome_usuario, senha) VALUES (?, ?, ?)', (cpf, nome, senha))
        conexao.commit()
```

#### <a name="f05-fiscal_validar_login"></a> 5. `[F05] fiscal_validar_login(login_cpf, login_user, login_senha)`
* **O que faz:** Fiscal de segurança. Cruza as três informações de login de forma exata e retorna o CPF confirmado apenas se o usuário for autêntico.
```python
def fiscal_validar_login(login_cpf, login_user, login_senha):
    with conectar() as conexao:
        cursor = conexao.cursor()
        cursor.execute('''
            SELECT cpf FROM usuarios WHERE cpf = ? AND nome_usuario = ? AND senha = ?
        ''', (login_cpf.strip(), login_user.strip(), login_senha.strip()))
        usuario = cursor.fetchone()
        if usuario is None:
            raise ValueError("erro-login-incorreto")
        return usuario["cpf"]
```

#### <a name="f06-buscar_nome_usuario"></a> 6. `[F06] buscar_nome_usuario(cpf_cliente)`
* **O que faz:** Função de apoio visual. Busca o nome de usuário do cliente baseado no CPF informado para exibir mensagens personalizadas na tela.
```python
def buscar_nome_usuario(cpf_cliente):
    with conectar() as conexao:
        cursor = conexao.cursor()
        cursor.execute("SELECT nome_usuario FROM usuarios WHERE cpf = ?", (cpf_cliente,))
        resultado = cursor.fetchone()
        return resultado["nome_usuario"] if resultado else "Cliente"
```

#### <a name="f07-extrair_catalogo_cardapio"></a> 7. `[F07] extrair_catalogo_cardapio()`
* **O que faz:** Lê toda a tabela `cardapio` e converte as linhas do SQLite em uma lista limpa de dicionários Python, facilitando a renderização no FastAPI.
```python
def extrair_catalogo_cardapio():
    with conectar() as conexao:
        cursor = conexao.cursor()
        cursor.execute("SELECT id, nome, preco, quantidade FROM cardapio")
        return [dict(row) for row in cursor.fetchall()]
```

#### <a name="f08-obter_preco_do_prato"></a> 8. `[F08] obter_preco_do_prato(id_prato)`
* **O que faz:** Isolamento técnico. Faz uma busca ultra rápida focada apenas no campo de preço de um item do cardápio pelo ID, devolvendo o número puro (float).
```python
def obter_preco_do_prato(id_prato):
    with conectar() as conexao:
        cursor = conexao.cursor()
        cursor.execute("SELECT preco FROM cardapio WHERE id = ?", (id_prato,))
        preco_prato = cursor.fetchone()
        if preco_prato is None:
            raise ValueError("erro-prato-inexistente")
        return preco_prato["preco"]
```

#### <a name="f09-fiscal_validar_estoque_pedido"></a> 9. `[F09] fiscal_validar_estoque_pedido(id_prato, qtd_desejada)`
* **O que faz:** Fiscal de estoque. Olha para a esteira de pedidos pelo ID enviado, valida se o volume solicitado existe na base histórica de pedidos e bloqueia quantidades negativas.
```python
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
```

 #### <a name="f10-operario_gravar_pedido_e_abater_estoque"></a> 10. `[F10] operario_gravar_pedido_e_abater_estoque(prato, preco_prato)`
* **O que faz:** Operário complexo. Processa o Objeto de Parâmetro (`prato`), executa a multiplicação financeira usando o preço isolado recebido por parâmetro, gera um novo registro de venda e dá a baixa final atualizando o estoque da cozinha.
```python
def operario_gravar_pedido_e_abater_estoque(prato, preco_prato):
    nome_prato = prato["nome_prato"]
    qtd_prato_disponível = prato["quantidade_pedida"] 
    id_prato = prato["id"]
    cpf_cliente = prato["cpf_cliente"]
    qtd_prato_pedido = prato["quantidade_pedida"] 
    valor_prato = preco_prato

    valor_total_item = valor_prato * qtd_prato_pedido
    nova_quantidade_estoque = qtd_prato_disponível - qtd_prato_pedido
     
    with conectar() as conexao:
        cursor = conexao.cursor()
        cursor.execute('''
            INSERT INTO pedidos (cpf_cliente, nome_prato, quantidade_pedida, valor_total) VALUES (?, ?, ?, ?)
        ''', (cpf_cliente, nome_prato, qtd_prato_pedido, valor_total_item))
        cursor.execute('UPDATE cardapio SET quantidade = ? WHERE id = ?', (nova_quantidade_estoque, id_prato))
        conexao.commit()
    return valor_total_item
```

#### <a name="f11-puxar_soma_total_pedidos"></a> 11. `[F11] puxar_soma_total_pedidos(cpf_cliente)`
* **O que faz:** Função analítica. Faz uma soma agregada de todos os gastos daquele CPF no restaurante utilizando a query `SUM`, protegendo a aplicação contra retornos vazios (`None`).
```python
def puxar_soma_total_pedidos(cpf_cliente):
    with conectar() as conexao:
        cursor = conexao.cursor()
        cursor.execute("SELECT SUM(valor_total) as total FROM pedidos WHERE cpf_cliente = ?", (cpf_cliente,))
        resultado_soma = cursor.fetchone()
        return resultado_soma["total"] if resultado_soma["total"] is not None else 0.0
```

---

### 🌐 MÓDULO 2: `app/routes.py`

#### <a name="r01-rota_cadastro"></a> 12. `[R01] rota_cadastro(dados)`
* **O que faz:** Gatilho Web de cadastro. Recebe o JSON da tela, envelopa a chamada no bloco `try`, passa os dados pelo Fiscal e grava com o Operário. Retorna `400 Bad Request` em caso de falha.
```python
@router.post("/cadastro")
def rota_cadastro(dados: EsquemaCadastro):
    try:
        cpf_aprovado = service.database.fiscal_validar_seguranca_cadastro(dados.cpf)
        service.database.operario_salvar_usuario_no_banco(cpf_aprovado, dados.nome, dados.senha)
        return {"status": "sucesso", "mensagem": "Usuario cadastrado com sucesso!"}
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))
```

#### <a name="r02-rota_login"></a> 13. `[R02] rota_login(dados)`
* **O que faz:** Gatilho Web de autenticação. Roda o login, devolvendo um código `401 Unauthorized` se o Fiscal de login acusar credenciais inválidas.
```python
@router.post("/login")
def rota_login(dados: EsquemaLogin):
    try:
        cpf_logado = service.database.fiscal_validar_login(dados.cpf, dados.nome, dados.senha)
        return {"status": "sucesso", "mensagem": "Logado com sucesso!", "cpf_logado": cpf_logado}
    except ValueError as erro:
        raise HTTPException(status_code=401, detail=str(erro))
```

#### <a name="r03-rota_listar_cardapio"></a> 14. `[R03] rota_listar_cardapio()`
* **O que faz:** Gatilho Web de listagem. Dispara a extração limpa do cardápio direto para a tela, gerando o catálogo visual no formato JSON automaticamente.
```python
@router.get("/cardapio")
def rota_listar_cardapio():
    linhas = service.database.extrair_catalogo_cardapio()
    return [{"id": r["id"], "nome": r["nome"], "preco": r["preco"], "quantidade": r["quantidade"]} for r in linhas]
```

#### <a name="r04-rota_realizar_pedido"></a> 15. `[R04] rota_realizar_pedido(dados)`
* **O que faz:** Gatilho Web do pedido. O ponto alto da arquitetura. Recebe a requisição, chama o Fiscal para validar o histórico, aplica o **Enriquecimento de Dados** (retângulos dinâmicos) injetando a quantidade e o CPF na "sacola" do prato, pega o preço isolado e entrega tudo para o Operário dar a baixa.
```python
@router.post("/pedido")
def rota_realizar_pedido(dados: EsquemaPedido):
    try:
        prato_validado = service.database.fiscal_validar_estoque_pedido(dados.id_prato, dados.quantidade)
        prato_validado["cpf_cliente"] = dados.cpf_cliente
        prato_validado["quantidade_pedida"] = dados.quantidade
        preco_isolado = service.database.obter_preco_do_prato(dados.id_prato)
        valor_total = service.database.operario_gravar_pedido_e_abater_estoque(prato_validado, preco_isolado)
        return {"status": "sucesso", "mensagem": "Pedido realizado e estoque updated!", "valor_total": valor_total}
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))
```

---

## 🚀 Como Executar o Ecossistema

1. Instale as bibliotecas necessárias no seu terminal:
   ```bash
   pip install fastapi uvicorn python-dotenv
   ```
2. Inicialize o servidor Uvicorn a partir da raiz do seu projeto:
   ```bash
   python -m uvicorn main:app --reload
   ```
3. Abra o seu navegador e acesse a documentação interativa automatizada para testar os endpoints em tempo real:
   *   **Swagger UI:** [127.0.0.1:8000/docs]
