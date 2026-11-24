
import json
import re
import socket
import urllib.request
from datetime import datetime

socket.setdefaulttimeout(10)

HOST = "site.api." + "espn" + ".com"
RUTA_1 = "/apis/site/v2/sports/soccer/esp.1/scoreboard"
RUTA_2 = "/apis/site/v2/sports/soccer/esp.2/scoreboard"

URL_PRIMERA = "https://" + HOST + RUTA_1
URL_SEGUNDA = "https://" + HOST + RUTA_2


def leer_espn(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        datos = json.loads(resp.read().decode("utf-8"))
    return datos.get("events") or []


def parsear_balance(resumen):
    # ESPN suele devolver "V-E-D" (ej. "10-4-2") o "V-D"
    nums = [int(x) for x in re.findall(r"\d+", str(resumen))]
    if len(nums) >= 3:
        v, e, d = nums, nums, nums
    elif len(nums) == 2:
        v, e, d = nums, 0, nums
    else:
        return 0.45, 0.28, 0.27

    total = v + e + d
    if total == 0:
        return 0.45, 0.28, 0.27

    # Puntos por partido (0 a 3) como medida de fuerza
    ppg = (v * 3 + e) / total
    tasa_empate = e / total
    return ppg, tasa_empate, total


def calcular_probabilidades(res_local, res_visitante):
    ppg_l, emp_l, tot_l = parsear_balance(res_local)
    ppg_v, emp_v, tot_v = parsear_balance(res_visitante)

    # Si aún no hay datos suficientes de temporada, usamos base equilibrada
    if tot_l == 0 or tot_v == 0 or isinstance(ppg_l, float) and ppg_l < 1.0 and tot_l < 1:
        return 0.45, 0.28, 0.27

    # Fuerza competitiva (evitamos ceros con base +0.35) + factor campo local (+0.35)
    fuerza_l = ppg_l + 0.70
    fuerza_v = ppg_v + 0.35

    diferencia = abs(fuerza_l - fuerza_v) / (fuerza_l + fuerza_v)

    # Probabilidad de empate: sube si ambos empatan mucho y si están igualados
    media_empate = (emp_l + emp_v) / 2.0
    prob_x = 0.24 + (media_empate * 0.25) - (diferencia * 0.22)
    prob_x = max(0.14, min(0.36, prob_x))

    # Repartimos el resto entre 1 y 2 según fuerza relativa
    restante = 1.0 - prob_x
    ratio_l = fuerza_l / (fuerza_l + fuerza_v)
    prob_1 = restante * ratio_l
    prob_2 = restante * (1.0 - ratio_l)

    # Evitamos porcentajes extremos irreales (mínimo 6%)
    prob_1 = max(0.06, prob_1)
    prob_2 = max(0.06, prob_2)

    # Normalizamos a 2 decimales sumando exactamente 1.00
    suma = prob_1 + prob_x + prob_2
    p1 = round(prob_1 / suma, 2)
    px = round(prob_x / suma, 2)
    p2 = round(1.00 - p1 - px, 2)

    return p1, px, p2


def obtener_boleto_oficial():
    primera = leer_espn(URL_PRIMERA)
    segunda = leer_espn(URL_SEGUNDA)

    seleccion = primera[:10] + segunda[:5]
    if len(seleccion) < 15:
        seleccion = (primera + segunda)[:15]

    jornada = "Activa"
    fecha_cierre = "Consultar horario"
    primer_evento = next(iter(primera), None)
    if primer_evento:
        season = primer_evento.get("season", {})
        if season.get("year"):
            jornada = str(season.get("year"))
        fecha_raw = primer_evento.get("date", "")
        if fecha_raw:
            fecha_cierre = fecha_raw[:16].replace("T", " ")

    partidos_json = []
    partido_15_json = {}

    for idx, ev in enumerate(seleccion[:15], start=1):
        comp = next(iter(ev.get("competitions") or []), {})
        equipos = comp.get("competitors") or []

        local = f"Local {idx}"
        visitante = f"Visitante {idx}"
        resumen_local = ""
        resumen_visitante = ""
        racha_local = "En forma"
        racha_visitante = "En forma"

        for eq in equipos:
            nombre = eq.get("team", {}).get("shortDisplayName") or eq.get("team", {}).get("displayName", "")
            rec = next(iter(eq.get("records") or []), {})
            resumen = rec.get("summary", "")
            if eq.get("homeAway") == "home":
                local = nombre
                resumen_local = resumen
                racha_local = f"Balance: {resumen}" if resumen else "Temporada actual"
            elif eq.get("homeAway") == "away":
                visitante = nombre
                resumen_visitante = resumen
                racha_visitante = f"Balance: {resumen}" if resumen else "Temporada actual"

        prob1, probx, prob2 = calcular_probabilidades(resumen_local, resumen_visitante)
        liga = "1ª Div" if ev in primera else "2ª Div"

        item = {
            "numero": idx,
            "local": local,
            "visitante": visitante,
            "prob1": prob1,
            "probX": probx,
            "prob2": prob2,
            "posLocal": 0,
            "posVisitante": 0,
            "rachaLocal": racha_local,
            "rachaVisitante": racha_visitante,
            "h2h": f"Partido #{idx} · {liga}"
        }

        if idx <= 14:
            partidos_json.append(item)
        elif idx == 15:
            partido_15_json = item

    while len(partidos_json) < 14:
        n = len(partidos_json) + 1
        partidos_json.append({
            "numero": n,
            "local": f"Por definir {n}A",
            "visitante": f"Por definir {n}B",
            "prob1": 0.34,
            "probX": 0.33,
            "prob2": 0.33,
            "posLocal": 10,
            "posVisitante": 10,
            "rachaLocal": "-",
            "rachaVisitante": "-",
            "h2h": "Pendiente de jornada"
        })

    if not partido_15_json:
        partido_15_json = {
            "numero": 15,
            "local": "Por definir 15A",
            "visitante": "Por definir 15B",
            "prob1": 0.34,
            "probX": 0.33,
            "prob2": 0.33,
            "posLocal": 10,
            "posVisitante": 10,
            "rachaLocal": "-",
            "rachaVisitante": "-",
            "h2h": "Pleno al 15"
        }

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
