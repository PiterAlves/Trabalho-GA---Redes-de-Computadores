import socket
import json
import os
import time
import threading
import base64
import math
import argparse

CHUNK_SIZE = 1024  # Tamanho do bloco em bytes para caber com folga no datagrama UDP

class PeerNode:
    def __init__(self, config_path="config.json", porta_override=None):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.minha_porta = porta_override if porta_override else self.config["meu_nodo"]["porta"]
        self.meu_ip = self.config["meu_nodo"]["ip"]
        self.pasta = self.config.get("pasta_sincronizada", "tmp")
        self.peers = self.config.get("peers", [])

        os.makedirs(self.pasta, exist_ok=True)

        # Socket UDP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Permite reusar a porta rapidamente se reiniciar
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.meu_ip, self.minha_porta))

        # Controle de estado local
        self.arquivos_locais = set(os.listdir(self.pasta))
        self.blocos_em_recebimento = {}  # {nome_arquivo: {parte_idx: dados, 'total': N}}
        self.running = True

        print(f"[*] Nodo inicializado em {self.meu_ip}:{self.minha_porta}")
        print(f"[*] Pasta sincronizada: '{os.path.abspath(self.pasta)}'")
        print(f"[*] Arquivos iniciais: {list(self.arquivos_locais)}")

    def enviar_mensagem(self, msg_dict, ip_dest, porta_dest):
        # Envia mensagem serializada em JSON via UDP
        try:
            dados = json.dumps(msg_dict).encode("utf-8")
            self.sock.sendto(dados, (ip_dest, porta_dest))
        except Exception as e:
            print(f"[!] Erro ao enviar para {ip_dest}:{porta_dest} -> {e}")

    def broadcast(self, msg_dict):
        """Envia para todos os peers configurados (exceto a si próprio)"""
        for peer in self.peers:
            p_ip = peer["ip"]
            p_porta = peer["porta"]
            if (p_ip in ["127.0.0.1", "localhost", self.meu_ip]) and (p_porta == self.minha_porta):
                continue
            self.enviar_mensagem(msg_dict, p_ip, p_porta)

    def thread_escuta(self):
        # Servidor UDP: escuta e processa todas as mensagens de entrada
        while self.running:
            try:
                dados_brutos, addr = self.sock.recvfrom(65507)
                if not dados_brutos:
                    continue
                mensagem = json.loads(dados_brutos.decode("utf-8"))
                self.processar_mensagem(mensagem, addr)
            except Exception as e:
                if self.running:
                    print(f"[!] Erro no loop de escuta: {e}")

    def processar_mensagem(self, msg, addr):
        tipo = msg.get("tipo")

        # 1. Anúncio de novo arquivo na rede
        if tipo == "ANUNCIO":
            nome = msg.get("nome")
            tamanho = msg.get("tamanho")
            caminho_local = os.path.join(self.pasta, nome)
            if not os.path.exists(caminho_local):
                print(f"[+] ANUNCIO recebido: '{nome}' ({tamanho} bytes) de {addr}. Solicitando...")
                self.enviar_mensagem({"tipo": "PEDIR", "nome": nome}, addr[0], addr[1])

        # 2. Solicitação de arquivo
        elif tipo == "PEDIR":
            nome = msg.get("nome")
            caminho_local = os.path.join(self.pasta, nome)
            if os.path.exists(caminho_local):
                print(f"[>] PEDIR recebido de {addr} para '{nome}'. Enviando em pedaços...")
                threading.Thread(target=self.enviar_arquivo_fatiado, args=(nome, addr), daemon=True).start()

        # 3. Pedaço de arquivo recebido
        elif tipo == "DADOS":
            nome = msg.get("nome")
            parte = msg.get("parte")
            total = msg.get("total")
            payload_b64 = msg.get("conteudo")

            if nome not in self.blocos_em_recebimento:
                self.blocos_em_recebimento[nome] = {"total": total, "partes": {}}

            self.blocos_em_recebimento[nome]["partes"][parte] = base64.b64decode(payload_b64)

            # Se todos os blocos chegaram, remonta o arquivo
            if len(self.blocos_em_recebimento[nome]["partes"]) == total:
                caminho_final = os.path.join(self.pasta, nome)
                with open(caminho_final, "wb") as f:
                    for i in range(total):
                        f.write(self.blocos_em_recebimento[nome]["partes"][i])
                
                del self.blocos_em_recebimento[nome]
                self.arquivos_locais.add(nome)
                print(f"[V] Arquivo '{nome}' recebido e sincronizado com sucesso!")

        # 4. Notificação de remoção
        elif tipo == "REMOVIDO":
            nome = msg.get("nome")
            caminho_local = os.path.join(self.pasta, nome)
            if os.path.exists(caminho_local):
                try:
                    os.remove(caminho_local)
                    self.arquivos_locais.discard(nome)
                    print(f"[-] REMOVIDO: Arquivo '{nome}' foi apagado por sincronização.")
                except Exception as e:
                    print(f"[!] Erro ao remover '{nome}': {e}")

        # 5. Pedido de lista para sincronização inicial (novo nodo)
        elif tipo == "LISTA_REQ":
            arquivos = list(os.listdir(self.pasta))
            self.enviar_mensagem({"tipo": "LISTA_RESP", "arquivos": arquivos}, addr[0], addr[1])

        # 6. Resposta com o catálogo de arquivos
        elif tipo == "LISTA_RESP":
            arquivos_remotos = msg.get("arquivos", [])
            for arq in arquivos_remotos:
                if arq not in os.listdir(self.pasta):
                    print(f"[*] Nodo novo se atualizando: solicitando '{arq}' de {addr}")
                    self.enviar_mensagem({"tipo": "PEDIR", "nome": arq}, addr[0], addr[1])

    def enviar_arquivo_fatiado(self, nome, addr):
        # Lê o arquivo local, divide em blocos de 1KB e envia em datagramas UDP com base64
        caminho = os.path.join(self.pasta, nome)
        if not os.path.exists(caminho):
            return

        with open(caminho, "rb") as f:
            conteudo = f.read()

        tamanho_total = len(conteudo)
        total_blocos = max(1, math.ceil(tamanho_total / CHUNK_SIZE))

        for i in range(total_blocos):
            inicio = i * CHUNK_SIZE
            fim = inicio + CHUNK_SIZE
            fatia = conteudo[inicio:fim]
            fatia_b64 = base64.b64encode(fatia).decode("utf-8")

            msg = {
                "tipo": "DADOS",
                "nome": nome,
                "parte": i,
                "total": total_blocos,
                "conteudo": fatia_b64
            }
            self.enviar_mensagem(msg, addr[0], addr[1])
            time.sleep(0.005)  # Pequeno delay para evitar buffer overflow em UDP

    def monitorar_pasta_local(self):
        # Monitora periodicamente a pasta local tmp para detectar adições e remoções manuais
        while self.running:
            try:
                arquivos_atuais = set(os.listdir(self.pasta))

                # Novos arquivos colocados manualmente na pasta
                novos = arquivos_atuais - self.arquivos_locais
                for arq in novos:
                    caminho = os.path.join(self.pasta, arq)
                    if os.path.isfile(caminho):
                        tam = os.path.getsize(caminho)
                        print(f"[!] Novo arquivo detectado na pasta: '{arq}'. Enviando ANUNCIO...")
                        self.arquivos_locais.add(arq)
                        self.broadcast({"tipo": "ANUNCIO", "nome": arq, "tamanho": tam})

                # Arquivos deletados manualmente da pasta
                deletados = self.arquivos_locais - arquivos_atuais
                for arq in deletados:
                    print(f"[!] Arquivo removido da pasta: '{arq}'. Enviando REMOVIDO...")
                    self.arquivos_locais.remove(arq)
                    self.broadcast({"tipo": "REMOVIDO", "nome": arq})

            except Exception as e:
                print(f"[!] Erro ao monitorar pasta: {e}")

            time.sleep(1.5)

    def iniciar_sincronizacao(self):
        # Ao iniciar, pede a lista de arquivos para todos os peers (Fase 4 / Critério 10)
        print("[*] Enviando LISTA_REQ para os peers conhecidos...")
        self.broadcast({"tipo": "LISTA_REQ"})

    def executar(self):
        # 1. Inicia thread do servidor UDP
        t_escuta = threading.Thread(target=self.thread_escuta, daemon=True)
        t_escuta.start()

        # 2. Inicia thread de monitoramento da pasta
        t_monitor = threading.Thread(target=self.monitorar_pasta_local, daemon=True)
        t_monitor.start()

        # 3. Pede lista para a rede
        time.sleep(0.5)
        self.iniciar_sincronizacao()

        print("\n=== NODO ATIVO E OPERANTE ===")
        print("Comandos disponíveis no terminal:")
        print("  status -> Exibe arquivos sincronizados locais e peers configurados")
        print("  sync   -> Força nova requisição de sincronização (LISTA_REQ)")
        print("  sair   -> Encerra o nodo\n")

        while self.running:
            try:
                cmd = input().strip().lower()
                if cmd == "status":
                    arqs = os.listdir(self.pasta)
                    print("\n--- STATUS DO NODO ---")
                    print(f"Porta: {self.minha_porta}")
                    print(f"Total de arquivos locais: {len(arqs)}")
                    print(f"Arquivos: {arqs}")
                    print(f"Peers na lista: {[p['nome'] + ' (' + p['ip'] + ':' + str(p['porta']) + ')' for p in self.peers]}")
                    print("----------------------\n")
                elif cmd == "sync":
                    self.iniciar_sincronizacao()
                elif cmd == "sair":
                    print("[*] Encerrando nodo...")
                    self.running = False
                    self.sock.close()
                    break
            except (KeyboardInterrupt, EOFError):
                self.running = False
                self.sock.close()
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nodo P2P UDP - Sincronização de Arquivos")
    parser.add_argument("--config", default="config.json", help="Caminho do arquivo config.json")
    parser.add_argument("--porta", type=int, default=None, help="Sobrescrever a porta local")
    args = parser.parse_args()

    nodo = PeerNode(config_path=args.config, porta_override=args.porta)
    nodo.executar()
