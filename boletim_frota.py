## https://api.telegram.org/bot9224945778:AAHYt22sT5uG-rkLY9rldMy1bWZ5EBYmPQQ/getUpdates

import os
import time
import urllib.parse
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. Localiza a pasta exata do script e carrega o arquivo .env
pasta_projeto = Path(__file__).resolve().parent
load_dotenv(dotenv_path=pasta_projeto / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def registrar_log(texto: str):
    """Salva o histórico de execuções e possíveis erros em log_envios.txt na pasta do projeto."""
    caminho_log = pasta_projeto / "log_envios.txt"
    with open(caminho_log, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {texto}\n")


if not GEMINI_API_KEY:
    erro = f"Chave GEMINI_API_KEY não encontrada em: {pasta_projeto / '.env'}"
    registrar_log(f"ERRO DE CONFIGURAÇÃO: {erro}")
    raise ValueError(erro)

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    erro = f"Credenciais do Telegram não encontradas em: {pasta_projeto / '.env'}"
    registrar_log(f"ERRO DE CONFIGURAÇÃO: {erro}")
    raise ValueError(erro)


def buscar_noticias_bahia() -> str:
    """Coleta manchetes recentes do Google News RSS sobre rodovias e clima na Bahia."""
    consultas = [
        "rodovias Bahia Seinfra interdição chuva",
        "PRF Bahia BR-324 BR-116 BR-101 trânsito",
        "Inema previsão do tempo alerta chuva Bahia"
    ]
    manchetes = []

    for termo in consultas:
        query = urllib.parse.quote(termo)
        url = f"https://news.google.com/rss/search?q={query}+when:2d&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "xml")
            for item in soup.find_all("item")[:5]:
                titulo = item.title.text if item.title else ""
                pub_date = item.pubDate.text if item.pubDate else ""
                manchetes.append(f"- [{pub_date}] {titulo}")
        except Exception as e:
            print(f"Aviso ao buscar '{termo}': {e}")

    return "\n".join(manchetes) if manchetes else "Sem manchetes críticas indexadas nas últimas 48h."


def gerar_boletim_rodovias() -> str:
    """Descobre automaticamente os modelos disponíveis na conta e sintetiza o boletim."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    noticias_brutas = buscar_noticias_bahia()

    prompt = f"""
    Data de hoje: {data_hoje}.
    Com base nas notícias recentes coletadas abaixo sobre as rodovias da BAHIA e previsão do tempo:

    {noticias_brutas}

    Atue como um Coordenador de Logística. Gere um boletim EXECUTIVO, DIRETO e SEM REDUNDÂNCIA para enviar no Telegram dos motoristas e supervisores de frota.
    
    Use EXATAMENTE esta estrutura com formatação para Telegram (*negrito*):

    🚛 *BOLETIM OPERACIONAL DE ROTAS - BAHIA ({data_hoje})*

    🔴 *BLOQUEIOS E INTERDIÇÕES CRÍTICAS:*
    - Liste apenas trechos interditados ou em meia pista mencionados. Se não houver, escreva: "Sem bloqueios totais registrados nas últimas 24h."

    🟡 *PONTOS DE ATENÇÃO E RETENÇÕES (BRs e BAs):*
    - Destaque obras, erosões, passagens molhadas, cidades em alerta, entrocamentos em alerta ou com restrições, tráfego intenso ou fiscalização (BR-324, BR-116, BR-101, BR-242, BA-093, BA-099). Seja telegráfico.

    ⛈️ *CLIMA E RISCO NA PISTA (PRÓXIMAS 48H):*
    - Resumo objetivo das regiões com alerta de chuva forte, enxurrada ou vento para caminhões baú/sider.

    ✅ *DIRETRIZ PARA A FROTA HOJE:*
    - 2 a 3 ações práticas curtas (ex: rotas de desvio, janelas de horário a evitar, cuidado em passagens molhadas).
    """

    # Descobre os modelos ativos na sua chave API
    modelos_candidatos = []
    try:
        for m in client.models.list():
            nome = m.name.replace("models/", "")
            if ("gemini" in nome or "gemma" in nome) and "embedding" not in nome and "vision" not in nome:
                modelos_candidatos.append(nome)
    except Exception:
        modelos_candidatos = ["gemini-flash-latest", "gemini-pro-latest", "gemma-3-27b-it"]

    # Prioriza modelos Flash e Gemma (cotas gratuitas maiores)
    modelos_candidatos.sort(key=lambda x: (0 if "flash" in x else (1 if "gemma" in x else 2)))

    for modelo in modelos_candidatos:
        try:
            print(f"Tentando gerar boletim com o modelo: {modelo}...")
            response = client.models.generate_content(
                model=modelo,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2),
            )
            if response.text:
                print(f"Sucesso usando {modelo}!")
                registrar_log(f"Boletim gerado com sucesso via {modelo}.")
                return response.text
        except Exception as e:
            print(f"Pulando {modelo} (cota/indisponível): {str(e)[:120]}...")
            time.sleep(2)

    raise RuntimeError("Nenhum modelo com cota disponível respondeu no momento.")


def enviar_telegram_silencioso(mensagem: str):
    """Envia o boletim para o Telegram com fallback automático caso haja erro de formatação."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, json=payload, timeout=20)
        # Se o Telegram rejeitar o Markdown por algum caractere especial, reenvia como texto puro
        if resp.status_code == 400:
            payload.pop("parse_mode")
            resp = requests.post(url, json=payload, timeout=20)

        resp.raise_for_status()
        msg_ok = "Boletim enviado com sucesso para o Telegram!"
        print(f"[{datetime.now()}] {msg_ok}")
        registrar_log(msg_ok)
    except Exception as e:
        msg_erro = f"Erro ao enviar no Telegram: {e}"
        print(f"[{datetime.now()}] {msg_erro}")
        registrar_log(msg_erro)


if __name__ == "__main__":
    try:
        registrar_log("Iniciando execução do script...")
        print("Coletando notícias e gerando boletim da Bahia...")
        boletim = gerar_boletim_rodovias()

        print("\n--- PRÉVIA DO BOLETIM ---\n")
        print(boletim)
        print("\n-------------------------\n")

        enviar_telegram_silencioso(boletim)
    except Exception as erro_geral:
        registrar_log(f"FALHA CRÍTICA NA EXECUÇÃO: {erro_geral}")
        raise
