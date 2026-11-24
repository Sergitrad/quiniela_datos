
import json
import urllib.request
from datetime import datetime

# Endpoint oficial público de SELAE para próximos sorteos de La Quiniela (LAQU)
URL_SELAE = "https://loteriasyapuestas.es"


def obtener_boleto_oficial():
    req = urllib.request.Request(
        URL_SELAE,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-ES,es;q=0.9",
            "Referer": "https://loteriasyapuestas.es"
        }
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        datos = json.loads(resp.read().decode("utf-8"))

    # Buscamos el sorteo activo que ya tenga los partidos publicados
    sorteo = None
    for s in datos:
        if s.get("partidos") and len(s["partidos"]) >= 15:
            sorteo = s
            break
    if not sorteo:
        sorteo = datos[0]

    jornada = sorteo.get("jornada", "Activa")
    fecha_raw = sorteo.get("fecha_cierre", sorteo.get("fecha", ""))
    fecha_cierre = fecha_raw[:16].replace("T", " ") if fecha_raw else "Consultar boleto"
    lista_partidos = sorteo.get("partidos", [])

    partidos_json = []
    partido_15_json = {}

    for idx, p in enumerate(lista_partidos, start=1):
        local = p.get("local", f"Local {idx}").strip()
        visitante = p.get("visitante", f"Visitante {idx}").strip()

        # Ponderación inicial (ligera ventaja local + equilibrio competitivo)
        prob1, probx, prob2 = 0.45, 0.28, 0.27

        item = {
            "numero": idx,
            "local": local,
            "visitante": visitante,
            "prob1": prob1,
            "probX": probx,
            "prob2": prob2,
            "posLocal": 0,
            "posVisitante": 0,
            "rachaLocal": "Jornada oficial SELAE",
            "rachaVisitante": "Boleto activo",
            "h2h": f"Partido oficial #{idx} · Jornada {jornada}"
        }

        if idx <= 14:
            partidos_json.append(item)
        elif idx == 15:
            partido_15_json = item

    salida = {
        "titulo_jornada": f"Jornada {jornada} · Oficial SELAE",
        "fecha_cierre": fecha_cierre,
        "actualizado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "partidos": partidos_json,
        "partido_15": partido_15_json
    }

    with open("jornada_actual.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    obtener_boleto_oficial()
