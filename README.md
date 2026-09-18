# 🔄 P2P File Sync - UDP

Sistema distribuído de sincronização de arquivos ponto a ponto (Peer-to-Peer), desenvolvido em Python para a disciplina de **Redes de Computadores: Aplicação e Transporte** da Unisinos.

O projeto implementa nós que atuam simultaneamente como cliente e servidor, mantendo um diretório local sincronizado de forma autônoma e sem necessidade de um servidor central.

---

## 🚀 Funcionalidades e Critérios Atendidos

- **Arquitetura Peer-to-Peer (Critérios 2, 3 e 4):** Criação de servidor e cliente UDP integrados no mesmo nodo de forma descentralizada[cite: 1, 3].
- **Transporte via UDP (`SOCK_DGRAM`):** Comunicação em nível de transporte usando datagramas UDP com tratamento de JSON[cite: 1, 3].
- **Protocolo na Camada de Aplicação:** Segmentação de arquivos em blocos de 1KB com codificação Base64 e mensagens estruturadas (`ANUNCIO`, `PEDIR`, `DADOS`, `REMOVIDO`, `LISTA_REQ`, `LISTA_RESP`)[cite: 1, 3].
- **Monitoramento em Tempo Real (Critérios 5, 6 e 7):** Detecção automática de novos arquivos e exclusões no diretório monitorado (`tmp/`) com propagação automática para os peers[cite: 1, 3].
- **Entrada Autônoma de Novos Nós (Critério 10):** Ao iniciar com a pasta vazia, o nodo envia `LISTA_REQ` e baixa autonomamente todos os arquivos já existentes na rede[cite: 1, 3].
- **Visão Sumarizada (Critério 8):** Comando interativo `status` no terminal exibindo informações consolidadas da rede e arquivos locais[cite: 1, 3].
- **Compatibilidade Multiambiente (Critério 9):** Testado e operante entre diferentes ambientes (Bare Metal Windows e VM Linux)[cite: 1, 3].

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3
- **Módulos Nativos:** `socket`, `threading`, `json`, `os`, `base64`, `argparse`
- **Protocolo de Transporte:** UDP

---

## ⚙️ Configuração e Execução

### 1. Pré-requisitos
Apenas o Python 3 instalado. Nenhuma dependência externa via `pip` é necessária. A pasta `tmp/` será criada automaticamente se não existir.

### 2. Configurar os Peers
Edite o arquivo `config.json` para definir o seu IP/porta e adicionar os endereços dos outros nós da rede:

```json
{
  "meu_nodo": {
    "ip": "0.0.0.0",
    "porta": 5000
  },
  "pasta_sincronizada": "tmp",
  "peers": [
    {
      "nome": "Peer-A",
      "ip": "192.168.1.X",
      "porta": 5000
    },
    {
      "nome": "Peer-B",
      "ip": "192.168.1.Y",
      "porta": 5000
    }
  ]
}