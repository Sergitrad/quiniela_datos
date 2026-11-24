import json
import socket
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

socket.setdefaulttimeout(10)

hoy = datetime.now()
fin = hoy + timedelta(days=14)
params = urllib.parse.urlencode({
    "dates": f"{hoy.strftime('%Y%m%d')}-{fin.strftime('%Y%m%d')}"
})

HOST = "site.api." + "espn" + ".com"
URL_PRIMERA = "https://" + HOST + "/apis/site/v2/sports/soccer/esp.1/scoreboard?" + params
URL_SEGUNDA = "https://" + HOST + "/apis/site/v2/sports/soccer/esp.2/scoreboard?" + params


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
        racha_local = "En forma"
        racha_visitante = "En forma"

        for eq in equipos:
            nombre = eq.get("team", {}).get("shortDisplayName") or eq.get("team", {}).get("displayName", "")
            rec = next(iter(eq.get("records") or []), {})
            resumen = rec.get("summary", "Temporada actual")
            if eq.get("homeAway") == "home":
                local = nombre
                racha_local = f"Balance: {resumen}"
            elif eq.get("homeAway") == "away":
                visitante = nombre
                racha_visitante = f"Balance: {resumen}"

        liga = "1ª Div" if ev in primera else "2ª Div"

        item = {
            "numero": idx,
            "local": local,
            "visitante": visitante,
            "prob1": 0.45,
            "probX": 0.28,
            "prob2": 0.27,
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
