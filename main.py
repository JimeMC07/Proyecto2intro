import os  # Para manejo de rutas y archivos
import sys  # Para obtener el intérprete de Python actual, esto para lanzar subprocesos
import subprocess  # Para lanzar otros scripts como subprocesos, esto para no bloquear la UI
import pygame
import json  # Para manejo de archivos JSON (puntajes y configuraciones)
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
        print("⚠️ No se encontró la música del menú:", music_path)
except Exception as e:
    print("Error cargando música del menú:", e)

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
# Gestión de puntajes (I/O)
# -------------------------
def load_scores():
    path = os.path.join(BASE_DIR, "scores.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        # No se propaga la excepción para mantener la UI estable
        print("Error cargando scores.json:", e)
        return []

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
scores_cache = load_scores()
selected_conf = {"num_enemies": 3, "enemy_speed_ms": 400}

def show_scores():
    global state, scores_cache
    scores_cache = load_scores()
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
    title = FONT.render("Top Puntajes (Modo Cazador - ejemplo)", True, COLOR_TEXT)
    SCREEN.blit(title, (panel.x + 16, panel.y + 12))
    y = panel.y + 56
    if not scores_cache:
        nof = SMALL.render("No hay puntajes guardados. Juega para generar uno.", True, COLOR_TEXT)
        SCREEN.blit(nof, (panel.x + 16, y))
    else:
        for i, entry in enumerate(scores_cache[:10], start=1):
            txt = SMALL.render(f"{i}. {entry.get('name','---')}  -  {entry.get('score',0)}", True, COLOR_TEXT)
            SCREEN.blit(txt, (panel.x + 16, y))
            y += 28
    back = SMALL.render("Presiona ESC o clic en pantalla para volver", True, COLOR_TEXT)
    SCREEN.blit(back, (panel.centerx - back.get_width()//2, panel.bottom - 34))

def draw_config():
    SCREEN.fill(COLOR_BG)
    panel = pygame.Rect(80, 60, WIDTH-160, HEIGHT-120)
    pygame.draw.rect(SCREEN, COLOR_PANEL, panel, border_radius=8)
    title = FONT.render("Configuraciones (temporal)", True, COLOR_TEXT)
    SCREEN.blit(title, (panel.x + 16, panel.y + 12))
    lines = [
        f"Cantidad de enemigos: {selected_conf['num_enemies']}",
        f"Velocidad enemigos (ms tick): {selected_conf['enemy_speed_ms']}",
        "Usa teclas: N/n aumentar, M/m disminuir (enemigos).",
        "Presiona G para guardar (archivo config.json)."
    ]
    y = panel.y + 56
    for line in lines:
        txt = SMALL.render(line, True, COLOR_TEXT)
        SCREEN.blit(txt, (panel.x + 16, y))
        y += 28
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
                elif event.key in (pygame.K_n, pygame.K_N):
                    selected_conf["num_enemies"] += 1
                elif event.key in (pygame.K_m, pygame.K_M):
                    selected_conf["num_enemies"] = max(1, selected_conf["num_enemies"] - 1)
                elif event.key in (pygame.K_u, pygame.K_U):
                    selected_conf["enemy_speed_ms"] = max(50, selected_conf["enemy_speed_ms"] - 50)
                elif event.key in (pygame.K_i, pygame.K_I):
                    selected_conf["enemy_speed_ms"] += 50
                elif event.key in (pygame.K_g, pygame.K_G):
                    save_config()
            # Clic también vuelve al menú
            if event.type == pygame.MOUSEBUTTONDOWN:
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