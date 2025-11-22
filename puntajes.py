import os
import json
import threading
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCORES_FILE = os.path.join(BASE_DIR, "scores.json")
_lock = threading.Lock()

# último resultado en memoria (no persistente) para que main.py lo pueda destacar
_ultimo_resultado = None  # dict: {"entry": {...}, "pos": int, "top5": [...], "mode": "cazador"/"escapa"}

def cargar_puntajes(modo=None):
    """Devuelve lista de registros guardados (lista de dicts).
    Si modo es 'cazador' o 'escapa', filtra por entry['mode']."""
    if not os.path.exists(SCORES_FILE):
        return []
    try:
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            if modo is None:
                return data
            modo_norm = str(modo).lower()
            return [e for e in data if str(e.get("mode", "")).lower() == modo_norm]
    except Exception:
        return []

def guardar_todos(lista_puntajes):
    """Sobrescribe el archivo de puntajes con la lista proporcionada."""
    try:
        with _lock:
            with open(SCORES_FILE, "w", encoding="utf-8") as f:
                json.dump(lista_puntajes, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def guardar_puntaje(nombre, puntaje, modo=None):
    """Añade un nuevo registro {name, score, mode, ts} al archivo (apéndice)."""
    try:
        entrada = {
            "name": str(nombre) if nombre is not None else "",
            "score": int(puntaje),
            "mode": str(modo) if modo is not None else "",
            "ts": datetime.utcnow().isoformat()
        }
    except Exception:
        return False

    try:
        with _lock:
            puntajes = cargar_puntajes()
            puntajes.append(entrada)
            with open(SCORES_FILE, "w", encoding="utf-8") as f:
                json.dump(puntajes, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def evaluar_y_guardar_puntaje(nombre, puntaje, modo=None):
    """Guarda el puntaje y devuelve (posición, top5)."""
    global _ultimo_resultado
    try:
        entrada = {
            "name": str(nombre) if nombre is not None else "",
            "score": int(puntaje),
            "mode": str(modo) if modo is not None else "",
            "ts": datetime.utcnow().isoformat()
        }
    except Exception:
        return None, []

    with _lock:
        todos = cargar_puntajes()
        todos.append(entrada)
        try:
            with open(SCORES_FILE, "w", encoding="utf-8") as f:
                json.dump(todos, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        modo_norm = str(modo).lower() if modo is not None else None
        filtrados = [e for e in todos if str(e.get("mode", "")).lower() == modo_norm] if modo_norm else todos[:]

        try:
            ordenados = sorted(filtrados, key=lambda e: (-int(e.get("score", 0)), e.get("ts", "")))
        except Exception:
            ordenados = filtrados[:]

        pos = None
        for idx, e in enumerate(ordenados, start=1):
            if e.get("ts") == entrada["ts"] and e.get("name") == entrada["name"] and int(e.get("score", 0)) == entrada["score"]:
                pos = idx
                break

        top5 = ordenados[:5]
        _ultimo_resultado = {"entry": entrada, "pos": pos, "top5": top5, "mode": modo_norm}

    return pos, top5

def obtener_ultimo_resultado():
    return _ultimo_resultado

def limpiar_ultimo_resultado():
    global _ultimo_resultado
    _ultimo_resultado = None

# Alias en inglés
load_scores = cargar_puntajes
save_all = guardar_todos
save_score = guardar_puntaje