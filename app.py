from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from lxml import etree
import os
import uvicorn

app = FastAPI(title="Validador NF-e Local")

# Caminho para os XSDs locais
XSD_DIR = "./xsd"

# Mapeamento da tag raiz -> XSD correto
ROOT_XSD_MAP = {
    "enviNFe": "enviNFe_v4.00.xsd",
    "NFe": "nfe_v4.00.xsd",
    "consSitNFe": "consSitNFe_v4.00.xsd",
    "consStatServ": "consStatServ_v4.00.xsd",
    "inutNFe": "inutNFe_v4.00.xsd",
    "retEnviNFe": "retEnviNFe_v4.00.xsd"
}

def carregar_xsd(xsd_file: str):
    try:
        with open(os.path.join(XSD_DIR, xsd_file), 'rb') as f:
            schema_doc = etree.parse(f)
            return etree.XMLSchema(schema_doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar XSD: {e}")

def validar_regras_negocio(xml_root):
    erros = []
    # Exemplo de regra: CST válido
    for det in xml_root.findall(".//{http://www.portalfiscal.inf.br/nfe}det"):
        cst = det.find(".//{http://www.portalfiscal.inf.br/nfe}CST")
        if cst is not None and cst.text not in ["00","01","02","03","04","05","49","50","51","52","53","54","55","99"]:
            erros.append(f"CST inválido: {cst.text}")

    return erros

class XmlRequest(BaseModel):
    xml: str

@app.post("/nfe/validate-xml")
async def validate_xml(request: XmlRequest):
    try:
        xml_doc = etree.fromstring(request.xml.encode("utf-8"))
    except Exception as e:
        return JSONResponse(status_code=400, content={"sucesso": False, "mensagem": f"Erro ao ler XML: {e}"})

    # Detectar raiz e escolher XSD
    root_tag = etree.QName(xml_doc).localname
    xsd_file = ROOT_XSD_MAP.get(root_tag)

    if not xsd_file:
        return JSONResponse(status_code=400, content={"sucesso": False, "mensagem": f"Tag raiz '{root_tag}' não suportada para validação"})

    # Validar schema
    try:
        schema = carregar_xsd(xsd_file)
        schema.assertValid(xml_doc)
    except etree.DocumentInvalid as e:
        return JSONResponse(status_code=400, content={"sucesso": False, "mensagem": f"Erro de validação XSD: {str(e)}"})

    # Validar regras de negócio
    erros_negocio = validar_regras_negocio(xml_doc)
    if erros_negocio:
        return JSONResponse(status_code=400, content={"sucesso": False, "mensagem": "Erros de regras de negócio", "detalhes": erros_negocio})

    return JSONResponse(status_code=200, content={"sucesso": True, "mensagem": "XML válido e regras de negócio conferidas!"})

@app.get("/")
def root():
    return {"status": "ok", "mensagem": "API Validador NF-e rodando!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
