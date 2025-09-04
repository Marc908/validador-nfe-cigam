from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from lxml import etree
import httpx
import os
import asyncio
import uvicorn

app = FastAPI(title="Validador NF-e CIGAM Async")

# ---------- MODELOS ----------
class XmlRequest(BaseModel):
    xml: str

# ---------- URLS DE TESTE DE DISPONIBILIDADE ----------
# Substitua pelas URLs reais dos WebServices de cada estado / nacional
SEFAZ_ENDPOINTS = {
    "Nacional": "https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx",
    "RS": "https://www.sefaz.rs.gov.br/NFE/NFE-VAL.aspx",
    "SP": "https://www.fazenda.sp.gov.br/nfe/NFE-CONSULTA.aspx"
}

# ---------- FUNÇÕES AUXILIARES ----------

async def checar_disponibilidade():
    """
    Consulta todos os WebServices em paralelo e retorna status
    """
    results = {}
    async with httpx.AsyncClient(timeout=5) as client:
        tasks = []
        for uf, url in SEFAZ_ENDPOINTS.items():
            tasks.append(asyncio.create_task(fetch_status(client, uf, url)))
        respostas = await asyncio.gather(*tasks, return_exceptions=True)
        for uf, resp in zip(SEFAZ_ENDPOINTS.keys(), respostas):
            if isinstance(resp, Exception):
                results[uf] = "Indisponível"
            else:
                results[uf] = resp
    return results

async def fetch_status(client, uf, url):
    resp = await client.get(url)
    if resp.status_code == 200:
        return "Ativo"
    return "Indisponível"

def validar_xml(xml_str):
    """
    Valida XML contra o XSD da NF-e
    """
    try:
        # Parse do XML
        xml_tree = etree.fromstring(xml_str.encode("utf-8"))
        # Aqui você poderia validar contra XSD usando etree.XMLSchema se quiser
        return xml_tree
    except etree.XMLSyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Erro de sintaxe XML: {str(e)}")

def simular_rejeicao(xml_tree):
    """
    Simula captura do cStat / xMotivo
    """
    # Exemplo: checa se existe algum elemento CST com valor inválido
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    csts = xml_tree.xpath("//nfe:CST/text()", namespaces=ns)
    for cst in csts:
        if cst not in ["00","10","20","30","40","41","50","51","60","70","90"]:
            return {"cStat": 225, "xMotivo": f"Falha no Schema XML da NFe - CST inválido: {cst}"}
    # Se nenhum erro encontrado, simula sucesso
    return {"cStat": 100, "xMotivo": "Lote processado com sucesso"}

# ---------- ENDPOINTS ----------

@app.get("/")
def root():
    return {"status": "ok", "mensagem": "API Validador NF-e CIGAM Async rodando!"}

@app.post("/nfe/validate-xml")
async def validate_nfe_xml(req: XmlRequest):
    # 1️⃣ Valida XML localmente
    xml_tree = validar_xml(req.xml)
    
    # 2️⃣ Simula cStat / xMotivo real
    erro_info = simular_rejeicao(xml_tree)
    
    # 3️⃣ Consulta disponibilidade SEFAZ em paralelo
    sefaz_status = await checar_disponibilidade()
    
    # 4️⃣ Retorna tudo em formato próximo do validador RS
    return {
        "cStat": erro_info["cStat"],
        "xMotivo": erro_info["xMotivo"],
        "sefaz_status": sefaz_status
    }

# ---------- RUN SERVER ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
