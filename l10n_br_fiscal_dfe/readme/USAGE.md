## Dashboard

O menu **Faturamento > DF-e Queries > Third-party NF-e** exibe a lista de
documentos recebidos. No topo da tela, um banner mostra:

- **Last Query**: data e status da última consulta à SEFAZ
- **Next Query**: próxima consulta agendada e status do auto-fetch
- **NSU**: progresso de sincronização (último NSU / máximo NSU)
- **Documents Today**: documentos de terceiros recebidos hoje
- **Pending Import**: NF-e completas ainda não importadas como documento fiscal

O banner também exibe alertas quando o ambiente está em homologação ou
quando há inatividade superior a 30 dias (após 60 dias sem consulta, a
SEFAZ para de gerar NSUs para o CNPJ).

## Consulta manual

- **Search All**: busca todos os documentos a partir do último NSU. Respeita
  o cooldown — se houver consulta agendada no futuro, exibe notificação com
  o tempo restante.
- **Specific Search**: abre wizard para buscar por chave de acesso (com
  validação do dígito verificador) ou por NSU específico.

## Documentos recebidos

Cada documento na lista mostra: status (completa/resumo/cancelada), chave de
acesso, emissor, CNPJ, valor, CFOPs, status de manifestação. Ações
disponíveis:

- **XML**: download do XML da NF-e completa
- **DANFE**: gera e baixa o DANFE em PDF
- **Import**: importa a NF-e como `l10n_br_fiscal.document`
- **Manifest**: abre wizard de manifestação do destinatário

## Download em lote

Na tree view, selecione múltiplos documentos e use
**Actions > Download XMLs (zip)** para baixar todos os XMLs completos em um
arquivo zip.

## Manifestação automática

Com a opção **Manifestação automática** habilitada na empresa, o módulo
envia automaticamente uma ciência da operação para cada resumo de NF-e
recebido. O envio é feito via `queue_job` no canal `root.dfe`.

## Log de distribuição

Acessível via o botão de link no card "Last Query" do banner, o log
registra cada interação com a SEFAZ incluindo o XML SOAP de request e
response completos, útil para depuração de problemas.
