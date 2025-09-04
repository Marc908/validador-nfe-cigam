from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from lxml import etree
import requests
from bs4 import BeautifulSoup
import io

app = FastAPI(title="Validador NF-e CIGAM")

class XmlRequest(BaseModel):
    xml: str

# ---------- Função para pegar XSD direto da SEFAZ ----------
def baixar_xsd(root_tag: str):
    base_url = "http://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo="

    # Mapeamento completo de schemas NF-e v4.00
    schemas = {
        # Autorização
        "enviNFe": "enviNFe_v4.00.xsd",
        "retEnviNFe": "retEnviNFe_v4.00.xsd",
        "retConsReciNFe": "retConsReciNFe_v4.00.xsd",

        # Consulta NF-e
        "consSitNFe": "consSitNFe_v4.00.xsd",
        "retConsSitNFe": "retConsSitNFe_v4.00.xsd",

        # Inutilização
        "inutNFe": "inutNFe_v4.00.xsd",
        "retInutNFe": "retInutNFe_v4.00.xsd",

        # Cancelamento (Evento)
        "envEventoCancNFe": "envEventoCancNFe_v1.00.xsd",
        "retEnvEventoCancNFe": "retEnvEventoCancNFe_v1.00.xsd",

        # Carta de Correção (Evento)
        "envCCe": "envCCe_v1.00.xsd",
        "retEnvCCe": "retEnvCCe_v1.00.xsd",

        # Manifestação do Destinatário (Evento)
        "envManifestacao": "envManifestacao_v1.00.xsd",
        "retEnvManifestacao": "retEnvManifestacao_v1.00.xsd",

        # Consulta Cadastro
        "consCad": "consCad_v2.00.xsd",
        "retConsCad": "retConsCad_v2.00.xsd"
    }

    if root_tag not in schemas:
        raise HTTPException(status_code=400, detail=f"Schema não suportado: {root_tag}")

    schema_url = base_url + schemas[root_tag]
    r = requests.get(schema_url)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Não foi possível baixar XSD da SEFAZ ({root_tag})")

    return etree.parse(io.BytesIO(r.content))

# ---------- Função para validar XML ----------
def validar_xml(xml_str: str):
    try:
        xml_doc = etree.fromstring(xml_str.encode("utf-8"))

        # Identifica tag raiz
        root_tag = etree.QName(xml_doc.tag).localname
        schema_doc = baixar_xsd(root_tag)
        schema = etree.XMLSchema(schema_doc)

        schema.assertValid(xml_doc)
        return {"status": "OK", "mensagem": "XML válido segundo schema SEFAZ"}
    except etree.DocumentInvalid as e:
        last_error = e.error_log.last_error
        return {
            "status": "Erro",
            "codigo": 225,  # Código oficial para falha de schema
            "mensagem": "Rejeicao: Falha no Schema XML da NFe",
            "detalhe": str(last_error)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar XML: {str(e)}")

# ---------- Função para checar disponibilidade SEFAZ ----------
def disponibilidade_sefaz():
    url = "https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx"
    r = requests.get(url)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail="Não foi possível acessar a disponibilidade da SEFAZ")

    soup = BeautifulSoup(r.text, "html.parser")
    status = {}
    for row in soup.select("table.tabelaListagemDados tbody tr"):
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        if cols:
            uf = cols[0]
            status[uf] = {
                "Autorizacao": cols[1],
                "Retorno": cols[2],
                "Consulta": cols[3],
                "Inutilizacao": cols[4],
                "StatusServico": cols[5],
            }
    return status

# ---------- Endpoint principal ----------
@app.post("/validar-nfe")
def validar_nfe(req: XmlRequest):
    xml_str = req.xml

    # 1 - Validar contra XSD oficial (online)
    resultado_validacao = validar_xml(xml_str)

    # 2 - Consultar disponibilidade SEFAZ
    status = disponibilidade_sefaz()

    return {
        "validacao_xml": resultado_validacao,
        "disponibilidade": status
    }
