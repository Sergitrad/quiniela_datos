import json
import re
import urllib.parse
import urllib.request
from datetime import datetime

DOMINIO_SELAE = "www." + "loteriasyapuestas" + ".es"
RUTA_SELAE = "/servicios/proximosv3?game_id=LAQU&num=2"
URL_SELAE = "https://" + DOMINIO_SELAE + RUTA_SELAE
URL_PUENTE = "https://allorigins.win" + urllib.parse.quote(URL_SELAE, safe="")
URL_RESPALDO = "https://www." + "eduardolosilla" + ".es/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "es-ES,es;q=0.9"
}


def descargar(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def construir_salida(jornada, fecha_cierre, parejas):
    partidos_json = []
    partido_15_json = {}

    for idx, (local, visitante) in enumerate(parejas[:15], start=1):
        item = {
            "numero": idx,
            "local": local.strip(),
            "visitante": visitante.strip(),
            "prob1": 0.45,
            "probX": 0.28,
            "prob2": 0.27,
            "posLocal": 0,
            "posVisitante": 0,
            "rachaLocal": "Jornada oficial",
            "rachaVisitante": "Boleto activo",
            "h2h": f"Partido #{idx} · Jornada {jornada}"
        }
        if idx <= 14:
            partidos_json.append(item)
        elif idx == 15:
            partido_15_json = item

    return {
        "titulo_jornada": f"Jornada {jornada} · La Quiniela",
        "fecha_cierre": fecha_cierre,
        "actualizado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "partidos": partidos_json,
        "partido_15": partido_15_json
    }


def desde_selae():
    for url in (URL_PUENTE, URL_SELAE):
        try:
            texto = descargar(url)
            datos = json.loads(texto)
            sorteo = next((s for s in datos if s.get("partidos") and len(s["partidos"]) >= 15), datos)
            jornada = sorteo.get("jornada", "Activa")
            fecha_raw = sorteo.get("fecha_cierre", sorteo.get("fecha", ""))
            fecha_cierre = fecha_raw[:16].replace("T", " ") if fecha_raw else "Consultar boleto"
            parejas = [(p.get("local", ""), p.get("visitante", "")) for p in sorteo.get("partidos", [])]
            if len(parejas) >= 15:
                return construir_salida(jornada, fecha_cierre, parejas)
        except Exception:
            continue
    return None


def desde_respaldo():
    html = descargar(URL_RESPALDO)
    limpio = re.sub(r"<[^>]+>", " ", html)
    limpio = re.sub(r"\s+", " ", limpio)
    m_jor = re.search(r"JORNADA\s+(\d+)", limpio, re.IGNORECASE)
    jornada = m_jor.group(1) if m_jor else "Activa"
    parejas = re.findall(r"\b(?:[1-9]|1[0-5])\s+([A-ZÁÉÍÓÚÑ0-9.\- ]{2,25}?)\s+-\s+([A-ZÁÉÍÓÚÑ0-9.\- ]{2,25}?)(?=\s+(?:LUN|MAR|MIÉ|MIE|JUE|VIE|SÁB|SAB|DOM|\d))", limpio)
    if len(parejas) >= 15:
        return construir_salida(jornada, "Consultar horario", parejas[:15])
    raise RuntimeError("No se pudieron extraer los 15 partidos de ninguna fuente.")


def obtener_boleto_oficial():
    salida = desde_selae() or desde_respaldo()
    with open("jornada_actual.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    obtener_boleto_oficial()

