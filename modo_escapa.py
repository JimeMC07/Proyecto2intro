import pygame
import random
import sys
import os
import subprocess
import mapa

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------ Parámetros del laberinto ------------------
tamaño_celda = 40
COLUMNAS = 19
FILAS = 13

# ------------------ Parámetros de enemigos ------------------
NUM_ENEMIGOS   = 3
ENEMY_TICK_MS  = 400
RADIO_PELIGRO  = 99   # en este modo los enemigos siempre persiguen; valor grande
ENEMY_MOVE_DURATION_MS = 300

# ------------------ PUNTOS / RESULTADO ------------------
PUNTOS_INICIALES = 0   # en este modo se puede calcular puntaje por tiempo si se desea
puntos = PUNTOS_INICIALES
juego_terminado = False
victoria = False

# ------------------ TRAMPAS (nueva mecánica) ------------------
MAX_TRAPS = 3
TRAP_COOLDOWN_MS = 5000
ENEMY_RESPAWN_MS = 10000
TRAP_BONUS = 150

traps = []  # lista de dicts: {"x":int,"y":int,"placed_time":int}
last_trap_time = -10_000_000  # timestamp en ms de la última colocación

# ------------------ TIMER ------------------
TIEMPO_INICIAL = 60   # tiempo para escapar (segundos)
tiempo_restante = TIEMPO_INICIAL

# --- Movimiento suave jugador ---
PLAYER_MOVE_DURATION_MS = 120

# ------------------ Crear laberinto ------------------
# 0 = camino, 1 = muro, 2 = salida, 3 = liana, 4 = tunel
def crear_laberinto_basico():
    lab, sx, sy = mapa.generate_map(COLUMNAS, FILAS, start=(1,1))
    return lab, sx, sy

laberinto, salida_x, salida_y = crear_laberinto_basico()

# ------------------ Helpers de celdas ------------------
def celda_es_caminable(x, y):
    """
    Jugador (corredor):
    - SÍ: CAMINO, SALIDA, TÚNEL
    - NO: MURO, LIANA
    """
    if not (0 <= y < FILAS and 0 <= x < COLUMNAS):
        return False
    v = laberinto[y][x]
    return v in (mapa.CAMINO, mapa.SALIDA, mapa.TUNEL)


def celda_es_caminable_para_enemigo(x, y):
    """
    Enemigos (cazadores):
    - SÍ: CAMINO, SALIDA, LIANA
    - NO: MURO, TÚNEL
    """
    if not (0 <= y < FILAS and 0 <= x < COLUMNAS):
        return False
    v = laberinto[y][x]
    return v in (mapa.CAMINO, mapa.SALIDA, mapa.LIANA)


def distancia_manhattan(x1, y1, x2, y2):
    return abs(x1 - x2) + abs(y1 - y2)

# ------------------ Pygame init + FULLSCREEN + música ------------------
pygame.init()

# Música de fondo (misma que el menú / cazador)
try:
    music_path = os.path.join(BASE_DIR, "musica_menu.mp3")
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.set_volume(0.35)
    pygame.mixer.music.play(-1)
except Exception as e:
    print("Error cargando música en modo escapa:", e)

# Creamos pantalla en FULLSCREEN
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
screen_width, screen_height = screen.get_size()
pygame.display.set_caption("Modo 1: Escapa - Pygame (sin imágenes)")

# Panel lateral
PANEL_W = 240

# Márgenes y ajuste dinámico del tamaño de celda
MARGEN_X = 40
MARGEN_Y = 40

# Área útil para el laberinto (restando panel y márgenes)
usable_width  = screen_width  - PANEL_W - 2 * MARGEN_X
usable_height = screen_height - 2 * MARGEN_Y

# Nuevo tamaño de celda que cabe en pantalla
tamaño_celda = min(usable_width // COLUMNAS, usable_height // FILAS)
if tamaño_celda < 10:
    tamaño_celda = 10  # por si acaso resolución muy pequeña

# Ancho/alto reales del área de laberinto
ancho = COLUMNAS * tamaño_celda
alto  = FILAS * tamaño_celda

# Offset para centrar laberinto + panel
offset_x = (screen_width - (ancho + PANEL_W)) // 2
offset_y = (screen_height - alto) // 2

clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 20, bold=True)
big_font = pygame.font.SysFont("consolas", 96, bold=True)

# --------- Función para texto con salto de línea automático ---------
def draw_text_wrapped(surface, text, x, y, font, color, max_width):
    """
    Dibuja 'text' en varias líneas sin salirse de max_width.
    Devuelve la coordenada y donde terminó de dibujar.
    """
    words = text.split(" ")
    line = ""
    for word in words:
        test_line = line + word + " "
        if font.size(test_line)[0] <= max_width:
            line = test_line
        else:
            surface.blit(font.render(line, True, color), (x, y))
            y += font.get_height() + 2
            line = word + " "
    if line:
        surface.blit(font.render(line, True, color), (x, y))
        y += font.get_height() + 4
    return y

# Colores
COLOR_FONDO   = (0, 0, 0)
COLOR_CAMINO  = (17, 25, 34)
COLOR_MURO    = (51, 51, 102)
COLOR_SALIDA  = (170, 153, 51)
COLOR_JUGADOR = (0, 200, 200)
COLOR_ENEMIGO = (200, 60, 60)
COLOR_TRAP    = (200, 20, 200)

# ------------------ Jugador (corredor) ------------------
jugador_x = 1
jugador_y = 1

# Posición de renderizado (animación suave)
player_render_x = jugador_x * tamaño_celda
player_render_y = jugador_y * tamaño_celda
player_moving = False
player_move_start_time = 0
player_start_px = player_render_x
player_start_py = player_render_y
player_target_px = player_render_x
player_target_py = player_render_y

# ------------------ Enemigos ------------------
enemigos = []

def posiciones_enemigos():
    return {(e["x"], e["y"]) for e in enemigos if e.get("alive", True)}

def respawnear_enemigo(enemigo):
    posibles = []
    ocupadas = posiciones_enemigos() - {(enemigo["x"], enemigo["y"])}
    for y in range(FILAS):
        for x in range(COLUMNAS):
            if (celda_es_caminable_para_enemigo(x, y)
                and (x, y) != (jugador_x, jugador_y)
                and (x, y) != (salida_x, salida_y)
                and (x, y) not in ocupadas
                and not trap_at(x, y)):
                posibles.append((x, y))
    if not posibles:
        return
    nuevo_x, nuevo_y = random.choice(posibles)
    enemigo["x"] = nuevo_x
    enemigo["y"] = nuevo_y
    enemigo["prev_x"] = None
    enemigo["prev_y"] = None
    enemigo["render_x"] = enemigo["x"] * tamaño_celda
    enemigo["render_y"] = enemigo["y"] * tamaño_celda
    enemigo["moving"] = False
    enemigo["move_start_time"] = 0
    enemigo["start_px"] = enemigo["render_x"]
    enemigo["start_py"] = enemigo["render_y"]
    enemigo["target_px"] = enemigo["render_x"]
    enemigo["target_py"] = enemigo["render_y"]
    enemigo["alive"] = True
    enemigo["dead_time"] = None

# ------------------ Trampas: utilidades ------------------
def place_trap_near_player(now):
    global last_trap_time, message
    if len(traps) >= MAX_TRAPS:
        message = "Máximo de trampas activo."
        return
    if now - last_trap_time < TRAP_COOLDOWN_MS:
        remaining = (TRAP_COOLDOWN_MS - (now - last_trap_time))//1000 + 1
        message = f"Trampa en cooldown ({remaining}s)"
        return
    for dx, dy in [(1,0),(-1,0),(0,-1),(0,1)]:
        tx = jugador_x + dx
        ty = jugador_y + dy
        if 0 <= tx < COLUMNAS and 0 <= ty < FILAS:
            if (not trap_at(tx, ty)
                and celda_es_caminable_para_enemigo(tx, ty)
                and (tx, ty) != (salida_x, salida_y)
                and (tx, ty) != (jugador_x, jugador_y)
                and (tx, ty) not in posiciones_enemigos()):
                traps.append({"x":tx,"y":ty,"placed_time":now})
                last_trap_time = now
                message = f"Trampa colocada en ({tx},{ty})"
                return
    message = "No hay casilla válida cerca para colocar trampa."

def comprobar_captura():
    global juego_terminado, victoria
    if juego_terminado:
        return
    for enemigo in enemigos:
        if not enemigo.get("alive", True):
            continue
        if (jugador_x, jugador_y) == (enemigo["x"], enemigo["y"]):
            juego_terminado = True
            victoria = False
            return

def comprobar_llegada_salida():
    global juego_terminado, victoria
    if juego_terminado:
        return
    if (jugador_x, jugador_y) == (salida_x, salida_y):
        juego_terminado = True
        victoria = True
        return

def trap_at(x, y):
    for t in traps:
        if t["x"] == x and t["y"] == y:
            return t
    return None

def kill_enemy_on_trap(enemigo, now):
    global puntos, message
    if not enemigo.get("alive", True):
        return False
    t = trap_at(enemigo["x"], enemigo["y"])
    if t is not None:
        try:
            traps.remove(t)
        except ValueError:
            pass
        enemigo["alive"] = False
        enemigo["dead_time"] = now
        puntos += TRAP_BONUS
        message = f"Eliminado enemigo (+{TRAP_BONUS})"
        return True
    return False

# ------------------ Movimiento enemigos (IA perseguidora) ------------------
def mover_un_enemigo(enemigo):
    if juego_terminado:
        return
    if not enemigo.get("alive", True):
        return
    ex, ey = enemigo["x"], enemigo["y"]
    candidatos = []
    for dx, dy in [(0,-1),(0,1),(-1,0),(1,0)]:
        nx = ex + dx
        ny = ey + dy
        if not celda_es_caminable_para_enemigo(nx, ny):
            continue
        if any((nx == e2["x"] and ny == e2["y"] and e2 is not enemigo and e2.get("alive", True)) for e2 in enemigos):
            continue
        d_player = distancia_manhattan(nx, ny, jugador_x, jugador_y)
        d_exit = distancia_manhattan(nx, ny, salida_x, salida_y)
        candidatos.append((d_player, d_exit, nx, ny))

    if candidatos:
        if enemigo["prev_x"] is not None and enemigo["prev_y"] is not None:
            filtrados = [c for c in candidatos if not (c[2] == enemigo["prev_x"] and c[3] == enemigo["prev_y"])]
            if filtrados:
                candidatos = filtrados
        candidatos.sort(key=lambda c: (c[0], c[1]))
        mejor_d_player, mejor_d_exit, mejor_x, mejor_y = candidatos[0]
        enemigo["start_px"] = enemigo["x"] * tamaño_celda
        enemigo["start_py"] = enemigo["y"] * tamaño_celda
        enemigo["target_px"] = mejor_x * tamaño_celda
        enemigo["target_py"] = mejor_y * tamaño_celda
        enemigo["move_start_time"] = pygame.time.get_ticks()
        enemigo["moving"] = True
        enemigo["prev_x"] = enemigo["x"]
        enemigo["prev_y"] = enemigo["y"]
        enemigo["x"] = mejor_x
        enemigo["y"] = mejor_y

def mover_enemigos_tick(now):
    if juego_terminado:
        return
    for enemigo in enemigos:
        mover_un_enemigo(enemigo)
    for enemigo in enemigos:
        if not enemigo.get("alive", True):
            continue
        if kill_enemy_on_trap(enemigo, now):
            continue
    comprobar_captura()

# ------------------ Movimiento jugador ------------------
def mover_jugador(dx, dy):
    global jugador_x, jugador_y
    global player_moving, player_move_start_time
    global player_start_px, player_start_py, player_target_px, player_target_py

    if juego_terminado:
        return

    nx = jugador_x + dx
    ny = jugador_y + dy

    # 👉 NO moverse si la casilla no es válida para el jugador
    if not celda_es_caminable(nx, ny):
        return

    # animación suave
    player_start_px = jugador_x * tamaño_celda
    player_start_py = jugador_y * tamaño_celda
    player_target_px = nx * tamaño_celda
    player_target_py = ny * tamaño_celda
    player_move_start_time = pygame.time.get_ticks()
    player_moving = True

    jugador_x = nx
    jugador_y = ny

    comprobar_llegada_salida()
    comprobar_captura()

    # animación suave (la lógica de colisión la sigues manejando con mapa)
    player_start_px = jugador_x * tamaño_celda
    player_start_py = jugador_y * tamaño_celda
    player_target_px = nx * tamaño_celda
    player_target_py = ny * tamaño_celda
    player_move_start_time = pygame.time.get_ticks()
    player_moving = True

    jugador_x = nx
    jugador_y = ny

    comprobar_llegada_salida()
    comprobar_captura()

# ------------------ Dibujo ------------------
def dibujar_laberinto(surface):
    for fila in range(FILAS):
        for col in range(COLUMNAS):
            x = offset_x + col * tamaño_celda
            y = offset_y + fila * tamaño_celda
            celda = laberinto[fila][col]
            if celda == mapa.MURO:
                color = COLOR_MURO
            elif celda == mapa.SALIDA:
                color = COLOR_SALIDA
            elif celda == mapa.LIANA:
                color = (34, 139, 34)
            elif celda == mapa.TUNEL:
                color = (120, 85, 40)
            else:
                color = COLOR_CAMINO
            pygame.draw.rect(surface, color, (x, y, tamaño_celda, tamaño_celda))

def dibujar_leyenda(surface):
    panel_w = PANEL_W - 24
    panel_h = alto - 20
    panel_x = offset_x + ancho + 12
    panel_y = offset_y + 10
    panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    pygame.draw.rect(surface, (18,18,18), panel, border_radius=8)
    pygame.draw.rect(surface, (80,80,80), panel, 2, border_radius=8)

    small = pygame.font.SysFont("consolas", 16)
    x = panel_x + 14
    y = panel_y + 14
    box_size = 18

    titulo = font.render("Modo 1: Escapa", True, (230,230,230))
    surface.blit(titulo, (x, y))
    y += 40

    items = [
        (COLOR_CAMINO, "Camino — transitable por jugador y enemigos"),
        (COLOR_MURO,   "Muro — bloqueado"),
        (COLOR_SALIDA, "Salida — objetivo del jugador"),
        ((34,139,34),  "Liana — solo enemigos"),
        ((120,85,40),  "Túnel — solo jugador"),
        (COLOR_TRAP,   "Trampa — coloca con T o SPACE"),
    ]

    for col, label in items:
        box_y = y
        pygame.draw.rect(surface, col, (x, box_y, box_size, box_size))
        text_x = x + box_size + 10
        max_text_width = (panel_x + panel_w - 20) - text_x
        y = draw_text_wrapped(surface, label, text_x, box_y, small, (230,230,230), max_text_width)
        y += 6

    # instrucciones abajo del panel (con salto de línea automático)
    text_x = panel_x + 14
    max_text_width = panel_w - 40 

    y_bottom = panel_y + panel_h - 140 

    y_bottom = draw_text_wrapped(
        surface,
        "Colocar trampa: T o SPACE",
        text_x, y_bottom,
        small,
        (220, 220, 220),
        max_text_width
    )

    y_bottom = draw_text_wrapped(
        surface,
        f"Máx {MAX_TRAPS} trampas, CD: {TRAP_COOLDOWN_MS//1000}s",
        text_x, y_bottom,
        small,
        (200, 200, 200),
        max_text_width
    )

    y_bottom = draw_text_wrapped(
        surface,
        "Cazadores reaparecen +10s tras morir",
        text_x, y_bottom,
        small,
        (200, 200, 200),
        max_text_width
    )


def dibujar_traps(surface):
    for t in traps:
        rx = offset_x + t["x"] * tamaño_celda
        ry = offset_y + t["y"] * tamaño_celda
        margin = tamaño_celda // 4
        rect = pygame.Rect(rx + margin, ry + margin, tamaño_celda - 2*margin, tamaño_celda - 2*margin)
        pygame.draw.rect(surface, COLOR_TRAP, rect)

def dibujar_jugador(surface):
    px = offset_x + player_render_x
    py = offset_y + player_render_y
    margin = 6
    rect = pygame.Rect(px + margin, py + margin, tamaño_celda - 2*margin, tamaño_celda - 2*margin)
    pygame.draw.ellipse(surface, COLOR_JUGADOR, rect)
    pygame.draw.ellipse(surface, (255,255,255), rect, 2)

def dibujar_enemigos(surface):
    margin = 6
    for enemigo in enemigos:
        if not enemigo.get("alive", True):
            continue
        ex = offset_x + enemigo.get("render_x", enemigo["x"] * tamaño_celda)
        ey = offset_y + enemigo.get("render_y", enemigo["y"] * tamaño_celda)
        rect = pygame.Rect(ex + margin, ey + margin, tamaño_celda - 2*margin, tamaño_celda - 2*margin)
        pygame.draw.ellipse(surface, COLOR_ENEMIGO, rect)
        pygame.draw.ellipse(surface, (255,255,255), rect, 2)

def dibujar_textos(surface):
    txt = font.render(f"Tiempo: {tiempo_restante}s", True, (255,255,255))
    surface.blit(txt, (offset_x + 10, offset_y + 10))
    txt2 = font.render(f"Puntos: {puntos}", True, (255,255,255))
    surface.blit(txt2, (offset_x + ancho - txt2.get_width() - 10, offset_y + 10))
    now = pygame.time.get_ticks()
    cooldown_left = max(0, (TRAP_COOLDOWN_MS - (now - last_trap_time))//1000)
    tinfo = font.render(f"Trampas: {len(traps)}/{MAX_TRAPS}  CD: {cooldown_left}s", True, (255,255,255))
    surface.blit(tinfo, (offset_x + 10, offset_y + alto - 28))

def dibujar_resultado(surface):
    if not juego_terminado:
        return
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0,0,0,180))
    surface.blit(overlay, (0,0))

    full_center_x = screen_width // 2
    center_y = screen_height // 2

    if victoria:
        titulo = "¡Has escapado!"
        linea = "Victoria"
        color_t = (0, 255, 0)
        resumen = f"Tiempo restante: {tiempo_restante}s"
    else:
        titulo = "¡Te atraparon!"
        linea = "Derrota"
        color_t = (255, 0, 0)
        resumen = f"Tiempo restante: {tiempo_restante}s"

    t1 = font.render(titulo, True, color_t)
    t2 = font.render(linea, True, (255,255,255))
    t3 = font.render(resumen, True, (255,255,255))

    r1 = t1.get_rect(center=(full_center_x, center_y - 40))
    r2 = t2.get_rect(center=(full_center_x, center_y))
    r3 = t3.get_rect(center=(full_center_x, center_y + 40))

    surface.blit(t1, r1)
    surface.blit(t2, r2)
    surface.blit(t3, r3)

    instr1 = font.render("Presiona M para volver al menú", True, (220,220,220))
    instr2 = font.render("Presiona Q o ESC para salir", True, (220,220,220))
    ir1 = instr1.get_rect(center=(full_center_x, center_y + 100))
    ir2 = instr2.get_rect(center=(full_center_x, center_y + 130))
    surface.blit(instr1, ir1)
    surface.blit(instr2, ir2)

# ------------------ Animaciones ------------------
def actualizar_animacion_enemigos(now):
    for enemigo in enemigos:
        if not enemigo.get("alive", True):
            continue
        if not enemigo.get("moving", False):
            enemigo["render_x"] = enemigo["x"] * tamaño_celda
            enemigo["render_y"] = enemigo["y"] * tamaño_celda
            continue
        t = (now - enemigo["move_start_time"]) / ENEMY_MOVE_DURATION_MS
        if t >= 1.0:
            enemigo["render_x"] = enemigo["target_px"]
            enemigo["render_y"] = enemigo["target_py"]
            enemigo["moving"] = False
        else:
            sx = enemigo["start_px"]
            sy = enemigo["start_py"]
            tx = enemigo["target_px"]
            ty = enemigo["target_py"]
            enemigo["render_x"] = sx + (tx - sx) * t
            enemigo["render_y"] = sy + (ty - sy) * t

def actualizar_animacion_jugador(now):
    global player_render_x, player_render_y, player_moving
    if not player_moving:
        player_render_x = jugador_x * tamaño_celda
        player_render_y = jugador_y * tamaño_celda
        return
    t = (now - player_move_start_time) / PLAYER_MOVE_DURATION_MS
    if t >= 1.0:
        player_render_x = player_target_px
        player_render_y = player_target_py
        player_moving = False
    else:
        player_render_x = player_start_px + (player_target_px - player_start_px) * t
        player_render_y = player_start_py + (player_target_py - player_start_py) * t

# ------------------ Timer y ticks ------------------
last_enemy_tick = 0
last_timer_tick = 0

# ------------------ Pre-partida: countdown ------------------
pre_count = 3
pre_count_active = True
pre_last_tick = pygame.time.get_ticks()

# Crear enemigos iniciales
for _ in range(NUM_ENEMIGOS):
    enemigo = {
        "x": 0, "y": 0,
        "prev_x": None, "prev_y": None,
        "render_x": 0, "render_y": 0,
        "moving": False,
        "move_start_time": 0,
        "start_px": 0, "start_py": 0,
        "target_px": 0, "target_py": 0,
        "alive": True,
        "dead_time": None
    }
    enemigos.append(enemigo)
    respawnear_enemigo(enemigo)

def return_to_menu():
    menu_path = os.path.join(BASE_DIR, "main.py")
    try:
        if os.path.exists(menu_path):
            subprocess.Popen([sys.executable, menu_path], cwd=BASE_DIR)
    except Exception as ex:
        print("Error al relanzar menú:", ex)
    pygame.quit()
    sys.exit(0)

# ------------------ Bucle principal ------------------
running = True
message = ""
while running:
    dt = clock.tick(60)
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if juego_terminado:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    return_to_menu()
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if my > alto // 2:
                    return_to_menu()
            continue

        if not pre_count_active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                mover_jugador(0, -1)
            elif event.key == pygame.K_DOWN:
                mover_jugador(0, 1)
            elif event.key == pygame.K_LEFT:
                mover_jugador(-1, 0)
            elif event.key == pygame.K_RIGHT:
                mover_jugador(1, 0)
            elif event.key in (pygame.K_t, pygame.K_SPACE):
                place_trap_near_player(now)

    if pre_count_active:
        if now - pre_last_tick >= 1000:
            pre_last_tick = now
            pre_count -= 1
            if pre_count < 0:
                pre_count_active = False
                last_enemy_tick = now
                last_timer_tick = now

    if not juego_terminado and not pre_count_active and now - last_enemy_tick >= ENEMY_TICK_MS:
        last_enemy_tick = now
        mover_enemigos_tick(now)

    for enemigo in enemigos:
        if not enemigo.get("alive", True) and enemigo.get("dead_time") is not None:
            if now - enemigo["dead_time"] >= ENEMY_RESPAWN_MS:
                respawnear_enemigo(enemigo)

    actualizar_animacion_enemigos(now)
    actualizar_animacion_jugador(now)

    if not juego_terminado and not pre_count_active and now - last_timer_tick >= 1000:
        last_timer_tick = now
        if tiempo_restante > 0:
            tiempo_restante -= 1
        if tiempo_restante <= 0:
            tiempo_restante = 0
            juego_terminado = True
            victoria = False

    screen.fill(COLOR_FONDO)
    dibujar_laberinto(screen)
    dibujar_traps(screen)
    dibujar_enemigos(screen)
    dibujar_jugador(screen)
    dibujar_textos(screen)
    dibujar_resultado(screen)
    dibujar_leyenda(screen)

    if pre_count_active:
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((0,0,0,150))
        screen.blit(overlay, (0,0))
        txt_val = str(pre_count) if pre_count >= 0 else ""
        if txt_val != "":
            txt_surf = big_font.render(txt_val, True, (255,255,255))
            rect = txt_surf.get_rect(center=(screen_width//2, screen_height//2))
            screen.blit(txt_surf, rect)

    pygame.display.flip()

pygame.quit()
sys.exit()
