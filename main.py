import os  # Para manejo de rutas y archivos
import sys  # Para obtener el intérprete de Python actual, esto para lanzar subprocesos
import subprocess  # Para lanzar otros scripts como subprocesos, esto para no bloquear la UI
import pygame
import json# Para manejo de archivos JSON (puntajes y configuraciones)
import puntajes
# OJO: aquí ya NO importamos juego todavía

# -------------------------
# Inicialización y constantes
# -------------------------
pygame.init()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------------
# Música de fondo del menú
# -------------------------
try:
    music_path = os.path.join(BASE_DIR, "musica_menu.mp3")  
    if os.path.exists(music_path):
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(0.55)  
        pygame.mixer.music.play(-1)    
    else:
        print("No se encontró la música del menú:", music_path)
except Exception as e:
    print("Error cargando música del menú:", e)

# Estado de sonido / UI de config
try:
    volumen_actual = pygame.mixer.music.get_volume()
except Exception:
    volumen_actual = 0.55
sonido_habilitado = True

# rects interactivos en la pantalla de config (se definen en draw_config)
SOUND_CHECK_RECT = None
VOL_MINUS_RECT = None
VOL_PLUS_RECT = None
CONTROLS_AREA_RECT = None


WIDTH, HEIGHT = 640, 480
SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = SCREEN.get_size()
pygame.display.set_caption("Escapa / Cazador - Menú")
FONT = pygame.font.SysFont("consolas", 24)
SMALL = pygame.font.SysFont("consolas", 18)
CLOCK = pygame.time.Clock()

import juego  # Importamos juego.py para llamar a su función main()

# Colores reutilizables
COLOR_BG = (18, 24, 30)
COLOR_BTN = (40, 120, 200)
COLOR_BTN_HOVER = (60, 150, 230)
COLOR_TEXT = (255, 255, 255)
COLOR_PANEL = (30, 40, 50)

# -------------------------
# Lanzamiento de la pantalla de selección (juego.py)
# -------------------------
def launch_game():
    # En lugar de abrir otro proceso, llamamos a juego.main()
    juego.main()

# -------------------------
# Clase Button
# -------------------------
class Button:
    def __init__(self, rect, text, callback):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.cb = callback

    def draw(self, surf): # Dibuja el botón, cambia color si el mouse está encima.
        mx, my = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mx, my)
        color = COLOR_BTN_HOVER if hover else COLOR_BTN
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        txt = FONT.render(self.text, True, COLOR_TEXT)
        tr = txt.get_rect(center=self.rect.center)
        surf.blit(txt, tr)

    def handle_event(self, e):
        # Ejecuta la callback asociada al clic izquierdo dentro del botón.
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos):
                try:
                    self.cb()
                except Exception as ex:
                    # Evitar que una excepción en la callback rompa la UI
                    print("Error en callback de botón:", ex)

# -------------------------
# Estado de la UI y callbacks de pantalla
# -------------------------
state = "menu"  # posibles: "menu", "scores", "config"
scores_cache = puntajes.cargar_puntajes()
selected_conf = {"num_enemies": 3, "enemy_speed_ms": 400}

def show_scores():
    global state, scores_cache
    scores_cache = puntajes.cargar_puntajes()
    state = "scores"

def show_config():
    global state
    state = "config"

def exit_game():
    pygame.quit()
    sys.exit()

# -------------------------
# Construcción de botones del menú principal
# -------------------------
btn_w, btn_h = 300, 56
gap = 16
start_y = HEIGHT//2 - (btn_h*4 + gap*3)//2

buttons = [
    Button((WIDTH//2 - btn_w//2, start_y + i*(btn_h+gap), btn_w, btn_h), txt, cb)
    for i, (txt, cb) in enumerate([
        ("Iniciar juego", launch_game),    # ahora dirige a juego.py
        ("Puntajes", show_scores),
        ("Configuraciones", show_config),
        ("Salir", exit_game)
    ])
]

# -------------------------
# Dibujo de pantallas
# -------------------------
def draw_menu():
    SCREEN.fill(COLOR_BG)
    title = FONT.render("Escapa / Cazador", True, COLOR_TEXT)
    tr = title.get_rect(center=(WIDTH//2, 80))
    SCREEN.blit(title, tr)
    subtitle = SMALL.render("Proyecto - Menú principal", True, COLOR_TEXT)
    SCREEN.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 110))
    for b in buttons:
        b.draw(SCREEN)

def draw_scores():
    SCREEN.fill(COLOR_BG)
    panel = pygame.Rect(60, 60, WIDTH-120, HEIGHT-120)
    pygame.draw.rect(SCREEN, COLOR_PANEL, panel, border_radius=8)
    title = FONT.render("Top 5 Puntajes por Modo", True, COLOR_TEXT)
    SCREEN.blit(title, (panel.x + 16, panel.y + 12))

    y = panel.y + 56
    ultimo = puntajes.obtener_ultimo_resultado()
    # Top 5 Cazador
    cazador_list = puntajes.cargar_puntajes(modo="cazador") or []
    try:
        top_cazador = sorted(cazador_list, key=lambda e: e.get("score", 0), reverse=True)[:5]
    except Exception:
        top_cazador = cazador_list[:5]

    header_c = SMALL.render("Cazador — Top 5", True, COLOR_TEXT)
    SCREEN.blit(header_c, (panel.x + 16, y))
    y += 28
    if not top_cazador:
        none_txt = SMALL.render("Sin puntajes para Cazador.", True, COLOR_TEXT)
        SCREEN.blit(none_txt, (panel.x + 16, y))
        y += 28
    else:
        for i, e in enumerate(top_cazador, start=1):
            nombre = e.get("name", "---")
            punt = e.get("score", 0)
            # resaltar si coincide con el último resultado guardado y es del mismo modo
            extra = ""
            color = COLOR_TEXT
            if ultimo and ultimo.get("mode") == "cazador":
                if ultimo.get("entry", {}).get("name") == e.get("name") and int(ultimo.get("entry", {}).get("score", 0)) == int(e.get("score", 0)):
                    extra = f"   <-- TU (#{ultimo.get('pos')})"
                    color = (240, 220, 80)
            línea = SMALL.render(f"{i}. {nombre}  -  {punt}{extra}", True, color)
            SCREEN.blit(línea, (panel.x + 16, y))
            y += 24

    y += 8  # separación entre secciones

    # Top 5 Escapa
    escapa_list = puntajes.cargar_puntajes(modo="escapa") or []
    try:
        top_escapa = sorted(escapa_list, key=lambda e: e.get("score", 0), reverse=True)[:5]
    except Exception:
        top_escapa = escapa_list[:5]

    header_e = SMALL.render("Escapa — Top 5", True, COLOR_TEXT)
    SCREEN.blit(header_e, (panel.x + 16, y))
    y += 28
    if not top_escapa:
        none_txt = SMALL.render("Sin puntajes para Escapa.", True, COLOR_TEXT)
        SCREEN.blit(none_txt, (panel.x + 16, y))
        y += 28
    else:
        for i, e in enumerate(top_escapa, start=1):
            nombre = e.get("name", "---")
            punt = e.get("score", 0)
            extra = ""
            color = COLOR_TEXT
            if ultimo and ultimo.get("mode") == "escapa":
                if ultimo.get("entry", {}).get("name") == e.get("name") and int(ultimo.get("entry", {}).get("score", 0)) == int(e.get("score", 0)):
                    extra = f"   <-- TU (#{ultimo.get('pos')})"
                    color = (240, 220, 80)
            línea = SMALL.render(f"{i}. {nombre}  -  {punt}{extra}", True, color)
            SCREEN.blit(línea, (panel.x + 16, y))
            y += 24

    back = SMALL.render("Presiona ESC o clic en pantalla para volver", True, COLOR_TEXT)
    SCREEN.blit(back, (panel.centerx - back.get_width()//2, panel.bottom - 34))

def draw_config():
    global SOUND_CHECK_RECT, VOL_MINUS_RECT, VOL_PLUS_RECT, CONTROLS_AREA_RECT, volumen_actual, sonido_habilitado
    SCREEN.fill(COLOR_BG)
    panel = pygame.Rect(80, 60, WIDTH-160, HEIGHT-120)
    pygame.draw.rect(SCREEN, COLOR_PANEL, panel, border_radius=8)
    title = FONT.render("Configuraciones", True, COLOR_TEXT)
    SCREEN.blit(title, (panel.x + 16, panel.y + 12))

    y = panel.y + 56

    # Sección: Sonido
    sub = SMALL.render("Sonido", True, COLOR_TEXT)
    SCREEN.blit(sub, (panel.x + 16, y))
    # casilla ON/OFF
    check_rect = pygame.Rect(panel.x + 140, y, 20, 20)
    SOUND_CHECK_RECT = check_rect
    pygame.draw.rect(SCREEN, (200,200,200), check_rect, border_radius=3)
    if sonido_habilitado:
        pygame.draw.rect(SCREEN, (60,200,80), check_rect.inflate(-4,-4), border_radius=2)
    else:
        pygame.draw.line(SCREEN, (200,50,50), check_rect.topleft, check_rect.bottomright, 2)
        pygame.draw.line(SCREEN, (200,50,50), check_rect.topright, check_rect.bottomleft, 2)

    # Volumen actual (porcentaje) y botones +/- 
    vol_pct = int(volumen_actual * 100)
    vol_txt = SMALL.render(f"Volumen: {vol_pct}%", True, COLOR_TEXT)
    SCREEN.blit(vol_txt, (panel.x + 16, y + 36))

    minus = pygame.Rect(panel.x + 140, y + 32, 28, 28)
    plus  = pygame.Rect(panel.x + 180, y + 32, 28, 28)
    VOL_MINUS_RECT = minus
    VOL_PLUS_RECT = plus
    pygame.draw.rect(SCREEN, COLOR_BTN, minus, border_radius=4)
    pygame.draw.rect(SCREEN, COLOR_BTN, plus, border_radius=4)
    SCREEN.blit(SMALL.render("-", True, COLOR_TEXT), minus.center)
    SCREEN.blit(SMALL.render("+", True, COLOR_TEXT), plus.center)

    # Nota breve de controles de teclado para volumen/sonido
    note = SMALL.render("Teclas: ↑ subir, ↓ bajar, S para activar/desactivar sonido", True, COLOR_TEXT)
    SCREEN.blit(note, (panel.x + 16, y + 72))

    y += 120

    # Sección: Controles del juego (lista)
    header = SMALL.render("Controles", True, COLOR_TEXT)
    SCREEN.blit(header, (panel.x + 16, y))
    y += 28
    controls = [
        "Moverse: Flechas ↑ ↓ ← →",
        "Correr / Dash: Shift (mantener)",
        "Interactuar / Seleccionar: Enter / Click",
        "Retroceder / Menu: Esc",
        "Activar trampas (si aplica): T (según modo)"
    ]
    CONTROLS_AREA_RECT = pygame.Rect(panel.x + 16, y, panel.width-32, 140)
    cy = y
    for c in controls:
        SCREEN.blit(SMALL.render(c, True, COLOR_TEXT), (panel.x + 24, cy))
        cy += 26

    # Pie con instrucciones para volver
    back = SMALL.render("Presiona ESC o clic en pantalla para volver", True, COLOR_TEXT)
    SCREEN.blit(back, (panel.centerx - back.get_width()//2, panel.bottom - 34))
    
# -------------------------
# Guardado de configuración
# -------------------------
def save_config():
    path = os.path.join(BASE_DIR, "config.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(selected_conf, f, indent=2)
        print("Configuración guardada en", path)
    except Exception as e:
        print("Error guardando configuración:", e)

# -------------------------
# Bucle principal
# -------------------------
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit_game()

        # Delegación por estado: menú (clicks en botones) / pantallas informativas
        if state == "menu":
            # En el menú delegamos los eventos de ratón a los botones
            for b in buttons:
                b.handle_event(event)

        elif state == "scores":
            # En la pantalla de puntajes: ESC o cualquier clic vuelve al menú
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state = "menu"
            if event.type == pygame.MOUSEBUTTONDOWN:
                state = "menu"

        elif state == "config":
            # En la pantalla de configuración manejamos teclas para editar valores
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    state = "menu"
                elif event.key == pygame.K_n:
                    selected_conf["num_enemies"] += 1
                elif event.key == pygame.K_m:
                    selected_conf["num_enemies"] = max(1, selected_conf["num_enemies"] - 1)
                elif event.key == pygame.K_u:
                    selected_conf["enemy_speed_ms"] = max(50, selected_conf["enemy_speed_ms"] - 50)
                elif event.key == pygame.K_i:
                    selected_conf["enemy_speed_ms"] += 50
                elif event.key == pygame.K_g:
                    save_config()
                # NUEVAS TECLAS: volumen y sonido
                elif event.key == pygame.K_UP:
                    volumen_actual = min(1.0, volumen_actual + 0.05)
                    try:
                        pygame.mixer.music.set_volume(volumen_actual)
                    except Exception:
                        pass
                elif event.key == pygame.K_DOWN:
                    volumen_actual = max(0.0, volumen_actual - 0.05)
                    try:
                        pygame.mixer.music.set_volume(volumen_actual)
                    except Exception:
                        pass
                elif event.key == pygame.K_s:
                    sonido_habilitado = not sonido_habilitado
                    try:
                        if sonido_habilitado:
                            pygame.mixer.music.set_volume(volumen_actual)
                            if not pygame.mixer.music.get_busy():
                                pygame.mixer.music.play(-1)
                        else:
                            pygame.mixer.music.set_volume(0.0)
                        # no detener la reproducción para mantener posición
                    except Exception:
                        pass
            # Clic también vuelve al menú o interactúa con los controles UI
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # clic general vuelve al menú
                # pero detectamos si hacen click sobre los controles interactivos
                if SOUND_CHECK_RECT and SOUND_CHECK_RECT.collidepoint(mx, my):
                    sonido_habilitado = not sonido_habilitado
                    try:
                        if sonido_habilitado:
                            pygame.mixer.music.set_volume(volumen_actual)
                            if not pygame.mixer.music.get_busy():
                                pygame.mixer.music.play(-1)
                        else:
                            pygame.mixer.music.set_volume(0.0)
                    except Exception:
                        pass
                elif VOL_MINUS_RECT and VOL_MINUS_RECT.collidepoint(mx, my):
                    volumen_actual = max(0.0, volumen_actual - 0.05)
                    try:
                        pygame.mixer.music.set_volume(volumen_actual if sonido_habilitado else 0.0)
                    except Exception:
                        pass
                elif VOL_PLUS_RECT and VOL_PLUS_RECT.collidepoint(mx, my):
                    volumen_actual = min(1.0, volumen_actual + 0.05)
                    try:
                        pygame.mixer.music.set_volume(volumen_actual if sonido_habilitado else 0.0)
                    except Exception:
                        pass
                else:
                    # clic fuera de controles regresa al menú
                    state = "menu"
    # Render según estado
    if state == "menu":
        draw_menu()
    elif state == "scores":
        draw_scores()
    elif state == "config":
        draw_config()

    pygame.display.flip()
    CLOCK.tick(60)