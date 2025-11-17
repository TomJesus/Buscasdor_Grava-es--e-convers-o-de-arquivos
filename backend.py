
# backend.py
import os
import re
import shutil
import subprocess
import tempfile
import threading
from collections import defaultdict
import pandas as pd
import pyodbc
from sqlalchemy import create_engine

# ===============================================================
# AJUSTE IMPORTANTE: Configuração de ambiente Tcl/Tk antes de tudo
# ===============================================================
os.environ['TCL_LIBRARY'] = r'C:\Users\aelton.jesus\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'
os.environ['TK_LIBRARY']  = r'C:\Users\aelton.jesus\AppData\Local\Programs\Python\Python313\tcl\tk8.6'

# ====== CONFIGURAÇÕES (Atualize conforme necessário) ======
CAMINHO_FFMPEG = r'C:\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe'
MAX_THREADS = 8

# === CONEXÃO SQL SERVER =========================================
def get_connection():
    raw_conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=172.16.0.33;"
        "DATABASE=Captacao;"
        "UID=Paulo.cruz;"
        "PWD=Fmp1234@;"
        "TrustServerCertificate=yes;"
    )
    engine = create_engine("mssql+pyodbc://", creator=lambda: raw_conn)
    return engine


# === FUNÇÕES AUXILIARES =========================================
def buscar_wav_por_data_e_prefixo(nome_arquivo_base):
    try:
        nome_base = os.path.basename(nome_arquivo_base).strip().lower()
        nome_base_sem_ext = os.path.splitext(nome_base)[0]
        partes = nome_base_sem_ext.split('-')
        if len(partes) < 5:
            return None
        data_str = partes[3]
        if len(data_str) != 8:
            return None
        ano, mes, dia = data_str[:4], str(int(data_str[4:6])), str(int(data_str[6:8]))
        pasta = os.path.join("D:\\", "GRAVACOES ESTILO IMP", "DISCADORA ANTIGA", ano, mes, dia)
        if not os.path.isdir(pasta):
            return None
        for arquivo in os.listdir(pasta):
            if os.path.splitext(arquivo)[0].lower() == nome_base_sem_ext:
                return os.path.join(pasta, arquivo)
        return None
    except Exception:
        return None


def carregar_telefones(caminho_excel=None, telefone_manual=None):
    telefones_info = []
    if telefone_manual:
        for t in telefone_manual.split(","):
            telefones_info.append((t.strip(), t.strip(), t.strip()))
    elif caminho_excel:
        df_auditoria = pd.read_excel(caminho_excel, sheet_name=None)
        for aba, df in df_auditoria.items():
            for _, linha in df.iterrows():
                telefone = str(linha.get("Telefone")).strip().replace(".", "").replace("-", "")
                telefone = telefone.split(".")[0]
                instalacao = str(linha.get("Instalação")).strip()
                nome_titular = str(linha.get("Nome titular")).strip()
                if pd.notna(telefone):
                    telefones_info.append((telefone, instalacao, nome_titular))
    return telefones_info

# === CONSULTA NO BANCO ==========================================
def executar_busca_sem_salvar(telefones_info, log_callback=None):
    engine = get_connection()
    if log_callback: log_callback("⏳ Iniciando busca no banco...")

    telefones = [t[0].strip() for t in telefones_info if str(t[0]).strip()]
    telefones = list(set(telefones))

    if not telefones:
        if log_callback: log_callback("[ERRO] Nenhum telefone válido informado.")
        return []

    df_gravacoes_total = pd.DataFrame()
    bloco = 1000

    for i in range(0, len(telefones), bloco):
        subset = telefones[i:i + bloco]
        placeholders = ", ".join(["?"] * len(subset))
        query = f"""
            SELECT [Telefone Origem], [Telefone Destino], [CAMINHO GRAVAÇÕES]
            FROM GravacoesEstilo
            WHERE [Telefone Origem] IN ({placeholders})
            OR [Telefone Destino] IN ({placeholders})
        """
        conn = engine.raw_connection()
        try:
            df_temp = pd.read_sql(query, conn, params=subset + subset)
            df_gravacoes_total = pd.concat([df_gravacoes_total, df_temp], ignore_index=True)
        finally:
            conn.close()
        if log_callback: log_callback(f"[INFO] Lote {i//bloco + 1} processado ({len(df_gravacoes_total)} registros)")

    if df_gravacoes_total.empty:
        if log_callback: log_callback("[!] Nenhuma gravação encontrada.")
        return []

    gravacoes_dict = defaultdict(list)
    for _, row in df_gravacoes_total.iterrows():
        for coluna in ["Telefone Origem", "Telefone Destino"]:
            tel = row.get(coluna)
            if pd.notna(tel):
                telefone = str(tel).split('.')[0].strip().replace("-", "").replace(" ", "")
                caminho = str(row.get("CAMINHO GRAVAÇÕES")).strip()
                if caminho:
                    gravacoes_dict[telefone].append(caminho)

    resultados = []
    for telefone, instalacao, nome in telefones_info:
        caminhos_encontrados = gravacoes_dict.get(telefone, [])
        if not caminhos_encontrados:
            if log_callback: log_callback(f"[!] Telefone não localizado: {telefone}")
            continue
        arquivos_unicos = list(dict.fromkeys(caminhos_encontrados))
        for idx, caminho in enumerate(arquivos_unicos, start=1):
            resultados.append({
                "telefone": telefone,
                "instalacao": instalacao,
                "nome": nome.replace("/", "-").replace("\\", "-").strip(),
                "idx": idx,
                "caminho_original": caminho,
                "formato": os.path.splitext(caminho)[1].lower().replace('.', '')
            })

    if log_callback: log_callback(f"[INFO] Total de arquivos listados: {len(resultados)}")
    return resultados


# === CONVERSÃO PARA MP3 TEMPORÁRIO ====================================
def preparar_arquivo_para_play(caminho_original, log_callback=None):
    try:
        if not os.path.exists(caminho_original):
            alt = buscar_wav_por_data_e_prefixo(caminho_original)
            if alt and os.path.exists(alt):
                caminho_original = alt
            else:
                if log_callback: log_callback(f"[ERRO] Arquivo não encontrado: {caminho_original}")
                return None

        ext = os.path.splitext(caminho_original)[1].lower()
        temp_dir = os.path.join(tempfile.gettempdir(), "buscagravacoes_temp")
        os.makedirs(temp_dir, exist_ok=True)

        nome_temp = os.path.splitext(os.path.basename(caminho_original))[0] + ".mp3"
        destino_temp = os.path.join(temp_dir, nome_temp)

        if os.path.exists(destino_temp) and os.path.getmtime(destino_temp) > os.path.getmtime(caminho_original):
            return destino_temp

        if ext in [".gsm", ".wav"]:
            comando = f'"{CAMINHO_FFMPEG}" -y -i "{caminho_original}" "{destino_temp}"'
        elif ext == ".mp3":
            shutil.copy2(caminho_original, destino_temp)
            return destino_temp
        else:
            if log_callback: log_callback(f"[✗] Formato não suportado: {ext}")
            return None

        result = subprocess.run(comando, shell=True, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(destino_temp):
            return destino_temp
        else:
            if log_callback: log_callback(f"[ERRO] FFmpeg falhou: {result.stderr}")
            return None

    except Exception as e:
        if log_callback: log_callback(f"[ERRO preparar_arquivo_para_play] {e}")
        return None


# === SALVAR ARQUIVO VIA DIALOG ====================================
def salvar_arquivo_via_dialog(caminho_origem, sugerido_nome=None):
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        default_name = sugerido_nome or os.path.basename(caminho_origem)
        destino = filedialog.asksaveasfilename(
            title="Salvar gravação como...",
            defaultextension=".mp3",
            initialfile=default_name,
            filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav"), ("Todos os arquivos", "*.*")]
        )
        root.destroy()

        if not destino:
            return None

        ext_origem = os.path.splitext(caminho_origem)[1].lower()
        if ext_origem == ".gsm":
            comando = f'"{CAMINHO_FFMPEG}" -y -i "{caminho_origem}" "{destino}"'
            subprocess.run(comando, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            shutil.copy2(caminho_origem, destino)

        return destino
    except Exception as e:
        print(f"Erro no diálogo de salvamento: {e}")
        return None
