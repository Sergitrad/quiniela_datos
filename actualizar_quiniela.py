import json
import re
import socket
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

socket.setdefaulttimeout(15)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/xml, application/xml, text/html;q=0.9, */*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9"
}


def descargar(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def leer_api_losilla():
    # Endpoint JSON público de jornadas activas
    urls = [
        "https://eduardolosilla.es",
        "https://eduardolosilla.es",
        "https://quinielista.es"
    ]
    ultimo_error = None
    for url in urls:
        try:
            contenido = descargar(url).strip()
            if contenido.startswith("{"):
                data = json.loads(contenido)
                partidos_raw = data.get("partidos") or data.get("encuentros") or []
                if len(partidos_raw) >= 15:
                    jornada = str(data.get("jornada") or data.get("numero") or "Activa")
                    cierre = str(data.get("fecha_cierre") or data.get("cierre") or "Consultar boleto")
                    lista = []
                    for idx, p in enumerate(partidos_raw[:15], start=1):
                        loc = str(p.get("local") or p.get("equipo_local") or "").strip()
                        vis = str(p.get("visitante") or p.get("equipo_visitante") or "").strip()
                        p1 = float(p.get("porcentaje_1") or p.get("prob1") or 40)
                        px = float(p.get("porcentaje_x") or p.get("probX") or 30)
                        p2 = float(p.get("porcentaje_2") or p.get("prob2") or 30)
                        if p1 > 1 or px > 1 or p2 > 1:
                            s = (p1 + px + p2) or 100.0
                            p1, px, p2 = round(p1 / s, 2), round(px / s, 2), round(max(0.01, 1.0 - round(p1 / s, 2) - round(px / s, 2)), 2)
                        lista.append((idx, loc, vis, p1, px, p2))
                    return jornada, cierre, lista

            elif contenido.startswith("<"):
                root = ET.fromstring(contenido)
                jornada = root.attrib.get("jornada") or root.findtext(".//jornada") or "Activa"
                cierre = root.attrib.get("cierre") or root.findtext(".//cierre") or "Consultar boleto"
                nodos = root.findall(".//partido")
                if len(nodos) >= 15:
                    lista = []
                    for idx, nodo in enumerate(nodos[:15], start=1):
                        loc = (nodo.attrib.get("local") or nodo.findtext("local") or "").strip()
                        vis = (nodo.attrib.get("visitante") or nodo.findtext("visitante") or "").strip()
                        p1 = float(nodo.attrib.get("p1") or nodo.findtext("p1") or 40)
                        px = float(nodo.attrib.get("px") or nodo.findtext("px") or 30)
                        p2 = float(nodo.attrib.get("p2") or nodo.findtext("p2") or 30)
                        if p1 > 1 or px > 1 or p2 > 1:
                            s = (p1 + px + p2) or 100.0
                            p1, px, p2 = round(p1 / s, 2), round(px / s, 2), round(max(0.01, 1.0 - round(p1 / s, 2) - round(px / s, 2)), 2)
                        lista.append((idx, loc, vis, p1, px, p2))
                    return jornada, cierre, lista
        except Exception as e:
            ultimo_error = f"{url} -> {e}"
    raise RuntimeError(f"Ninguna API respondió: {ultimo_error}")


def obtener_boleto_oficial():
    jornada, fecha_cierre, lista = leer_api_losilla()

    partidos_json = []
    partido_15_json = {}

    for num, local, visitante, p1, px, p2 in lista:
        item = {
            "numero": num,
            "local": local,
            "visitante": visitante,
            "prob1": p1,
            "probX": px,
            "prob2": p2,
            "posLocal": 0,
            "posVisitante": 0,
            "rachaLocal": f"1: {int(round(p1 * 100))}%",
            "rachaVisitante": f"2: {int(round(p2 * 100))}%",
            "h2h": f"Jornada {jornada} · Partido #{num}"
        }
        if num <= 14:
            partidos_json.append(item)
        elif num == 15:
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
