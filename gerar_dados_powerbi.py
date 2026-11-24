import os
import json
import time
import urllib.parse
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. Diretórios e Variáveis de Ambiente (Salva exclusivamente dentro de 01_Projetos/monitor-rodovias-ba)
pasta_script = Path(__file__).resolve().parent
load_dotenv(dotenv_path=pasta_script / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Chave GEMINI_API_KEY não encontrada.")

FUSO_BAHIA = ZoneInfo("America/Bahia")

# 24 Cidades Estratégicas (12 Polos Principais + 12 Cidades do Entorno e Entroncamentos)
CIDADES_MONITORADAS = [
    # --- 12 POLOS PRINCIPAIS ---
    {
        "cidade": "Salvador",
        "macrorregiao": "Leste / RMS",
        "territorio_identidade": "Metropolitano de Salvador",
        "rodovia_principal": "BR-324 / BA-099",
        "lat": -12.9714,
        "lon": -38.5014,
    },
    {
        "cidade": "Feira de Santana",
        "macrorregiao": "Centro-Norte",
        "territorio_identidade": "Portal do Sertão",
        "rodovia_principal": "BR-324 / BR-116 / BR-101",
        "lat": -12.2664,
        "lon": -38.9663,
    },
    {
        "cidade": "Serrinha",
        "macrorregiao": "Nordeste",
        "territorio_identidade": "Território do Sisal",
        "rodovia_principal": "BR-116 / BA-409",
        "lat": -11.6642,
        "lon": -39.0075,
    },
    {
        "cidade": "Juazeiro",
        "macrorregiao": "Norte",
        "territorio_identidade": "Sertão do São Francisco",
        "rodovia_principal": "BR-407 / BR-235",
        "lat": -9.4167,
        "lon": -40.5033,
    },
    {
        "cidade": "Barreiras",
        "macrorregiao": "Oeste",
        "territorio_identidade": "Bacia do Rio Grande",
        "rodovia_principal": "BR-242 / BR-135",
        "lat": -12.1439,
        "lon": -44.9969,
    },
    {
        "cidade": "Bom Jesus da Lapa",
        "macrorregiao": "Oeste / São Francisco",
        "territorio_identidade": "Velho Chico (Médio São Francisco)",
        "rodovia_principal": "BR-349 / BA-160",
        "lat": -13.2550,
        "lon": -43.4181,
    },
    {
        "cidade": "Seabra",
        "macrorregiao": "Centro-Sul",
        "territorio_identidade": "Chapada Diamantina",
        "rodovia_principal": "BR-242",
        "lat": -12.4186,
        "lon": -41.7719,
    },
    {
        "cidade": "Vitória da Conquista",
        "macrorregiao": "Sudoeste",
        "territorio_identidade": "Sudoeste Baiano",
        "rodovia_principal": "BR-116 / BA-262",
        "lat": -14.8619,
        "lon": -40.8442,
    },
    {
        "cidade": "Valença",
        "macrorregiao": "Baixo Sul",
        "territorio_identidade": "Costa do Dendê",
        "rodovia_principal": "BA-001 / BR-101",
        "lat": -13.3703,
        "lon": -39.0731,
    },
    {
        "cidade": "Ilhéus",
        "macrorregiao": "Sul",
        "territorio_identidade": "Litoral Sul (Costa do Cacau)",
        "rodovia_principal": "BR-415 / BA-001",
        "lat": -14.7935,
        "lon": -39.0464,
    },
    {
        "cidade": "Porto Seguro",
        "macrorregiao": "Extremo Sul",
        "territorio_identidade": "Costa do Descobrimento",
        "rodovia_principal": "BR-367 / BR-101",
        "lat": -16.4435,
        "lon": -39.0643,
    },
    {
        "cidade": "Teixeira de Freitas",
        "macrorregiao": "Extremo Sul",
        "territorio_identidade": "Extremo Sul",
        "rodovia_principal": "BR-101 / BA-290",
        "lat": -17.5399,
        "lon": -39.7419,
    },
    # --- 12 CIDADES DO ENTORNO E EIXOS COMPLEMENTARES ---
    {
        "cidade": "Camaçari",
        "macrorregiao": "Leste / RMS",
        "territorio_identidade": "Metropolitano de Salvador",
        "rodovia_principal": "BA-093 / BA-099",
        "lat": -12.6996,
        "lon": -38.3263,
    },
    {
        "cidade": "Alagoinhas",
        "macrorregiao": "Nordeste",
        "territorio_identidade": "Litoral Norte e Agreste Baiano",
        "rodovia_principal": "BR-101 / BR-110",
        "lat": -12.1336,
        "lon": -38.4192,
    },
    {
        "cidade": "Santo Antônio de Jesus",
        "macrorregiao": "Recôncavo",
        "territorio_identidade": "Recôncavo",
        "rodovia_principal": "BR-101 / BA-046",
        "lat": -12.9689,
        "lon": -39.2614,
    },
    {
        "cidade": "Jequié",
        "macrorregiao": "Centro-Sul",
        "territorio_identidade": "Médio Rio de Contas",
        "rodovia_principal": "BR-116 / BR-330",
        "lat": -13.8578,
        "lon": -40.0836,
    },
    {
        "cidade": "Itabuna",
        "macrorregiao": "Sul",
        "territorio_identidade": "Litoral Sul (Costa do Cacau)",
        "rodovia_principal": "BR-101 / BR-415",
        "lat": -14.7876,
        "lon": -39.2781,
    },
    {
        "cidade": "Eunápolis",
        "macrorregiao": "Extremo Sul",
        "territorio_identidade": "Costa do Descobrimento",
        "rodovia_principal": "BR-101 / BR-367",
        "lat": -16.3716,
        "lon": -39.5821,
    },
    {
        "cidade": "Luís Eduardo Magalhães",
        "macrorregiao": "Oeste",
        "territorio_identidade": "Bacia do Rio Grande",
        "rodovia_principal": "BR-242 / BR-020",
        "lat": -12.0967,
        "lon": -45.7867,
    },
    {
        "cidade": "Guanambi",
        "macrorregiao": "Centro-Sul",
        "territorio_identidade": "Sertão Produtivo",
        "rodovia_principal": "BR-030 / BR-122",
        "lat": -14.2233,
        "lon": -42.7814,
    },
    {
        "cidade": "Jacobina",
        "macrorregiao": "Centro-Norte",
        "territorio_identidade": "Piemonte da Diamantina",
        "rodovia_principal": "BR-324",
        "lat": -11.1806,
        "lon": -40.5183,
    },
    {
        "cidade": "Senhor do Bonfim",
        "macrorregiao": "Norte",
        "territorio_identidade": "Piemonte Norte do Itapicuru",
        "rodovia_principal": "BR-407",
        "lat": -10.4614,
        "lon": -40.1894,
    },
    {
        "cidade": "Irecê",
        "macrorregiao": "Centro-Norte",
        "territorio_identidade": "Irecê",
        "rodovia_principal": "BA-052",
        "lat": -11.3042,
        "lon": -41.8558,
    },
    {
        "cidade": "Paulo Afonso",
        "macrorregiao": "Nordeste",
        "territorio_identidade": "Itaparica",
        "rodovia_principal": "BR-110 / BA-210",
        "lat": -9.4061,
        "lon": -38.2219,
    },
]


def agora_bahia() -> datetime:
    return datetime.now(FUSO_BAHIA)


def buscar_temperaturas_bahia() -> list:
    """Consulta temperatura atual, chuva e vento real das 24 cidades em uma única chamada rápida via Open-Meteo."""
    lats = ",".join(str(c["lat"]) for c in CIDADES_MONITORADAS)
    lons = ",".join(str(c["lon"]) for c in CIDADES_MONITORADAS)
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lats}&longitude={lons}&current=temperature_2m,precipitation,wind_speed_10m"
    )
    dados_clima = []
    try:
        respostas = requests.get(url, timeout=15).json()
        if not isinstance(respostas, list):
            respostas = [respostas]

        for item, resp in zip(CIDADES_MONITORADAS, respostas):
            atual = resp.get("current", {})
            dados_clima.append({
                "cidade": item["cidade"],
                "macrorregiao": item["macrorregiao"],
                "territorio_identidade": item["territorio_identidade"],
                "rodovia_principal": item["rodovia_principal"],
                "latitude": item["lat"],
                "longitude": item["lon"],
                "temperatura_c": atual.get("temperature_2m", 28.0),
                "chuva_mm": atual.get("precipitation", 0.0),
                "vento_kmh": atual.get("wind_speed_10m", 10.0),
            })
    except Exception:
        for item in CIDADES_MONITORADAS:
            dados_clima.append({
                "cidade": item["cidade"],
                "macrorregiao": item["macrorregiao"],
                "territorio_identidade": item["territorio_identidade"],
                "rodovia_principal": item["rodovia_principal"],
                "latitude": item["lat"],
                "longitude": item["lon"],
                "temperatura_c": 28.0,
                "chuva_mm": 0.0,
                "vento_kmh": 10.0,
            })
    return dados_clima


def buscar_noticias_bahia() -> str:
    """Coleta manchetes recentes do Google News RSS sobre rodovias e clima na Bahia."""
    consultas = [
        "rodovias Bahia Seinfra interdição chuva obras",
        "PRF Bahia BR-324 BR-116 BR-101 BR-242 BR-407 trânsito",
        "Inema previsão do tempo alerta chuva Bahia Ilhéus Porto Seguro Juazeiro Barreiras",
    ]
    manchetes = []
    for termo in consultas:
        query = urllib.parse.quote(termo)
        url = f"https://news.google.com/rss/search?q={query}+when:2d&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "xml")
            for item in soup.find_all("item")[:6]:
                titulo = item.title.text if item.title else ""
                pub_date = item.pubDate.text if item.pubDate else ""
                manchetes.append(f"- [{pub_date}] {titulo}")
        except Exception:
            pass
    return "\n".join(manchetes) if manchetes else "Sem manchetes críticas indexadas nas últimas 48h."


def gerar_json_powerbi(clima_cidades: list, noticias_brutas: str) -> dict:
    """Consolida temperatura + territórios de identidade + ocorrências rodoviárias em JSON."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    data_hora = agora_bahia().strftime("%d/%m/%Y %H:%M")

    prompt = f"""
    Data/Hora (Bahia): {data_hora}
    DADOS TÉRMICOS E TERRITORIAIS ATUAIS (24 CIDADES): {json.dumps(clima_cidades, ensure_ascii=False)}
    MANCHETES RECENTES: {noticias_brutas}

    Atue como um Analista de Inteligência Logística. Gere um JSON estritamente válido (sem markdown ```json) com duas tabelas planas prontas para o Power BI:

    {{
      "data_atualizacao": "{data_hora}",
      "cidades_mapa_calor": [
        {{
          "cidade": "Nome da Cidade",
          "macrorregiao": "Macrorregião",
          "territorio_identidade": "Território de Identidade da Bahia",
          "latitude": -12.9714,
          "longitude": -38.5014,
          "temperatura_c": 29.5,
          "chuva_mm": 0.0,
          "vento_kmh": 12.0,
          "nivel_risco": "Normal | Atenção | Crítico",
          "rodovia_eixo": "BR-324 / BA-099",
          "resumo_cartao_cidade": "Situação resumida desta cidade e território (clima + tráfego local) para os cartões do Power BI"
        }}
      ],
      "detalhamento_rodovias": [
        {{
          "rodovia": "BR-324",
          "territorio_identidade": "Portal do Sertão",
          "trecho_cidade": "Salvador - Feira de Santana",
          "categoria": "Bloqueio | Obra | Erosão | Passagem Molhada | Tráfego Intenso | Fiscalização | Clima",
          "severidade": "Alta | Média | Baixa",
          "situacao_detalhada": "Descrição clara e estruturada do que está acontecendo neste trecho",
          "diretriz_motorista": "Ação recomendada para a frota"
        }}
      ]
    }}

    Regras:
    1. Em "cidades_mapa_calor", inclua TODAS as 24 cidades fornecidas mantendo exatamente macrorregiao, territorio_identidade, latitudes, longitudes, temperaturas, chuva e vento.
    2. Em "detalhamento_rodovias", liste de 12 a 16 registros cobrindo as principais rodovias (BR-324, BR-116, BR-101, BR-242, BR-407, BR-367, BR-349, BR-030, BR-110, BA-001, BA-052, BA-093, BA-099) e preenchendo obrigatoriamente o campo "territorio_identidade" correspondente a cada trecho.
    """

    modelos = ["gemini-flash-latest", "gemini-pro-latest", "gemma-3-27b-it"]
    try:
        lista = [
            m.name.replace("models/", "") for m in client.models.list()
            if ("gemini" in m.name or "gemma" in m.name) and "embedding" not in m.name and "vision" not in m.name
        ]
        if lista:
            lista.sort(key=lambda x: (0 if "flash" in x else (1 if "gemma" in x else 2)))
            modelos = lista
    except Exception:
        pass

    for modelo in modelos:
        try:
            response = client.models.generate_content(
                model=modelo,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2),
            )
            texto_limpo = response.text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(texto_limpo)
        except Exception:
            time.sleep(2)

    raise RuntimeError("Nenhum modelo disponível respondeu para gerar o JSON.")


def salvar_arquivos_json(payload_completo: dict):
    """Salva o JSON apenas na pasta do projeto (01_Projetos/monitor-rodovias-ba)."""
    arquivo_repo = pasta_script / "dados_powerbi_atual.json"
    with open(arquivo_repo, "w", encoding="utf-8") as f:
        json.dump(payload_completo, f, ensure_ascii=False, indent=2)

    print(f"JSON com 24 cidades atualizado com sucesso às {payload_completo.get('data_atualizacao')}.")


if __name__ == "__main__":
    clima_atual = buscar_temperaturas_bahia()
    noticias = buscar_noticias_bahia()
    dados_finais = gerar_json_powerbi(clima_atual, noticias)
    salvar_arquivos_json(dados_finais)