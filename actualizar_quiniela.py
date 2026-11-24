import json
import urllib.request
from datetime import datetime

HOST = "www." + "thesportsdb" + ".com"
BASE = "/api/v1/json/3/eventsnextleague.php?id="
URL_PRIMERA = "https://" + HOST + BASE + "4335"
URL_SEGUNDA = "https://" + HOST + BASE + "4400"


def leer_liga(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        datos = json.loads(resp.read().decode("utf-8"))
    return datos.get("events") or []


def obtener_boleto_oficial():
    primera = leer_liga(URL_PRIMERA)
    segunda = leer_liga(URL_SEGUNDA)

    # Tomamos los próximos 10 partidos de Primera y 5 de Segunda (total 15)
    seleccion = primera[:10] + segunda[:5]
    if len(seleccion) < 15:
        seleccion = (primera + segunda)[:15]

    jornada = primera[0].get("intRound", "Activa") if primera else "Activa"
    fecha_raw = primera[0].get("strTimestamp", "") if primera else ""
    fecha_cierre = fecha_raw[:16].replace("T", " ") if fecha_raw else "Consultar horario"

    partidos_json = []
    partido_15_json = {}

    for idx, ev in enumerate(seleccion[:15], start=1):
        local = ev.get("strHomeTeam", f"Local {idx}").strip()
        visitante = ev.get("strAwayTeam", f"Visitante {idx}").strip()
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
            "rachaLocal": f"{liga} · Jornada {jornada}",
            "rachaVisitante": "Próximo partido",
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

