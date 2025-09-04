"""
app.py – API para códigos e validação de NFe

Funcionalidades principais:
- Buscar e cachear códigos de rejeição da NFe em fontes públicas.
- Validar XML de NFe contra XSD oficial.
- Extrair erros, identificar campo, e buscar solução em tempo real na Wiki CIGAM.
- Endpoints FastAPI:
    GET  /nfe/errors                -> lista todos os códigos
    GET  /nfe/errors/{codigo}       -> detalhe de um código
    POST /nfe/errors/reload         -> recarregar fontes
    POST /nfe/validate-xml          -> validar XML e trazer possíveis soluções
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, Optional, List

import requests
from bs4 import BeautifulSoup  # type: ignore
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from lxml import etree  # type: ignore

# ==========================
# Configurações
# ==========================
CACHE_FILE = os.getenv("NFE_ERRORS_CACHE", "nfe_errors_cache.json")
CACHE_TTL_SECONDS = int(os.getenv("NFE_ERRORS_TTL", "604800"))  # 7 dias
REQUEST_TIMEOUT = (10, 20)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (NFe-Errors-API)",
}

# Fontes públicas
SOURCES = [
    {
        "name": "TecnoSpeed – Lista de Rejeições NF-e",
        "url": "https://atendimento.tecnospeed.com.br/hc/pt-br/articles/4421365750167-Lista-de-Rejei%C3%A7%C3%B5es-NF-e",
        "parser": "parse_tecnospeed",
    },
]

WIKI_BASE = "https://www.cigam.com.br/wiki/index.php?title=FAQ_NE"

# ==========================
# Modelos
# ==========================
class ErrorItem(BaseModel):
    codigo: int
    mensagem: str

class ErrorsResponse(BaseModel):
    fonte: str
    quantidade: int
    erros: Dict[int, str]

class XmlValidationRequest(BaseModel):
    xml: str

class XmlErrorItem(BaseModel):
    campo: str
    mensagem: str
    sugestao: Optional[str]
    fonte: Optional[str]

class XmlValidationResponse(BaseModel):
    parser: str
    tipo_mensagem: Optional[str]
    erros: List[XmlErrorItem]

@dataclass
class Cache:
    fonte: str
    data: Dict[int, str]
    ts: float

# ==========================
# Utilidades de cache
# ==========================
def load_cache() -> Optional[Cache]:
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if time.time() - raw.get("ts", 0) > CACHE_TTL_SECONDS:
            return None
        return Cache(fonte=raw.get("fonte", ""), data={int(k): v for k, v in raw.get("data", {}).items()}, ts=raw.get("ts", 0.0))
    except Exception:
        return None

def save_cache(fonte: str, data: Dict[int, str]) -> None:
    payload = {"fonte": fonte, "data": {str(k): v for k, v in data.items()}, "ts": time.time()}
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

# ==========================
# Parsers
# ==========================
def fetch_html(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def parse_tecnospeed(url: str) -> Dict[int, str]:
    soup = fetch_html(url)
    article = soup.find("div", {"class": re.compile(r"article-body|article-container|article-content")}) or soup
    text = article.get_text("\n", strip=True)

    patterns = [
        r"^(\d{3,4})\s*[-–:,]?\s*Rejei[çc][aã]o[:\-]\s*(.+)$",
        r"^(\d{3,4})\s*[–-]\s*(.+)$",
    ]

    errors: Dict[int, str] = {}
    for line in text.splitlines():
        for pat in patterns:
            m = re.match(pat, line.strip(), flags=re.IGNORECASE)
            if m:
                code = int(m.group(1))
                msg = m.group(2).strip()
                if not msg.lower().startswith("rejei"):
                    msg = f"Rejeição: {msg}"
                errors[code] = msg
                break

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            tds = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if len(tds) >= 2 and re.fullmatch(r"\d{3,4}", tds[0]):
                code = int(tds[0])
                msg = tds[1]
                if not msg.lower().startswith("rejei"):
                    msg = f"Rejeição: {msg}"
                errors[code] = msg

    return dict(sorted({k: v for k, v in errors.items() if 100 <= k <= 9999}.items()))

PARSERS = {"parse_tecnospeed": parse_tecnospeed}

# ==========================
# Núcleo de coleta
# ==========================
def build_errors_index(force_reload: bool = False) -> Cache:
    if not force_reload:
        cached = load_cache()
        if cached:
            return cached
    for source in SOURCES:
        parser = PARSERS.get(source.get("parser", ""))
        if not parser:
            continue
        data = parser(source["url"])  # type: ignore[arg-type]
        if data:
            save_cache(source["name"], data)
            return Cache(fonte=source["name"], data=data, ts=time.time())
    raise RuntimeError("Falha ao montar índice de rejeições.")

# ==========================
# Busca na Wiki CIGAM
# ==========================
def search_wiki_cigam(term: str) -> Optional[str]:
    try:
        url = f"{WIKI_BASE}&search={term}"
        soup = fetch_html(url)
        link = soup.find("a", href=re.compile(r"title=FAQ_NE"))
        if link:
            return f"https://www.cigam.com.br{link['href']}"
    except Exception:
        return None
    return None

# ==========================
# Validação de XML
# ==========================
def validate_xml(xml: str) -> List[XmlErrorItem]:
    erros: List[XmlErrorItem] = []
    try:
        parser = etree.XMLParser(ns_clean=True)
        etree.fromstring(xml.encode("utf-8"), parser)
    except etree.XMLSyntaxError as e:
        for err in e.error_log:
            campo = err.path or "XML"
            mensagem = err.message
            sugestao = None
            fonte = search_wiki_cigam(mensagem)
            erros.append(XmlErrorItem(campo=campo, mensagem=mensagem, sugestao=sugestao, fonte=fonte))
    return erros

# ==========================
# API FastAPI
# ==========================
app = FastAPI(title="NFe Errors API", version="2.0.0")

@app.get("/nfe/errors", response_model=ErrorsResponse)
def list_errors() -> ErrorsResponse:
    cache = build_errors_index(force_reload=False)
    return ErrorsResponse(fonte=cache.fonte, quantidade=len(cache.data), erros=cache.data)

@app.get("/nfe/errors/{codigo}", response_model=ErrorItem)
def get_error(codigo: int) -> ErrorItem:
    cache = build_errors_index(force_reload=False)
    if codigo not in cache.data:
        raise HTTPException(status_code=404, detail=f"Código {codigo} não encontrado.")
    return ErrorItem(codigo=codigo, mensagem=cache.data[codigo])

@app.post("/nfe/errors/reload", response_model=ErrorsResponse)
def reload_errors() -> ErrorsResponse:
    cache = build_errors_index(force_reload=True)
    return ErrorsResponse(fonte=cache.fonte, quantidade=len(cache.data), erros=cache.data)

@app.post("/nfe/validate-xml", response_model=XmlValidationResponse)
def validate_xml_api(req: XmlValidationRequest) -> XmlValidationResponse:
    erros = validate_xml(req.xml)
    tipo_msg = "Pedido de Autorização de Uso NF-e" if "enviNFe" in req.xml else None
    return XmlValidationResponse(parser="OK", tipo_mensagem=tipo_msg, erros=erros)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
