# ==============================================================================
# 📁 ARQUIVO: app/routes.py
# ==============================================================================
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from service import database  # Importação correta e direta

router = APIRouter()

class EsquemaCadastro(BaseModel):
    cpf: str
    nome: str
    senha: str

class EsquemaLogin(BaseModel):
    cpf: str
    nome: str
    senha: str

class EsquemaPedido(BaseModel):
    cpf_cliente: str
    id_prato: int
    quantidade: int


# --- GATILHOS / ROTAS WEB ---

@router.post("/cadastro")
def rota_cadastro(dados: EsquemaCadastro):
    try:
        # CORRIGIDO: Removido os termos repetidos, usando apenas database.
        cpf_aprovado = database.fiscal_validar_seguranca_cadastro(dados.cpf)
        database.operario_salvar_usuario_no_banco(cpf_aprovado, dados.nome, dados.senha)
        return {"status": "sucesso", "mensagem": "Usuario cadastrado com sucesso!"}
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))

@router.post("/login")
def rota_login(dados: EsquemaLogin):
    try:
        # CORRIGIDO: Usando apenas database.
        cpf_logado = database.fiscal_validar_login(dados.cpf, dados.nome, dados.senha)
        return {"status": "sucesso", "mensagem": "Logado com sucesso!", "cpf_logado": cpf_logado}
    except ValueError as erro:
        raise HTTPException(status_code=401, detail=str(erro))

@router.get("/cardapio")
def rota_listar_cardapio():
    # CORRIGIDO: Usando apenas database.
    linhas = database.extrair_catalogo_cardapio()
    return [{"id": r["id"], "nome": r["nome"], "preco": r["preco"], "quantidade": r["quantidade"]} for r in linhas]


@router.post("/pedido")
def rota_realizar_pedido(dados: EsquemaPedido):
    try:
        # CORRIGIDO: Usando apenas database em todas as chamadas da rota.
        prato_validado = database.fiscal_validar_estoque_pedido(dados.id_prato, dados.quantidade)
        
        prato_validado["cpf_cliente"] = dados.cpf_cliente
        prato_validado["quantidade_pedida"] = dados.quantidade
        
        preco_isolado = database.obter_preco_do_prato(dados.id_prato)
        valor_total = database.operario_gravar_pedido_e_abater_estoque(prato_validado, preco_isolado)
        
        return {
            "status": "sucesso", 
            "mensagem": "Pedido realizado e estoque updated!", 
            "valor_total": valor_total
        }
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))
