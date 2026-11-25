
import html as html_lib
import json
import re
import socket
import urllib.request
from datetime import datetime

socket.setdefaulttimeout(15)

URL_QUINIELA = "https://eduardolosilla.es"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9"
}


def descargar_lineas():
    req = urllib.request.Request(URL_QUINIELA, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    # Eliminar scripts y estilos antes de extraer texto por bloques
    sin_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", "\n", raw, flags=re.DOTALL | re.IGNORECASE)
    con_saltos = re.sub(r"<[^>]+>", "\n", sin_scripts)
    texto = html_lib.unescape(con_saltos)

    lineas = []
    for l in texto.splitlines():
        limpia = re.sub(r"\s+", " ", l).strip()
        if limpia:
            lineas.append(limpia)
    return lineas


def extraer_ternas_porcentajes(ventana):
    """Busca grupos de 3 porcentajes válidos (que sumen ~100) en las líneas siguientes al partido."""
    nums = []
    for item in ventana:
        if re.match(r"^\d{1,2}$", item):
            nums.append(int(item))
        elif item == "-":
            nums.append(None)

    ternas = []
    i = 0
    while i <= len(nums) - 3:
        a, b, c = nums[i], nums[i + 1], nums[i + 2]
        if a is not None and b is not None and c is not None and 97 <= (a + b + c) <= 103:
            ternas.append((a, b, c))
            i += 3
        else:
            i += 1
    return ternas


def calcular_1x2_desde_goles(valores_8):
    """Convierte las 8 probabilidades de goles (0,1,2,M local y 0,1,2,M visitante) en 1, X, 2."""
    g_loc = [v / 100.0 for v in valores_8[:4]]
    g_vis = [v / 100.0 for v in valores_8[4:8]]
    p1 = px = p2 = 0.0
    for i in range(4):
        for j in range(4):
            prob = g_loc[i] * g_vis[j]
            if i > j:
                p1 += prob
            elif i == j:
                px += prob
            else:
                p2 += prob
    suma = (p1 + px + p2) or 1.0
    r1 = round(p1 / suma, 2)
    rx = round(px / suma, 2)
    r2 = round(max(0.01, 1.0 - r1 - rx), 2)
    return r1, rx, r2


def obtener_boleto_oficial():
    lineas = descargar_lineas()

    jornada = "Activa"
    fecha_cierre = "Consultar horario oficial"

    for idx, l in enumerate(lineas):
        m_jor = re.search(r"JORNADA\s+(\d+)", l, re.IGNORECASE)
        if m_jor and jornada == "Activa":
            jornada = m_jor.group(1)

        if l.upper().startswith("CIERRE"):
            parte_hora = lineas[idx + 2] if idx + 2 < len(lineas) else ""
            fecha_cierre = f"{l} ({parte_hora})".strip()

    partidos_detectados = {}
    i = 0
    while i < len(lineas):
        l = lineas[i]

        # Caso A: "1 BETIS - RAYO" en la misma línea
        m_inline = re.match(r"^(\d{1,2})\s+([A-ZÁÉÍÓÚÑ0-9 .'-]+?)\s+-\s+([A-ZÁÉÍÓÚÑ0-9 .'-]+)$", l)
        # Caso B: "1" en una línea y "BETIS - RAYO" en la siguiente
        m_num = re.match(r"^(\d{1,2})$", l)

        num = None
        local = ""
        visitante = ""
        salto = i + 1

        if m_inline:
            num = int(m_inline.group(1))
            local = m_inline.group(2).strip()
            visitante = m_inline.group(3).strip()
            salto = i + 1
        elif m_num and i + 1 < len(lineas):
            cand_num = int(m_num.group(1))
            m_vs = re.match(r"^([A-ZÁÉÍÓÚÑ0-9 .'-]+?)\s+-\s+([A-ZÁÉÍÓÚÑ0-9 .'-]+)$", lineas[i + 1])
            if 1 <= cand_num <= 14 and m_vs:
                num = cand_num
                local = m_vs.group(1).strip()
                visitante = m_vs.group(2).strip()
                salto = i + 2

        if num is not None and 1 <= num <= 14 and num not in partidos_detectados:
            ventana = lineas[salto:salto + 22]
            ternas = extraer_ternas_porcentajes(ventana)

            # Primera terna: % Jugados | Segunda terna (si existe): % Probables reales
            jugados = ternas[0] if len(ternas) >= 1 else (40, 30, 30)
            probables = ternas[1] if len(ternas) >= 2 else jugados

            p1 = round(probables[0] / 100.0, 2)
            px = round(probables[1] / 100.0, 2)
            p2 = round(max(0.01, 1.0 - p1 - px), 2)

            partidos_detectados[num] = {
                "numero": num,
                "local": local,
                "visitante": visitante,
                "prob1": p1,
                "probX": px,
                "prob2": p2,
                "posLocal": 0,
                "posVisitante": 0,
                "rachaLocal": f"Jugado: {jugados[0]}% | Prob: {probables[0]}%",
                "rachaVisitante": f"Jugado: {jugados[2]}% | Prob: {probables[2]}%",
                "h2h": f"Jornada {jornada} · Partido #{num}"
            }

        # Partido 15 (Pleno al 15: los equipos van en dos líneas consecutivas)
        if 15 not in partidos_detectados:
            m_15_inline = re.match(r"^15\s+([A-ZÁÉÍÓÚÑ0-9 .'-]{2,})$", l)
            if m_15_inline and i + 1 < len(lineas) and len(partidos_detectados) >= 14:
                loc_15 = m_15_inline.group(1).strip()
                vis_15 = lineas[i + 1].strip()
                if not re.match(r"^(LUN|MAR|MIE|JUE|VIE|SAB|DOM|\d)", vis_15):
                    ventana_15 = lineas[i + 2:i + 35]
                    vals = [int(x) for x in ventana_15 if re.match(r"^\d{1,2}$", x)]
                    if len(vals) >= 16:
                        p1, px, p2 = calcular_1x2_desde_goles(vals[8:16])
                        jug_15 = vals[:8]
                    elif len(vals) >= 8:
                        p1, px, p2 = calcular_1x2_desde_goles(vals[:8])
                        jug_15 = vals[:8]
                    else:
                        p1, px, p2 = 0.40, 0.30, 0.30
                        jug_15 = [25] * 8

                    partidos_detectados[15] = {
                        "numero": 15,
                        "local": loc_15,
                        "visitante": vis_15,
                        "prob1": p1,
                        "probX": px,
                        "prob2": p2,
                        "posLocal": 0,
                        "posVisitante": 0,
                        "rachaLocal": f"Goles 0-1-2-M: {jug_15[0]}-{jug_15[1]}-{jug_15[2]}-{jug_15[3]}%",
                        "rachaVisitante": f"Goles 0-1-2-M: {jug_15[4]}-{jug_15[5]}-{jug_15[6]}-{jug_15[7]}%",
                        "h2h": f"Jornada {jornada} · Pleno al 15"
                    }

        i += 1

    if len(partidos_detectados) < 15:
        raise RuntimeError(f"Solo se detectaron {len(partidos_detectados)} partidos de 15")

    partidos_json = [partidos_detectados[n] for n in range(1, 15)]
    partido_15_json = partidos_detectados[15]

    salida = {
        "titulo_jornada": f"Jornada {jornada} · La Quiniela",
        "fecha_cierre": fecha_cierre,
        "actualizado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "partidos": partidos_json,
        "partido_15": partido_15_json
    }

    with open("jornada_actual.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    obtener_boleto_oficial()
