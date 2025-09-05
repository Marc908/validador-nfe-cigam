# 🚀 Validador NF-e Local (FastAPI)

API para validação de arquivos **XML da NF-e** de forma **local**.  
Valida tanto o **schema XSD oficial** quanto **regras de negócio**, retornando **códigos de rejeição (cStat)** idênticos ao validador da SEFAZ.

---

## ✨ Funcionalidades

- ✅ Validação contra **XSD local** (sem depender da SEFAZ).  
- ✅ Verificação de **regras de negócio** (CST, CFOP, campos obrigatórios, etc).  
- ✅ Retorno no formato oficial da NF-e (`cStat` + `xMotivo`).  
- ✅ Integração automática com os **códigos oficiais de rejeição da SEFAZ**, com **cache de 24h**.  
- ✅ API construída em **FastAPI** com suporte a deploy em qualquer ambiente (Docker, Railway, Render, etc).  

---

## 📂 Estrutura do Projeto

