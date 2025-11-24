import os
import sys
import subprocess  # (ya no lo usamos, pero lo dejo por si luego lo ocupas de nuevo)
import pygame
import json
import modo_cazador
import modo_escapa

# -------------------------
# Configuración / Constantes
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# OJO: aquí ya NO hacemos pygame.init(), eso lo hace main.py
# pygame.init()

# Intentar reutilizar la ventana existente (creada en main.py)
SCREEN = pygame.display.get_surface()
if SCREEN is None:
    # Si se ejecuta juego.py directamente (sin pasar por main),
    # entonces sí creamos la ventana fullscreen aquí.
    pygame.init()
    SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

SIZE = SCREEN.get_size()  # ahora SIZE tiene (ancho, alto) reales de la pantalla

pygame.display.set_caption("Registro y Selección de Modo - Escapa / Cazador")

FONT = pygame.font.SysFont("consolas", 26)
SMALL = pygame.font.SysFont("consolas", 18)
CLOCK = pygame.time.Clock()

COL_BG = (18, 24, 30)
COL_BTN = (40, 120, 200)
COL_BTN_H = (60, 150, 230)
COL_TEXT = (255, 255, 255)
COL_PANEL = (28, 34, 40)
COL_INPUT_BG = (245, 245, 245)
COL_INPUT_TEXT = (20, 20, 20)

# -------------------------
# Música de fondo
# -------------------------
try:
    music_path = os.path.join(BASE_DIR, "musica_menu.mp3")
    # Opcional: solo cargar si no hay música sonando
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(0.35)  # volumen entre 0.0 y 1.0
        pygame.mixer.music.play(-1)  # -1 = loop infinito
except Exception as e:
    print("Error cargando música:", e)

# -------------------------
# Estado de registro / UI
# -------------------------
player_name = ""         # texto actual del input
registered = False       # si ya completó el registro
message = ""             # mensaje informativo en pantalla

# Nuevos flags de submenús
in_cazador_menu = False
in_escapa_menu = False

PLAYERS_FILE = os.path.join(BASE_DIR, "players.json")

def load_players():
    try:
        if os.path.exists(PLAYERS_FILE):
            with open(PLAYERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_player(name):
    """Añade el nombre a players.json si no existe (historial simple)."""
    if not name:
        return
    players = load_players()
    if name not in players:
        players.append(name)
        try:
            with open(PLAYERS_FILE, "w", encoding="utf-8") as f:
                json.dump(players, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Error guardando players.json:", e)

# -------------------------
# Clase Button (simple)
# -------------------------
class Button:
    def __init__(self, rect, text, cb):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.cb = cb

    def draw(self, surf, enabled=True):
        mx, my = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mx, my) and enabled
        col = COL_BTN_H if hover else COL_BTN
        # si no está habilitado, atenuar
        if not enabled:
            col = (100, 100, 100)
        pygame.draw.rect(surf, col, self.rect, border_radius=8)
        txt = FONT.render(self.text, True, COL_TEXT if enabled else (200,200,200))
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle(self, e, enabled=True):
        if not enabled:
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            try:
                if callable(self.cb):
                    self.cb()
            except Exception as ex:
                print("Error en callback de botón:", ex)

# -------------------------
# UI: registro -> selección
# -------------------------
# Dimensiones botones selección
btn_w, btn_h = 360, 56
gap = 18
start_y = SIZE[1]//2 - (btn_h*3 + gap*2)//2 + 40

# --------- CALLBACKS PRINCIPALES ---------
def on_cazador():
    """En vez de ir directamente al juego, abre el submenú de dificultad."""
    global message, in_cazador_menu, in_escapa_menu
    message = ""
    in_escapa_menu = False
    in_cazador_menu = True

def on_escapa():
    """Abrir submenú de dificultad del modo Escapa (no iniciar todavía)."""
    global message, in_cazador_menu, in_escapa_menu
    message = ""
    in_cazador_menu = False
    in_escapa_menu = True

def on_quit():
    pygame.quit()
    sys.exit(0)

# --------- RESETEAR ESTADO DE MODO_CAZADOR ---------
def reset_cazador_estado():
    """Deja las variables globales de modo_cazador como si fuera una partida nueva."""
    try:
        modo_cazador.puntos = modo_cazador.PUNTOS_INICIALES
        modo_cazador.tiempo_restante = modo_cazador.TIEMPO_INICIAL
        modo_cazador.juego_terminado = False
        modo_cazador.energia_segmentos = modo_cazador.ENERGIA_MAX_SEGMENTOS
        modo_cazador.corriendo = False
        modo_cazador.jugador_dir_dx = 0
        modo_cazador.jugador_dir_dy = 0
    except AttributeError:
        # Por si en el futuro cambias algo en modo_cazador y falta alguna variable
        pass

# --------- RESETEAR ESTADO DE MODO_ESCAPA ---------
def reset_escapa_estado():
    """Reinicia las variables globales de modo_escapa para una nueva partida."""
    try:
        modo_escapa.juego_terminado = False
        modo_escapa.tiempo_restante = modo_escapa.TIEMPO_INICIAL
        modo_escapa.velocidad_enemigos = modo_escapa.VEL_BASE
        modo_escapa.player_dx = 0
        modo_escapa.player_dy = 0
        modo_escapa.contador_energia = modo_escapa.ENERGIA_MAX
        modo_escapa.corriendo = False
    except AttributeError:
        pass

# --------- CALLBACKS DE DIFICULTAD CAZADOR ---------
def start_cazador_facil():
    global message
    message = ""
    # Ajustar parámetros del modo cazador para fácil:
    modo_cazador.COLUMNAS = 15
    modo_cazador.FILAS = 11
    modo_cazador.ENEMY_TICK_MS = 500  # más lento
    reset_cazador_estado()
    modo_cazador.run()

def start_cazador_medio():
    global message
    message = ""
    # Valores originales (modo "normal")
    modo_cazador.COLUMNAS = 19
    modo_cazador.FILAS = 13
    modo_cazador.ENEMY_TICK_MS = 400
    reset_cazador_estado()
    modo_cazador.run()

def start_cazador_dificil():
    global message
    message = ""
    # Más grande y más rápido
    modo_cazador.COLUMNAS = 23
    modo_cazador.FILAS = 15
    modo_cazador.ENEMY_TICK_MS = 300  # más rápido
    reset_cazador_estado()
    modo_cazador.run()

def on_cazador_back():
    """Volver del submenú de dificultad al menú principal de modos."""
    global in_cazador_menu, message
    in_cazador_menu = False
    message = ""

# --------- CALLBACKS DE DIFICULTAD PARA MODO ESCAPA ---------
def start_escapa_facil():
    global message
    message = ""
    modo_escapa.VEL_BASE = 2     # más lento
    modo_escapa.TIEMPO_INICIAL = 30
    reset_escapa_estado()
    modo_escapa.run()

def start_escapa_medio():
    global message
    message = ""
    modo_escapa.VEL_BASE = 3
    modo_escapa.TIEMPO_INICIAL = 25
    reset_escapa_estado()
    modo_escapa.run()

def start_escapa_dificil():
    global message
    message = ""
    modo_escapa.VEL_BASE = 4     # enemigos muy rápidos
    modo_escapa.TIEMPO_INICIAL = 20
    reset_escapa_estado()
    modo_escapa.run()

def on_escapa_back():
    """Volver del submenú de Escapa al menú principal de modos."""
    global in_escapa_menu, message
    in_escapa_menu = False
    message = ""

# Botones de selección PRINCIPAL (se dibujan tras el registro)
buttons = [
    Button((SIZE[0]//2 - btn_w//2, start_y + i*(btn_h + gap), btn_w, btn_h), text, cb)
    for i, (text, cb) in enumerate([
        ("Modo Cazador (1)", lambda: on_cazador()),
        ("Modo Escapa (2)",  lambda: on_escapa()),
        ("Salir (ESC)",      lambda: on_quit())
    ])
]

# Botones del SUBMENÚ de dificultad del cazador
cazador_buttons = [
    Button((SIZE[0]//2 - btn_w//2, start_y + i*(btn_h + gap), btn_w, btn_h), text, cb)
    for i, (text, cb) in enumerate([
        ("Fácil",   start_cazador_facil),
        ("Medio",   start_cazador_medio),
        ("Difícil", start_cazador_dificil),
        ("Volver",  on_cazador_back),
    ])
]

# Botones del SUBMENÚ de dificultad del escapa
escapa_buttons = [
    Button((SIZE[0]//2 - btn_w//2, start_y + i*(btn_h + gap), btn_w, btn_h), text, cb)
    for i, (text, cb) in enumerate([
        ("Fácil",   start_escapa_facil),
        ("Medio",   start_escapa_medio),
        ("Difícil", start_escapa_dificil),
        ("Volver",  on_escapa_back),
    ])
]

# -------------------------
# Dibujo UI
# -------------------------
input_rect = pygame.Rect(120, 160, SIZE[0]-240, 44)
input_active = True
max_name_len = 20

def draw_registration():
    SCREEN.fill(COL_BG)
    title = FONT.render("Registro obligatorio", True, COL_TEXT)
    SCREEN.blit(title, title.get_rect(center=(SIZE[0]//2, 80)))
    subtitle = SMALL.render("Introduce tu nombre de jugador (obligatorio) y pulsa Enter o Continuar", True, COL_TEXT)
    SCREEN.blit(subtitle, (SIZE[0]//2 - subtitle.get_width()//2, 110))

    # input box
    pygame.draw.rect(SCREEN, COL_INPUT_BG, input_rect, border_radius=6)
    pygame.draw.rect(SCREEN, (100,100,100), input_rect, 2, border_radius=6)
    name_surf = FONT.render(
        player_name if player_name else "Escribe tu nombre...",
        True,
        COL_INPUT_TEXT if player_name else (120,120,120)
    )
    SCREEN.blit(name_surf, (input_rect.x + 8, input_rect.y + (input_rect.height - name_surf.get_height())//2))

    # continuar button
    cont_btn = Button((SIZE[0]//2 - 140, input_rect.bottom + 20, 280, 48), "Continuar", lambda: submit_registration())
    cont_btn.draw(SCREEN, enabled=(len(player_name.strip()) > 0))

    # historial rápido (últimos jugadores)
    players = load_players()
    if players:
        hs = SMALL.render("Historial: " + ", ".join(players[-6:]), True, (200,200,200))
        SCREEN.blit(hs, (input_rect.x, input_rect.bottom + 80))

    if message:
        msg_s = SMALL.render(message, True, (220,220,220))
        SCREEN.blit(msg_s, (20, SIZE[1]-30))

def draw_selection():
    SCREEN.fill(COL_BG)
    header = FONT.render(f"Jugador: {player_name}", True, COL_TEXT)
    SCREEN.blit(header, header.get_rect(center=(SIZE[0]//2, 48)))

    pygame.draw.rect(SCREEN, COL_PANEL, (40, 120, SIZE[0]-80, SIZE[1]-200), border_radius=10)

    if not in_cazador_menu and not in_escapa_menu:
        # Menú principal de modos
        subtitle = SMALL.render("Elige el modo de juego", True, COL_TEXT)
        SCREEN.blit(subtitle, (SIZE[0]//2 - subtitle.get_width()//2, 84))
        for b in buttons:
            b.draw(SCREEN)
    elif in_cazador_menu:
        # Submenú de dificultad del cazador
        subtitle = SMALL.render("Modo Cazador - Elige dificultad", True, COL_TEXT)
        SCREEN.blit(subtitle, (SIZE[0]//2 - subtitle.get_width()//2, 84))
        for b in cazador_buttons:
            b.draw(SCREEN)
    else:
        # Submenú de dificultad del escapa
        subtitle = SMALL.render("Modo Escapa - Elige dificultad", True, COL_TEXT)
        SCREEN.blit(subtitle, (SIZE[0]//2 - subtitle.get_width()//2, 84))
        for b in escapa_buttons:
            b.draw(SCREEN)

    if message:
        txt = SMALL.render(message, True, (220,220,220))
        SCREEN.blit(txt, (20, SIZE[1]-30))

# -------------------------
# Registro: manejar submit
# -------------------------
def submit_registration():
    global registered, message
    name = player_name.strip()
    if not name:
        message = "El nombre es obligatorio."
        return
    save_player(name)
    registered = True
    message = f"Registro completado: {name}"

# -------------------------
# Manejo de eventos
# -------------------------
def handle_event(e):
    global player_name, input_active, message, registered, in_cazador_menu, in_escapa_menu
    if e.type == pygame.QUIT:
        pygame.quit()
        sys.exit(0)

    if not registered:
        # entrada de texto para nombre
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit(0)
            elif e.key == pygame.K_RETURN:
                submit_registration()
            elif e.key == pygame.K_BACKSPACE:
                player_name = player_name[:-1]
            else:
                # añadir caracteres imprimibles
                ch = e.unicode
                if ch and len(player_name) < max_name_len and ch.isprintable():
                    player_name += ch
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            # clic sobre "Continuar" (dibujado en draw_registration)
            cont_btn_rect = pygame.Rect(SIZE[0]//2 - 140, input_rect.bottom + 20, 280, 48)
            if cont_btn_rect.collidepoint(e.pos) and len(player_name.strip()) > 0:
                submit_registration()
    else:
        # después del registro: selección de modo y atajos
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                # ESC solo sale del juego si estamos en el menú principal.
                # Si estamos en un submenú de dificultad, vuelve al menú de modos.
                if in_cazador_menu or in_escapa_menu:
                    in_cazador_menu = False
                    in_escapa_menu = False
                    message = ""
                else:
                    pygame.quit()
                    sys.exit(0)
            if e.key == pygame.K_1 and not in_escapa_menu:
                # Atajo: abrir menú de cazador (no lanza directamente el juego)
                on_cazador()
            if e.key == pygame.K_2 and not in_cazador_menu:
                # Atajo: abrir menú de escapa (no lanza directamente el juego)
                on_escapa()

        # Manejo de botones según la pantalla actual
        if in_cazador_menu:
            for b in cazador_buttons:
                b.handle(e, enabled=True)
        elif in_escapa_menu:
            for b in escapa_buttons:
                b.handle(e, enabled=True)
        else:
            for b in buttons:
                b.handle(e, enabled=True)

# -------------------------
# Bucle principal
# -------------------------
def main():
    global SCREEN, SIZE
    # Reasegurar que usamos la ventana actual (por si main cambió algo)
    surf = pygame.display.get_surface()
    if surf is not None:
        SCREEN = surf
        SIZE = SCREEN.get_size()

    while True:
        for e in pygame.event.get():
            handle_event(e)
        if not registered:
            draw_registration()
        else:
            draw_selection()
        pygame.display.flip()
        CLOCK.tick(60)

if __name__ == "__main__":
    main()
