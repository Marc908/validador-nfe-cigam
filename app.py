from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from lxml import etree
import requests
from bs4 import BeautifulSoup

app = FastAPI(title="Validador NF-e CIGAM")

# ---------- MODELOS ----------
class XmlRequest(BaseModel):
    xml: str

# ---------- MENSAGENS AMIGÁVEIS ----------
friendly_messages = {
    225: {
        "erro": "A NF-e foi rejeitada porque o arquivo XML está incorreto.",
        "onde_ocorreu": "Estrutura do XML",
        "como_resolver": (
            "Verifique se o XML foi gerado corretamente no CIGAM. "
            "Esse erro acontece quando existe tag faltando, duplicada ou valor fora do padrão. "
            "Sugestão: reenvie a NF-e ou gere novamente."
        )
    },
    217: {
        "erro": "A NF-e não consta na base de dados da SEFAZ.",
        "onde_ocorreu": "Consulta na SEFAZ",
        "como_resolver": (
            "Isso acontece quando tenta consultar uma NF-e que nunca foi autorizada. "
            "Confirme se a nota foi transmitida com sucesso no CIGAM e reenvie se necessário."
        )
    },
    539: {
        "erro": "Já existe uma NF-e com a mesma numeração, mas com chave diferente.",
        "onde_ocorreu": "Chave de Acesso",
        "como_resolver": (
            "Verifique a numeração da nota no CIGAM. "
            "Se já existe uma nota com o mesmo número, corrija a sequência e transmita novamente."
        )
    },
    204: {
        "erro": "Duplicidade de NF-e.",
        "onde_ocorreu": "Chave de Acesso",
        "como_resolver": (
            "A NF-e já foi transmitida e autorizada. "
            "Não é necessário reenviar. "
            "Consulte a autorização anterior para confirmar."
        )
    },
    237: {
        "erro": "CPF ou CNPJ do destinatário inválido.",
        "onde_ocorreu": "Cadastro do Cliente",
        "como_resolver": (
            "Verifique o CPF ou CNPJ do cliente no CIGAM. "
            "Corrija no cadastro e reenvie a nota."
        )
    },
    482: {
        "erro": "CFOP inválido para a operação.",
        "onde_ocorreu": "Impostos → CFOP",
        "como_resolver": (
            "O CFOP informado não é aceito para essa operação. "
            "Verifique a tabela de CFOPs e ajuste no item da nota no CIGAM."
        )
    },
    501: {
        "erro": "CST incompatível com a operação.",
        "onde_ocorreu": "Impostos → CST",
        "como_resolver": (
            "O CST usado não corresponde ao tipo de operação. "
            "Corrija no cadastro de impostos no CIGAM antes de reenviar."
        )
    },
    580: {
        "erro": "Inscrição Estadual (IE) do destinatário não informada.",
        "onde_ocorreu": "Cadastro do Cliente",
        "como_resolver": (
            "Inclua a IE no cadastro do cliente no CIGAM. "
            "Se o cliente for isento, marque como 'ISENTO'."
        )
    },
    999: {
        "erro": "Erro interno da SEFAZ.",
        "onde_ocorreu": "Serviço da SEFAZ",
        "como_resolver": (
            "Esse erro não depende do CIGAM. "
            "Aguarde alguns minutos e tente novamente. "
            "Se persistir, consulte o status do serviço da SEFAZ."
        )
    },
    9999: {
        "erro": "Erro desconhecido.",
        "onde_ocorreu": "Não identificado",
        "como_resolver": (
            "Revise o XML e tente reenviar. "
            "Se continuar com problema, entre em contato com o suporte CIGAM."
        )
    }
}
# ---------- FUNÇÃO AUXILIAR ----------
def buscar_na_wiki(codigo: int) -> dict:
    try:
        url = f"https://www.cigam.com.br/wiki/index.php?title=FAQ_NE_{codigo}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            content = soup.find("div", {"id": "mw-content-text"})
            if content:
                texto = content.get_text(" ", strip=True)[:500]
                return {"erro": f"Rejeição {codigo}", "como_resolver": texto, "fonte": url}
    except Exception as e:
        print(f"[Wiki] Falha ao buscar {codigo}: {e}")
    return {"erro": f"Rejeição {codigo}", "como_resolver": "Consulte a Wiki CIGAM.", "fonte": "Wiki CIGAM"}

# ---------- ENDPOINTS ----------
@app.get("/")
def root():
    return {"status": "ok", "mensagem": "API Validador NF-e CIGAM rodando!"}

@app.post("/nfe/validate-xml")
async def validate_nfe_xml(req: XmlRequest):
    try:
        xml_tree = etree.fromstring(req.xml.encode("utf-8"))

        # Simula código de rejeição
        codigo = 225

        if codigo in friendly_messages:
            return {"codigo": codigo, **friendly_messages[codigo], "fonte": "Tratamento interno CIGAM"}

        wiki_info = buscar_na_wiki(codigo)
        return {"codigo": codigo, **wiki_info}

    except etree.XMLSyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Erro de sintaxe XML: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao processar XML: {str(e)}")

# ---------- RUN SERVER ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
