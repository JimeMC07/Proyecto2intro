import os 
import sys  
import subprocess  
import pygame
import json  

################################################################################################################################
################################################ Configuración inicial ##########################################################
pygame.init()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#---------------------------------------------------- musica de fondo ---------------------------------------------------------#
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

COLOR_BG = (18, 24, 30)
COLOR_BTN = (40, 120, 200)
COLOR_BTN_HOVER = (60, 150, 230)
COLOR_TEXT = (255, 255, 255)
COLOR_PANEL = (30, 40, 50)

################################################################################################################################
################################################ Funciones de carga de puntajes ################################################
#-------------------------------------------------- cargar puntajes -------------------------------------------------------#
# -------------------- Puntajes (archivo scores.json) -------------------- #
SCORES_FILE = os.path.join(BASE_DIR, "scores.json")

def cargar_puntajes():
    if not os.path.exists(SCORES_FILE):
        return {"escapa": [], "cazador": []}

    try:
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "escapa" not in data:
            data["escapa"] = []
        if "cazador" not in data:
            data["cazador"] = []
        return data
    except Exception as e:
        print("Error cargando scores.json:", e)
        return {"escapa": [], "cazador": []}
    
#------------------------------------------------ registrar puntaje -----------------------------------------------------#
def registrar_puntaje(modo, nombre, puntaje):
    data = cargar_puntajes()
    if modo not in data:
        data[modo] = []

    data[modo].append({"name": nombre, "score": puntaje})
    data[modo] = sorted(data[modo], key=lambda e: e["score"], reverse=True)[:5]

    try:
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error guardando scores.json:", e)

#----------------------------------------------------- Lanzar juego ---------------------------------------------------------#
def abrir_juego():
    global state
    resultado = juego.main()

    if resultado == "menu_principal":
        state = "menu"

#----------------------------------------------------- Clase Botón ---------------------------------------------------------#
class Button:
    def __init__(self, rect, text, callback):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.cb = callback

    def draw(self, surf):
        mx, my = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mx, my)
        color = COLOR_BTN_HOVER if hover else COLOR_BTN
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        txt = FONT.render(self.text, True, COLOR_TEXT)
        tr = txt.get_rect(center=self.rect.center)
        surf.blit(txt, tr)

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos):
                try:
                    self.cb()
                except Exception as ex:
                    print("Error en callback de botón:", ex)

state = "menu" 
scores_cache = cargar_puntajes()
selected_conf = {"num_enemies": 3, "enemy_speed_ms": 400}

#--------------------------------------------- mostrar puntajes ------------------------------------------------------#
def mostrar_puntajes():
    global state, scores_cache
    scores_cache = cargar_puntajes()
    state = "scores"

#------------------------------------------- mostrar configuracion ----------------------------------------------------#
def mostrar_configuracion():
    global state
    state = "config"

#---------------------------------------------- salir del juego ------------------------------------------------------#
def salir_juego():
    pygame.quit()
    sys.exit()

btn_w, btn_h = 300, 56
gap = 16
start_y = HEIGHT//2 - (btn_h*4 + gap*3)//2

buttons = [
    Button((WIDTH//2 - btn_w//2, start_y + i*(btn_h+gap), btn_w, btn_h), txt, cb)
    for i, (txt, cb) in enumerate([
        ("Iniciar juego", abrir_juego),  
        ("Puntajes", mostrar_puntajes),
        ("Configuraciones", mostrar_configuracion),
        ("Salir", salir_juego)
    ])
]

################################################################################################################################
################################################ Funciones de dibujo ##########################################################
#----------------------------------------------------- Dibujar menú ---------------------------------------------------------#
def dibujar_menu():
    SCREEN.fill(COLOR_BG)
    title = FONT.render("Escapa / Cazador", True, COLOR_TEXT)
    tr = title.get_rect(center=(WIDTH//2, 80))
    SCREEN.blit(title, tr)
    subtitle = SMALL.render("Proyecto - Menú principal", True, COLOR_TEXT)
    SCREEN.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 110))
    for b in buttons:
        b.draw(SCREEN)

#---------------------------------------------------- Dibujar puntajes -------------------------------------------------------#
def dibujar_puntajes():
    SCREEN.fill(COLOR_BG)

    panel = pygame.Rect(60, 60, WIDTH - 120, HEIGHT - 120)
    pygame.draw.rect(SCREEN, COLOR_PANEL, panel, border_radius=8)

    titulo = FONT.render("Puntajes", True, COLOR_TEXT)
    SCREEN.blit(titulo, (panel.x + (panel.width - titulo.get_width()) // 2, panel.y + 10))

    col_width = (panel.width - 40) // 2
    left_x  = panel.x + 20
    right_x = left_x + col_width + 20
    top_y   = panel.y + 50

    pygame.draw.line(
        SCREEN,
        (200, 200, 200),
        (panel.centerx, panel.y + 40),
        (panel.centerx, panel.bottom - 50),
        1,
    )

    # ---------- Columna izquierda: Modo Escapa ---------- #
    titulo_esc = FONT.render("Top 5 – Modo Escapa", True, COLOR_TEXT)
    SCREEN.blit(titulo_esc, (left_x, top_y))

    lista_escapa = sorted(
        scores_cache.get("escapa", []),
        key=lambda e: e.get("score", 0),
        reverse=True
    )[:5]

    y_esc = top_y + 40
    if not lista_escapa:
        sin_datos = SMALL.render("Sin puntajes aún.", True, COLOR_TEXT)
        SCREEN.blit(sin_datos, (left_x, y_esc))
    else:
        for i, entry in enumerate(lista_escapa, start=1):
            nombre = entry.get("name", "---")
            puntaje = entry.get("score", 0)
            linea = SMALL.render(f"{i}. {nombre}  -  {puntaje}", True, COLOR_TEXT)
            SCREEN.blit(linea, (left_x, y_esc))
            y_esc += 26

    # ---------- Columna derecha: Modo Cazador ---------- #
    titulo_caz = FONT.render("Top 5 – Modo Cazador", True, COLOR_TEXT)
    SCREEN.blit(titulo_caz, (right_x, top_y))

    lista_cazador = sorted(
        scores_cache.get("cazador", []),
        key=lambda e: e.get("score", 0),
        reverse=True
    )[:5]

    y_caz = top_y + 40
    if not lista_cazador:
        sin_datos = SMALL.render("Sin puntajes aún.", True, COLOR_TEXT)
        SCREEN.blit(sin_datos, (right_x, y_caz))
    else:
        for i, entry in enumerate(lista_cazador, start=1):
            nombre = entry.get("name", "---")
            puntaje = entry.get("score", 0)
            linea = SMALL.render(f"{i}. {nombre}  -  {puntaje}", True, COLOR_TEXT)
            SCREEN.blit(linea, (right_x, y_caz))
            y_caz += 26

    back = SMALL.render("Presiona ESC o clic en pantalla para volver", True, COLOR_TEXT)
    SCREEN.blit(back, (panel.centerx - back.get_width()//2, panel.bottom - 34))


#-------------------------------------------------- Dibujar configuración -----------------------------------------------------#
def dibujar_config():
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

################################################################################################################################
################################################ Funciones de configuración ######################################################
#----------------------------------------------------- Guardar config --------------------------------------------------------#
def guardar_config():
    path = os.path.join(BASE_DIR, "config.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(selected_conf, f, indent=2)
        print("Configuración guardada en", path)
    except Exception as e:
        print("Error guardando configuración:", e)

################################################################################################################################
################################################ Bucle principal ##############################################################
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            salir_juego()
        if state == "menu":
            for b in buttons:
                b.handle_event(event)
        elif state == "scores":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state = "menu"
            if event.type == pygame.MOUSEBUTTONDOWN:
                state = "menu"
        elif state == "config":
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
                    guardar_config()
            if event.type == pygame.MOUSEBUTTONDOWN:
                state = "menu"

    if state == "menu":
        dibujar_menu()
    elif state == "scores":
        dibujar_puntajes()
    elif state == "config":
        dibujar_config()

    pygame.display.flip()
    CLOCK.tick(60)