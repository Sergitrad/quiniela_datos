import json
import re
import socket
import urllib.request
from datetime import datetime

socket.setdefaulttimeout(15)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9"
}


def descargar_texto(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def limpiar_html(texto):
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = texto.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#039;", "'").replace("&quot;", '"')
    return re.sub(r"\s+", " ", texto).strip()


def obtener_desde_losilla():
    url = "https://www.eduardolosilla.es/quiniela/boletos"
    html = descargar_texto(url)

    # Buscar número de jornada
    m_jor = re.search(r"Jornada\s+(\d+)", html, re.IGNORECASE)
    jornada = m_jor.group(1) if m_jor else "Activa"

    # Buscar fecha de cierre si aparece
    m_cierre = re.search(r"cierre[^<]{0,40}(\d{1,2}/\d{1,2}(?:/\d{2,4})?\s*\d{1,2}:\d{2})", html, re.IGNORECASE)
    fecha_cierre = m_cierre.group(1).strip() if m_cierre else "Consultar boleto oficial"

    partidos = []

    # Intentar extraer primero desde datos JSON embebidos en el HTML (SSR / Nuxt / Angular / State)
    bloques_json = re.findall(r'\{[^{}]*"local"[^{}]*"visitante"[^{}]*\}', html)
    if len(bloques_json) >= 15:
        for idx, b in enumerate(bloques_json[:15], start=1):
            try:
                obj = json.loads(b)
                local = str(obj.get("local") or obj.get("equipoLocal") or "").strip()
                visitante = str(obj.get("visitante") or obj.get("equipoVisitante") or "").strip()
                p1 = float(obj.get("porcentaje1") or obj.get("prob1") or 34)
                px = float(obj.get("porcentajeX") or obj.get("probX") or 33)
                p2 = float(obj.get("porcentaje2") or obj.get("prob2") or 33)
                if p1 > 1 or px > 1 or p2 > 1:
                    suma = (p1 + px + p2) or 100.0
                    p1, px, p2 = round(p1 / suma, 2), round(px / suma, 2), round(p2 / suma, 2)
                if local and visitante:
                    partidos.append((idx, local, visitante, p1, px, p2))
            except Exception:
                continue

    # Si no venían en JSON embebido, extraer filas de la tabla del boleto oficial
    if len(partidos) < 15:
        partidos = []
        filas = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
        for fila in filas:
            celdas = [limpiar_html(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", fila, re.DOTALL | re.IGNORECASE)]
            celdas = [c for c in celdas if c]
            if len(celdas) < 2:
                continue

            num_match = re.match(r"^(\d{1,2})$", celdas[0])
            if not num_match:
                continue
            num = int(num_match.group(1))
            if num < 1 or num > 15:
                continue

            # Buscar celda con el enfrentamiento "Equipo A - Equipo B"
            local, visitante = "", ""
            for c in celdas[1:4]:
                if " - " in c and len(c) >= 5:
                    partes = c.split(" - ", 1)
                    local, visitante = partes[0].strip(), partes[1].strip()
                    break

            if not local or not visitante:
                continue

            # Buscar porcentajes (3 números entre 1 y 99 en la fila)
            nums_fila = []
            for c in celdas[2:]:
                for m in re.findall(r"\b(\d{1,2}(?:[.,]\d+)?)\s*%?\b", c):
                    val = float(m.replace(",", "."))
                    if 1 <= val <= 98:
                        nums_fila.append(val)

            if len(nums_fila) >= 3:
                raw1, rawx, raw2 = nums_fila[-3], nums_fila[-2], nums_fila[-1]
                suma = (raw1 + rawx + raw2) or 100.0
                p1 = round(raw1 / suma, 2)
                px = round(rawx / suma, 2)
                p2 = round(max(0.01, 1.0 - p1 - px), 2)
            else:
                p1, px, p2 = 0.40, 0.30, 0.30

            partidos.append((num, local, visitante, p1, px, p2))

    # Ordenar por número de partido 1..15 y eliminar duplicados
    unicos = {}
    for item in partidos:
        if item[0] not in unicos:
            unicos[item[0]] = item

    lista_ordenada = [unicos[i] for i in sorted(unicos.keys()) if 1 <= i <= 15]
    if len(lista_ordenada) < 15:
        raise RuntimeError(f"Solo se detectaron {len(lista_ordenada)} partidos en Losilla")

    return jornada, fecha_cierre, lista_ordenada


def obtener_desde_selae():
    url = "https://loteriasyapuestas.es"
    raw = descargar_texto(url)
    data = json.loads(raw)

    sorteo = data[0] if isinstance(data, list) and data else data
    jornada = str(sorteo.get("jornada") or sorteo.get("numero_sorteo") or "Activa")
    fecha_cierre = str(sorteo.get("fecha_sorteo") or "Consultar boleto oficial")[:16].replace("T", " ")

    lista_partidos = sorteo.get("partidos") or []
    lista_ordenada = []
    for idx, p in enumerate(lista_partidos[:15], start=1):
        local = str(p.get("local") or "").strip()
        visitante = str(p.get("visitante") or "").strip()
        if local and visitante:
            lista_ordenada.append((idx, local, visitante, 0.40, 0.30, 0.30))

    if len(lista_ordenada) < 15:
        raise RuntimeError("SELAE no devolvió los 15 partidos completos")

    return jornada, fecha_cierre, lista_ordenada


def obtener_boleto_oficial():
    fuente = "Boleto Oficial"
    try:
        jornada, fecha_cierre, lista = obtener_desde_losilla()
        fuente = "Boleto Oficial · % Jugados"
    except Exception:
        jornada, fecha_cierre, lista = obtener_desde_selae()
        fuente = "Boleto Oficial SELAE"

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
            "h2h": f"Partido #{num} · {fuente}"
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
