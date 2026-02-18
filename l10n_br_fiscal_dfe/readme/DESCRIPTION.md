Distribuição de documentos fiscais

Utiliza `queue_job` para executar a consulta de distribuição DF-e de forma
assíncrona, evitando conflitos de lock no cron.

## Configuração do queue_job

### 1. Carregar o módulo como server wide module

O `queue_job` precisa ser carregado na inicialização do Odoo. Adicione na
configuração do servidor ou como variável de ambiente:

```ini
[options]
server_wide_modules = web,queue_job
```

Ou via variável de ambiente:

```
SERVER_WIDE_MODULES=web,queue_job
```

### 2. Configurar o canal `root.dfe`

O módulo registra os jobs de distribuição DF-e no canal `root.dfe`.
É **obrigatório** configurar este canal com capacidade máxima de **1 job
simultâneo**, caso contrário consultas concorrentes à SEFAZ podem causar
erro 656 (consumo indevido) e bloqueio temporário do CNPJ.

No arquivo de configuração do Odoo:

```ini
[queue_job]
channels = root:2,root.dfe:1
```

Ou via variável de ambiente:

```
ODOO_QUEUE_JOB_CHANNELS=root:2,root.dfe:1
```

### 3. Ambiente de produção

Em produção, o Odoo deve rodar com `workers > 0` para que o jobrunner
inicie como processo dedicado. Exemplo:

```ini
[options]
workers = 2
```

### 4. Ambiente de desenvolvimento

Com `--workers=0` (modo threaded), o queue_job funciona normalmente —
ele cria uma thread extra no mesmo processo para processar os jobs.
Não é necessária nenhuma configuração adicional além dos passos 1 e 2.
