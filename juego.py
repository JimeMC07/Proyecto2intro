import os
import sys
import subprocess  # Para lanzar otros scripts sin bloquear la UI
import pygame
import json

# -------------------------
# Configuración / Constantes
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
pygame.init()
# --- PANTALLA COMPLETA ---
SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
SIZE = SCREEN.get_size()  # ahora SIZE tiene (ancho, alto) reales de la pantalla

pygame.display.set_caption("Registro y Selección de Modo - Escapa / Cazador")

FONT = pygame.font.SysFont("consolas", 26)
SMALL = pygame.font.SysFont("consolas", 18)
CLOCK = pygame.time.Clock()

# -------------------------
# Música de fondo
# -------------------------
try:
    music_path = os.path.join(BASE_DIR, "musica_menu.mp3")
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.set_volume(0.35)  # volumen entre 0.0 y 1.0
    pygame.mixer.music.play(-1)  # -1 = loop infinito
except Exception as e:
    print("Error cargando música:", e)


COL_BG = (18, 24, 30)
COL_BTN = (40, 120, 200)
COL_BTN_H = (60, 150, 230)
COL_TEXT = (255, 255, 255)
COL_PANEL = (28, 34, 40)
COL_INPUT_BG = (245, 245, 245)
COL_INPUT_TEXT = (20, 20, 20)

# -------------------------
# Estado de registro / UI
# -------------------------
player_name = ""         # texto actual del input
registered = False       # si ya completó el registro
message = ""             # mensaje informativo en pantalla

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
# Control de instancia única para modos
# -------------------------
game_process = None  # Guarda el proceso lanzado, si existe

def launch_script(name, player):
    """
    Lanza el script indicado solo si no hay otro proceso de juego abierto.
    Pasa el nombre del jugador como argumento de línea de comandos.
    """
    global game_process
    path = os.path.join(BASE_DIR, name)
    if game_process is not None:
        if game_process.poll() is None:
            return f"Ya hay una ventana de juego abierta."
        else:
            game_process = None

    if not os.path.exists(path):
        return f"No encontrado: {name}"
    try:
        # Pasamos el nombre del jugador como argumento
        game_process = subprocess.Popen([sys.executable, path, player], cwd=BASE_DIR)
    except Exception as ex:
        print("Error al lanzar:", ex)
        return f"Error al lanzar {name}"
    return f"Lanzado: {name} (jugador: {player})"

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

# funciones que usan player_name dinámico
def on_cazador():
    global message
    message = launch_script("modo_cazador.py", player_name)
    # cerrar esta ventana para que quede solo la ventana del modo
    pygame.quit()
    sys.exit(0)

def on_escapa():
    global message
    message = launch_script("modo_escapa.py", player_name)
    pygame.quit()
    sys.exit(0)

def on_quit():
    pygame.quit()
    sys.exit(0)

# Botones de selección (se dibujan solo tras el registro)
buttons = [
    Button((SIZE[0]//2 - btn_w//2, start_y + i*(btn_h + gap), btn_w, btn_h), text, cb)
    for i, (text, cb) in enumerate([
        ("Modo Cazador (1)", lambda: on_cazador()),
        ("Modo Escapa (2)",  lambda: on_escapa()),
        ("Salir (ESC)", lambda: on_quit())
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
    name_surf = FONT.render(player_name if player_name else "Escribe tu nombre...", True, COL_INPUT_TEXT if player_name else (120,120,120))
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
    subtitle = SMALL.render("Elige el modo de juego", True, COL_TEXT)
    SCREEN.blit(subtitle, (SIZE[0]//2 - subtitle.get_width()//2, 84))
    pygame.draw.rect(SCREEN, COL_PANEL, (40, 120, SIZE[0]-80, SIZE[1]-200), border_radius=10)
    for b in buttons:
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
    global player_name, input_active, message, registered
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
                pygame.quit()
                sys.exit(0)
            if e.key == pygame.K_1:
                on_cazador()
            if e.key == pygame.K_2:
                on_escapa()
        for b in buttons:
            b.handle(e, enabled=True)

# -------------------------
# Bucle principal
# -------------------------
def main():
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