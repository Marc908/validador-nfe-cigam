from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from lxml import etree
import os

app = FastAPI(title="Validador NF-e Local")

# Caminho para os XSDs locais
XSD_DIR = "./xsd"  # coloque seus XSDs aqui (ex: enviNFe_v4.00.xsd)

# Função para carregar o XSD
def carregar_xsd(xsd_file: str):
    try:
        with open(os.path.join(XSD_DIR, xsd_file), 'rb') as f:
            schema_doc = etree.parse(f)
            return etree.XMLSchema(schema_doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar XSD: {e}")

# Validação de regras de negócio básicas
def validar_regras_negocio(xml_root):
    erros = []

    # Exemplo: CST obrigatório
    for det in xml_root.findall(".//{http://www.portalfiscal.inf.br/nfe}det"):
        cst = det.find(".//{http://www.portalfiscal.inf.br/nfe}CST")
        if cst is not None and cst.text not in [
            "00","01","02","03","04","05","49","50","51","52","53","54","55","99"
        ]:
            erros.append(f"CST inválido: {cst.text}")

    # Exemplo: campo Id obrigatório
    chave = xml_root.find(".//{http://www.portalfiscal.inf.br/nfe}infNFe")
    if chave is None or not chave.get("Id"):
        erros.append("Campo Id da NFe obrigatório ausente")

    return erros

# Modelo para receber JSON
class XmlRequest(BaseModel):
    xml: str

# Endpoint principal
@app.post("/nfe/validate-xml")
async def validate_xml(request: Request):
    """
    Aceita XML cru ou JSON:
    - JSON: {"xml": "<xml>...</xml>"}
    - Body puro: <xml>...</xml>
    """
    # Detecta se é JSON ou texto cru
    try:
        data = await request.json()
        xml_string = data.get("xml", "")
    except:
        xml_string = await request.body()
        xml_string = xml_string.decode("utf-8")

    if not xml_string.strip():
        return JSONResponse(
            status_code=400,
            content={"sucesso": False, "mensagem": "Nenhum XML fornecido"}
        )

    # Parse do XML
    try:
        xml_doc = etree.fromstring(xml_string.encode("utf-8"))
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"sucesso": False, "mensagem": f"Erro ao ler XML: {e}"}
        )

    # Validação XSD (enviNFe)
    try:
        schema = carregar_xsd("enviNFe_v4.00.xsd")  # agora usa enviNFe_v4.00.xsd
        schema.assertValid(xml_doc)
    except etree.DocumentInvalid as e:
        return JSONResponse(
            status_code=400,
            content={"sucesso": False, "mensagem": f"Erro de validação XSD: {str(e)}"}
        )

    # Validação regras de negócio
    erros_negocio = validar_regras_negocio(xml_doc)
    if erros_negocio:
        return JSONResponse(
            status_code=400,
            content={"sucesso": False, "mensagem": "Erros de regras de negócio", "detalhes": erros_negocio}
        )

    return JSONResponse(
        status_code=200,
        content={"sucesso": True, "mensagem": "XML válido e regras de negócio conferidas!"}
    )

# Endpoint raiz
@app.get("/")
def root():
    return {"status": "ok", "mensagem": "API Validador NF-e Local rodando!"}

# Execução direta
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
