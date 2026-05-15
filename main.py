import os
import threading
import urllib.parse
import webview


from http.server import HTTPServer, SimpleHTTPRequestHandler

from backend import (
    carregar_telefones,
    executar_busca_sem_salvar,
    preparar_arquivo_para_play
)


# =========================================================
# SERVIDOR LOCAL PARA STREAM DE ÁUDIO
# =========================================================

class AudioFileHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        try:
            if self.path.startswith('/audio/'):

                file_path = urllib.parse.unquote(self.path[7:])

                if os.path.exists(file_path):

                    ext = os.path.splitext(file_path)[1].lower()

                    mime_type = {
                        '.mp3': 'audio/mpeg',
                        '.wav': 'audio/wav'
                    }.get(ext, 'application/octet-stream')

                    self.send_response(200)
                    self.send_header('Content-type', mime_type)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()

                    with open(file_path, 'rb') as f:
                        self.wfile.write(f.read())

                else:
                    self.send_error(404, "Arquivo não encontrado")

            else:
                self.send_error(404, "Rota inválida")

        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, format, *args):
        pass


def iniciar_servidor():
    server = HTTPServer(('******', ****), AudioFileHandler)
    print("Servidor de áudio iniciado em *****)
    server.serve_forever()


# =========================================================
# API PYTHON → FRONTEND
# =========================================================

class API:

    def __init__(self):
        pass


    # -----------------------------------------------------
    # ABRIR EXCEL (SEM TKINTER)
    # -----------------------------------------------------

    def abrir_excel(self):

        try:

            resultado = webview.windows[0].create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=('Excel (*.xlsx;*.xls)',)
            )

            if resultado:
                caminho = resultado[0]
                self.log(f"[✓] Excel selecionado: {caminho}")
                return caminho

            return None

        except Exception as e:
            self.log(f"[ERRO] Abrir Excel: {str(e)}")
            return None


    # -----------------------------------------------------
    # BUSCAR TELEFONES
    # -----------------------------------------------------

    def buscar(self, telefones_str, caminho_excel):

        try:

            telefones_info = carregar_telefones(
                caminho_excel,
                telefones_str
            )

            resultados = executar_busca_sem_salvar(
                telefones_info,
                log_callback=self.log
            )

            return resultados

        except Exception as e:

            self.log(f"[ERRO] Busca: {str(e)}")
            return []


    # -----------------------------------------------------
    # PREPARAR PLAY
    # -----------------------------------------------------

    def preparar_play(self, caminho_original):

        try:

            caminho_temp = preparar_arquivo_para_play(
                caminho_original,
                log_callback=self.log
            )

            if caminho_temp and os.path.exists(caminho_temp):

                encoded = urllib.parse.quote(caminho_temp, safe='')

                return f"http://127.0.0.1:8765/audio/{encoded}"

            return None

        except Exception as e:

            self.log(f"[ERRO] Play: {str(e)}")
            return None


    # -----------------------------------------------------
    # SALVAR ARQUIVO (SEM TKINTER)
    # -----------------------------------------------------

    def salvar(self, caminho_origem, nome_sugerido="arquivo.mp3"):

        try:

            if not os.path.exists(caminho_origem):

                self.log("[ERRO] Arquivo não encontrado")
                return None


            resultado = webview.windows[0].create_file_dialog(
                webview.FileDialog.SAVE,
                save_filename=nome_sugerido
            )

            if resultado:

                destino = resultado[0]

                with open(caminho_origem, 'rb') as origem:
                    with open(destino, 'wb') as dest:
                        dest.write(origem.read())

                self.log(f"[✓] Salvo em: {destino}")

                return destino


            self.log("[!] Salvamento cancelado")
            return None


        except Exception as e:

            self.log(f"[ERRO] Salvar: {str(e)}")
            return None


    # -----------------------------------------------------
    # LOG → FRONTEND
    # -----------------------------------------------------

    def log(self, mensagem):

        print(mensagem)

        try:

            mensagem_js = mensagem.replace("\\", "\\\\").replace("'", "\\'")

            webview.windows[0].evaluate_js(
                f"window.addLog('{mensagem_js}')"
            )

        except:
            pass


# =========================================================
# INICIALIZAÇÃO
# =========================================================

def iniciar_app():

    # inicia servidor de áudio
    threading.Thread(
        target=iniciar_servidor,
        daemon=True
    ).start()


    api = API()

    webview.create_window(
        title="Busca de Gravações",
        url="web/index.html",
        width=1100,
        height=720,
        js_api=api
    )

    webview.start(debug=False)


if __name__ == '__main__':

    iniciar_app()