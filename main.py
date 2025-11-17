import os
from tkinter import filedialog
import tkinter as tk
import webview
import threading
from backend import carregar_telefones, executar_busca_sem_salvar, preparar_arquivo_para_play, salvar_arquivo_via_dialog
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse


class AudioFileHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        try:
            # Decodifica o caminho do arquivo da URL
            if self.path.startswith('/audio/'):
                file_path = urllib.parse.unquote(self.path[7:])  # Remove '/audio/'

                # Verifica se o arquivo existe
                if os.path.exists(file_path):
                    # Determina o tipo MIME
                    ext = os.path.splitext(file_path)[1].lower()
                    mime_type = "audio/mpeg" if ext == '.mp3' else "audio/wav"

                    # Envia o arquivo
                    self.send_response(200)
                    self.send_header('Content-type', mime_type)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()

                    with open(file_path, 'rb') as f:
                        self.wfile.write(f.read())
                    return
                else:
                    self.send_error(404, "File not found")
                    return
            else:
                self.send_error(404, "Invalid path")

        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")

    def log_message(self, format, *args):
        # Suprime logs do servidor para não poluir o console
        pass


def run_server():
    server = HTTPServer(('localhost', 8765), AudioFileHandler)
    print("Servidor de áudio rodando na porta 8765")
    server.serve_forever()


class API:

    def abrir_excel(self):
        root = tk.Tk()
        root.withdraw()  # oculta janela principal
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo Excel",
            filetypes=[("Planilhas Excel", "*.xlsx *.xls")]
        )
        print(f"[DEBUG] Arquivo selecionado: {caminho}")
        return caminho or None

    def __init__(self):
        self._log_callbacks = []

    def buscar(self, telefones_str, caminho_excel):
        try:
            telefones_info = carregar_telefones(caminho_excel, telefones_str)
            resultados = executar_busca_sem_salvar(telefones_info, log_callback=self.log)
            return resultados
        except Exception as e:
            self.log(f"[ERRO] Busca: {str(e)}")
            return []

    def preparar_play(self, caminho_original):
        try:
            caminho_temp = preparar_arquivo_para_play(caminho_original, log_callback=self.log)
            if caminho_temp and os.path.exists(caminho_temp):
                # Retorna URL do servidor local
                encoded_path = urllib.parse.quote(caminho_temp, safe='')
                return f"http://localhost:8765/audio/{encoded_path}"
            else:
                self.log(f"[ERRO] Arquivo temporário não criado: {caminho_original}")
                return None
        except Exception as e:
            self.log(f"[ERRO] Preparar play: {str(e)}")
            return None

    def salvar(self, caminho_origem, nome_sugerido=None):
        try:
            if not os.path.exists(caminho_origem):
                self.log(f"[ERRO] Arquivo original não encontrado: {caminho_origem}")
                return None

            salvo = salvar_arquivo_via_dialog(caminho_origem, sugerido_nome=nome_sugerido)
            if salvo:
                self.log(f"[✓] Salvo em: {salvo}")
                return salvo
            else:
                self.log("[!] Salvamento cancelado.")
                return None
        except Exception as e:
            self.log(f"[ERRO] Salvamento: {str(e)}")
            return None

    def log(self, mensagem):
        print(mensagem)
        try:
            mensagem_escape = mensagem.replace("'", "\\'")
            js = f"window.addLog('{mensagem_escape}')"
            webview.windows[0].evaluate_js(js)
        except Exception as e:
            print(f"Erro ao enviar log para frontend: {e}")


if __name__ == '__main__':
    # Inicia o servidor em thread separada
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    api = API()
    window = webview.create_window(
        "Busca de Gravações - Estilo",
        "web/index.html",
        width=1100,
        height=720,
        js_api=api
    )
    webview.start(debug=False)

