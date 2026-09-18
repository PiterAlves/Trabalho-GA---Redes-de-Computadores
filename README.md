# Sistema P2P de Sincronização de Arquivos (UDP)

Projeto desenvolvido para a disciplina de **Redes de Computadores: Aplicação e Transporte** (UNISINOS).

## Estrutura do Projeto
- `nodo.py`: Implementação do nodo que atua simultaneamente como Cliente e Servidor UDP com multithreading.
- `config.json`: Arquivo de configuração que define o IP/porta local e a lista de peers conhecidos.
- `tmp/`: Diretório sincronizado onde os arquivos são adicionados ou removidos.

## Fases e Critérios Atendidos:
- **Fase 1 (Critérios 2, 3 e 4):** Criação do servidor UDP, cliente UDP e integração unificada em cada nodo com leitura via JSON.
- **Fase 2:** Protocolo em nível de aplicação com fatiamento de dados em blocos e mensagens tipadas (`ANUNCIO`, `PEDIR`, `DADOS`, `REMOVIDO`, `LISTA_REQ`, `LISTA_RESP`).
- **Fase 3 (Critérios 5, 6 e 7):** Monitoramento contínuo da pasta `tmp/` com propagação automática de adição e remoção para os peers.
- **Fase 4 (Critério 10):** Ao iniciar com a pasta vazia, o nodo envia `LISTA_REQ` e baixa autonomamente todos os arquivos já existentes na rede.
- **Critério 8:** Comando `status` interativo no terminal exibindo informações sumarizadas.

## Como Executar
Copie o projeto para a sua maquina, ajuste o `config.json` se necessário (ou passe a porta/config) e rode:
```bash
python3 nodo.py
```
