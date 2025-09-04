from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from lxml import etree
import requests
from bs4 import BeautifulSoup

app = FastAPI(title="Validador NF-e CIGAM")

class XmlRequest(BaseModel):
    xml: str

# ----------- Função para validar XML contra XSD -----------
def validar_xml(xml_str: str, xsd_path: str):
    try:
        xml_doc = etree.fromstring(xml_str.encode("utf-8"))
        schema_doc = etree.parse(xsd_path)
        schema = etree.XMLSchema(schema_doc)
        schema.assertValid(xml_doc)
        return {"status": "OK"}
    except etree.DocumentInvalid as e:
        return {
            "status": "Erro",
            "codigo": 225,
            "mensagem": "Rejeicao: Falha no Schema XML da NFe",
            "detalhe": str(e.error_log.last_error)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar XML: {str(e)}")

# ----------- Função para checar disponibilidade SEFAZ -----------
def disponibilidade_sefaz():
    url = "https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    
    status = {}
    for row in soup.select("table.tabelaListagemDados tbody tr"):
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        if cols:
            uf = cols[0]
            autorizacao = cols[1]
            retorno = cols[2]
            consulta = cols[3]
            status[uf] = {"Autorizacao": autorizacao, "Retorno": retorno, "Consulta": consulta}
    return status

# ----------- Endpoint principal -----------
@app.post("/validar-nfe")
def validar_nfe(req: XmlRequest):
    xml_str = req.xml

    # 1 - Validar contra XSD oficial
    resultado_validacao = validar_xml(xml_str, "schemas/nfe_v4.00.xsd")

    # 2 - Consultar disponibilidade SEFAZ
    status = disponibilidade_sefaz()

    return {
        "validacao_xml": resultado_validacao,
        "disponibilidade": status
    }
