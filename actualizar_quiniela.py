
import json
import re
import socket
import urllib.request
from datetime import datetime

socket.setdefaulttimeout(20)

URL_PROXY = "https://jina.ai"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/plain, */*"
}


def descargar_texto():
    req = urllib.request.Request(URL_PROXY, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extraer_ternas(bloque):
    nums = [int(x) for x in re.findall(r"\b(\d{1,2})\b", bloque)]
    ternas = []
    i = 0
    while i <= len(nums) - 3:
        a, b, c = nums[i], nums[i + 1], nums[i + 2]
        if 97 <= (a + b + c) <= 103:
            ternas.append((a, b, c))
            i += 3
        else:
            i += 1
    return ternas


def obtener_boleto_oficial():
    texto = descargar_texto()

    m_jor = re.search(r"JORNADA\s+(\d+)", texto, re.IGNORECASE)
    jornada = m_jor.group(1) if m_jor else "Activa"

    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    partidos = {}

    for idx, l in enumerate(lineas):
        # Buscar líneas tipo "1 BETIS - RAYO" o "1 | BETIS - RAYO"
        m = re.match(r"^(\d{1,2})\s*[|\-]?\s*([A-ZÁÉÍÓÚÑ0-9 .'-]{2,}?)\s+-\s+([A-ZÁÉÍÓÚÑ0-9 .'-]{2,})$", l)
        if m:
            num = int(m.group(1))
            if 1 <= num <= 14 and num not in partidos:
                loc = m.group(2).strip()
                vis = m.group(3).strip()
                contexto = " ".join(lineas[idx + 1:idx + 10])
                ternas = extraer_ternas(contexto)
                t = ternas[-1] if ternas else (40, 30, 30)
                p1 = round(t[0] / 100.0, 2)
                px = round(t[1] / 100.0, 2)
                p2 = round(max(0.01, 1.0 - p1 - px), 2)
                partidos[num] = {
                    "numero": num,
                    "local": loc,
                    "visitante": vis,
                    "prob1": p1,
                    "probX": px,
                    "prob2": p2,
                    "posLocal": 0,
                    "posVisitante": 0,
                    "rachaLocal": f"1: {t[0]}%",
                    "rachaVisitante": f"2: {t[2]}%",
                    "h2h": f"Jornada {jornada} · Partido #{num}"
                }

    # Si no se pudieron extraer los 14, guardar diagnóstico visible para no fallar a ciegas
    if len(partidos) < 14:
        raise RuntimeError(f"Detectados {len(partidos)} partidos. Muestra: {' | '.join(lineas[:15])}")

    # Buscar partido 15
    p15 = {
        "numero": 15,
        "local": "Pleno Local",
        "visitante": "Pleno Visitante",
        "prob1": 0.40,
        "probX": 0.30,
        "prob2": 0.30,
        "posLocal": 0,
        "posVisitante": 0,
        "rachaLocal": "-",
        "rachaVisitante": "-",
        "h2h": f"Jornada {jornada} · Pleno al 15"
    }
    for idx, l in enumerate(lineas):
        m15 = re.match(r"^15\s*[|\-]?\s*([A-ZÁÉÍÓÚÑ0-9 .'-]{2,})$", l)
        if m15 and idx + 1 < len(lineas):
            p15["local"] = m15.group(1).strip()
            p15["visitante"] = lineas[idx + 1].strip()
            break

    salida = {
        "titulo_jornada": f"Jornada {jornada} · La Quiniela",
        "fecha_cierre": "Consultar boleto oficial",
        "actualizado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "partidos": [partidos[n] for n in range(1, 15)],
        "partido_15": p15
    }

    with open("jornada_actual.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    obtener_boleto_oficial()
