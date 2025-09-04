# errors_friendly.py

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
