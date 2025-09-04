from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from lxml import etree

app = FastAPI(
    title="API Validador NF-e CIGAM",
    description="Valida XML de NF-e e retorna erros de sintaxe detalhados",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"status": "ok", "mensagem": "API Validador NF-e CIGAM rodando!"}

@app.post("/nfe/validate-xml")
async def validate_xml(file: UploadFile):
    """
    Valida XML enviado via upload.
    Retorna erro de sintaxe com linha, coluna e trecho problemático se XML estiver inválido.
    """
    if not file.filename.endswith(".xml"):
        raise HTTPException(status_code=400, detail="Arquivo enviado não é XML")

    try:
        content = await file.read()
        etree.fromstring(content)  # parsea o XML
        return JSONResponse(content={"sucesso": True, "mensagem": "XML válido!"})
    
    except etree.XMLSyntaxError as e:
        # Pega a linha problemática do XML
        lines = content.decode('utf-8', errors='replace').splitlines()
        erro_linha = lines[e.lineno - 1] if 0 < e.lineno <= len(lines) else ""
        # Retorna linha, coluna e trecho
        raise HTTPException(
            status_code=400,
            detail={
                "mensagem": f"Erro de sintaxe no XML: {e.msg}",
                "linha": e.lineno,
                "coluna": e.position[1],
                "trecho": erro_linha.strip()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao processar XML: {str(e)}"
        )

# Rodar com: uvicorn app:app --reload --port 8080
