from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from lxml import etree
import requests
import threading
import os
import tempfile

app = FastAPI()

# URLs oficiais dos XSDs
XSD_URLS = {
    "enviNFe": "https://www.nfe.fazenda.gov.br/NFe/arquivos/nfe_v4.00.xsd"
}

# Cache em memória
XSD_CACHE = {}
CACHE_LOCK = threading.Lock()

class XMLPayload(BaseModel):
    xml: str

def get_schema(xsd_name: str) -> etree.XMLSchema:
    """
    Retorna o schema do cache, ou carrega do disco (/tmp), ou baixa da SEFAZ.
    """
    with CACHE_LOCK:
        if xsd_name in XSD_CACHE:
            return XSD_CACHE[xsd_name]

        if xsd_name not in XSD_URLS:
            raise HTTPException(status_code=400, detail=f"Schema não configurado para {xsd_name}")

        url = XSD_URLS[xsd_name]
        temp_path = os.path.join(tempfile.gettempdir(), f"{xsd_name}.xsd")

        # 1) Se já existe em disco, tenta carregar
        if os.path.exists(temp_path):
            try:
                with open(temp_path, "rb") as f:
                    schema_root = etree.XML(f.read())
                    schema = etree.XMLSchema(schema_root)
                    XSD_CACHE[xsd_name] = schema
                    return schema
            except Exception:
                # se o arquivo em disco estiver corrompido, baixa de novo
                pass

        # 2) Baixa da SEFAZ
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise HTTPException(status_code=502, detail=f"Erro ao baixar XSD da SEFAZ: {str(e)}")

        # 3) Salva no /tmp
        try:
            with open(temp_path, "wb") as f:
                f.write(resp.content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao salvar XSD em /tmp: {str(e)}")

        # 4) Compila e guarda em cache
        try:
            schema_root = etree.XML(resp.content)
            schema = etree.XMLSchema(schema_root)
            XSD_CACHE[xsd_name] = schema
            return schema
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao compilar XSD: {str(e)}")

@app.post("/validar-nfe")
def validar_nfe(payload: XMLPayload):
    """
    Valida um XML de NF-e contra o XSD oficial da SEFAZ.
    """
    try:
        xml_doc = etree.fromstring(payload.xml.encode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao parsear XML: {str(e)}")

    schema = get_schema("enviNFe")

    try:
        schema.assertValid(xml_doc)
        return {"status": "OK", "mensagem": "XML válido segundo schema SEFAZ"}
    except etree.DocumentInvalid as e:
        return {
            "status": "Erro",
            "codigo": 225,
            "mensagem": "Rejeicao: Falha no Schema XML da NFe",
            "detalhe": str(e)
        }
