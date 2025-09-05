from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from lxml import etree
import os

app = FastAPI(title="Validador NF-e Local")

# Caminho para os XSDs locais
XSD_DIR = "./xsd"  # coloque seus XSDs aqui

def carregar_xsd(xsd_file: str):
    try:
        with open(os.path.join(XSD_DIR, xsd_file), 'rb') as f:
            schema_doc = etree.parse(f)
            return etree.XMLSchema(schema_doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar XSD: {e}")

# Função para validação de regras básicas
def validar_regras_negocio(xml_root):
    erros = []

    # Exemplo CST obrigatório (só como demonstração)
    for det in xml_root.findall(".//{http://www.portalfiscal.inf.br/nfe}det"):
        cst = det.find(".//{http://www.portalfiscal.inf.br/nfe}CST")
        if cst is not None and cst.text not in ["00","01","02","03","04","05","49","50","51","52","53","54","55","99"]:
            erros.append(f"CST inválido: {cst.text}")

    # Exemplo de campo obrigatório
    chave = xml_root.find(".//{http://www.portalfiscal.inf.br/nfe}Id")
    if chave is None or not chave.text:
        erros.append("Campo Id da NFe obrigatório ausente")

    return erros

@app.post("/nfe/validate-xml")
async def validate_xml(file: UploadFile):
    if not file.filename.endswith(".xml"):
        raise HTTPException(status_code=400, detail="O arquivo deve ser XML")

    try:
        content = await file.read()
        xml_doc = etree.fromstring(content)
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"sucesso": False, "mensagem": f"Erro ao ler XML: {e}"}
        )

    # Validar schema
    try:
        schema = carregar_xsd("nfe_v4.00.xsd")  # coloque o XSD correto
        schema.assertValid(xml_doc)
    except etree.DocumentInvalid as e:
        return JSONResponse(
            status_code=400,
            content={"sucesso": False, "mensagem": f"Erro de validação XSD: {str(e)}"}
        )

    # Validar regras de negócio
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

@app.get("/")
def root():
    return {"status": "ok", "mensagem": "API Validador NF-e Local rodando!"}

# ---------- RUN SERVER ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)

