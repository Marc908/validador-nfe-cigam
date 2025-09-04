from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from lxml import etree
import requests
from bs4 import BeautifulSoup

from errors_friendly import friendly_messages

app = FastAPI(title="Validador NF-e CIGAM")

# ---------- MODELOS ----------
class XmlRequest(BaseModel):
    xml: str


# ---------- FUNÇÃO AUXILIAR ----------
def buscar_na_wiki(codigo: int) -> dict:
    """
    Busca na Wiki CIGAM informações sobre o código de rejeição.
    Se não achar, retorna um texto genérico.
    """
    try:
        url = f"https://www.cigam.com.br/wiki/index.php?title=FAQ_NE_{codigo}"
        resp = requests.get(url, timeout=10)

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            content = soup.find("div", {"id": "mw-content-text"})
            if content:
                texto = content.get_text(" ", strip=True)[:500]
                return {
                    "erro": f"Rejeição {codigo}",
                    "como_resolver": texto,
                    "fonte": url
                }
    except Exception as e:
        print(f"[Wiki] Falha ao buscar {codigo}: {e}")

    # fallback se não achou
    return {
        "erro": f"Rejeição {codigo}",
        "como_resolver": "Consulte a Wiki CIGAM para mais detalhes.",
        "fonte": "Wiki CIGAM"
    }


# ---------- FUNÇÃO PARA ESCAPAR XML CRU ----------
def escape_xml_cru(xml: str) -> str:
    """
    Escapa caracteres problemáticos em XML enviado cru dentro de JSON.
    """
    return (xml.replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;")
               .replace('"', "&quot;")
               .replace("'", "&apos;"))


# ---------- ENDPOINTS ----------
@app.get("/")
def root():
    return {"status": "ok", "mensagem": "API Validador NF-e CIGAM rodando!"}


@app.post("/nfe/validate-xml")
async def validate_nfe_xml(req: XmlRequest):
    """
    Recebe um XML de NF-e e retorna validação + mensagem amigável.
    Aceita XML cru com aspas duplas, simples ou caracteres especiais.
    """
    try:
        # escapa XML cru
        xml_str = escape_xml_cru(req.xml)

        # tenta parsear XML
        xml_tree = etree.fromstring(xml_str.encode("utf-8"))

        # ⚠️ Aqui entra a validação XSD (precisa ter os .xsd da NFe)
        codigo = 225  # exemplo fixo só para teste

        if codigo in friendly_messages:
            return {
                "codigo": codigo,
                **friendly_messages[codigo],
                "fonte": "Tratamento interno CIGAM"
            }

        wiki_info = buscar_na_wiki(codigo)
        return {
            "codigo": codigo,
            **wiki_info
        }

    except etree.XMLSyntaxError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erro de sintaxe XML: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao processar XML: {str(e)}"
        )
