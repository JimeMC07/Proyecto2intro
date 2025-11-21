import pygame
import random
import sys
import os
import subprocess
import mapa

# --- NUEVO: base para volver al menú ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
pygame.init()

# -------------------------
# Música de fondo (misma que el menú)
# -------------------------
try:
    music_path = os.path.join(BASE_DIR, "musica_menu.mp3")  
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.set_volume(0.35)  
    pygame.mixer.music.play(-1)         
except Exception as e:
    print("Error cargando música en modo de juego:", e)


# ------------------ Parámetros del laberinto ------------------
COLUMNAS = 19
FILAS = 13

# El tamaño de celda se recalcula después según la resolución
tamaño_celda = 40      # valor base, luego se ajusta

# ------------------ Parámetros de enemigos ------------------
NUM_ENEMIGOS   = 3      # <- cantidad de enemigos
ENEMY_TICK_MS  = 400    # <- cada cuántos ms se mueven (menor = más rápido)
RADIO_PELIGRO  = 3      # distancia a la que "reacciona" al jugador
ENEMY_MOVE_DURATION_MS = 300  # duración de la animación de paso enemigo

# ------------------ PUNTOS ------------------
PUNTOS_INICIALES   = 800
PUNTOS_POR_CAPTURA = 200
PUNTOS_POR_ESCAPE  = 100

puntos = PUNTOS_INICIALES
juego_terminado = False   # bandera para detener el juego

# ------------------ TIMER ------------------
TIEMPO_INICIAL = 20      # segundos de partida (CÁMBIALO AQUÍ)
tiempo_restante = TIEMPO_INICIAL

# ------------------ ENERGÍA / CARRERA ------------------
ENERGIA_MAX_SEGMENTOS = 4     # barra dividida en 4 partes
energia_segmentos = ENERGIA_MAX_SEGMENTOS  # empieza llena
corriendo = False             # true mientras está haciendo el dash
jugador_dir_dx = 0            # última dirección de movimiento (x)
jugador_dir_dy = 0            # última dirección de movimiento (y)

# --- JUGADOR SUAVE ---
PLAYER_MOVE_DURATION_MS = 120  # duración animación al caminar

# --- BOTONES GAME OVER ---
btn_menu_rect = None
btn_retry_rect = None
btn_exit_rect = None

# ------------------ Pygame init ------------------
pygame.init()

# Creamos pantalla en FULLSCREEN
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
screen_width, screen_height = screen.get_size()
pygame.display.setCaption = pygame.display.set_caption("Modo 2: Cazador - Pygame (sin imágenes)")

# Panel lateral
PANEL_W = 240

# --- NUEVO: márgenes y ajuste dinámico del tamaño de celda ---
MARGEN_X = 40
MARGEN_Y = 40

# Área útil para el laberinto (restando panel y márgenes)
usable_width  = screen_width  - PANEL_W - 2 * MARGEN_X
usable_height = screen_height - 2 * MARGEN_Y

# Nuevo tamaño de celda que cabe en pantalla
tamaño_celda = min(usable_width // COLUMNAS, usable_height // FILAS)
if tamaño_celda < 10:
    tamaño_celda = 10  # por si acaso resolución muy pequeña

# Ahora sí, ancho/alto reales del área del laberinto
ancho = COLUMNAS * tamaño_celda
alto  = FILAS * tamaño_celda

# Offset para centrar laberinto + panel dejando bordes
offset_x = (screen_width - (ancho + PANEL_W)) // 2
offset_y = (screen_height - alto) // 2

clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 20, bold=True)

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
        # ¿Cuánto mide en píxeles esta línea de prueba?
        if font.size(test_line)[0] <= max_width:
            line = test_line
        else:
            surface.blit(font.render(line, True, color), (x, y))
            y += font.get_height() + 2
            line = word + " "
    # Última línea
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
COLOR_ENERGIA_LLENA = (0, 255, 0)
COLOR_ENERGIA_VACIA = (40, 40, 40)

# ------------------ Crear laberinto ------------------
def crear_laberinto_basico():
    lab, sx, sy = mapa.generate_map(COLUMNAS, FILAS, start=(1, 1))
    return lab, sx, sy

laberinto, salida_x, salida_y = crear_laberinto_basico()

# --------- CAMINABILIDAD ESPECÍFICA PARA CADA LADO ---------
def celda_es_caminable(x, y):
    """
    Caminabilidad del JUGADOR (cazador):
    - Puede pasar por CAMINO, SALIDA y LIANA (verde).
    - NO puede pasar por TÚNEL.
    """
    if not (0 <= y < FILAS and 0 <= x < COLUMNAS):
        return False
    v = laberinto[y][x]
    return v in (mapa.CAMINO, mapa.SALIDA, mapa.LIANA)

def celda_es_caminable_enemigo(x, y):
    """
    Caminabilidad de los ENEMIGOS:
    - Pueden pasar por CAMINO, SALIDA y TÚNEL (marrón).
    - NO pueden pasar por LIANA.
    """
    if not (0 <= y < FILAS and 0 <= x < COLUMNAS):
        return False
    v = laberinto[y][x]
    return v in (mapa.CAMINO, mapa.SALIDA, mapa.TUNEL)

def distancia_manhattan(x1, y1, x2, y2):
    return abs(x1 - x2) + abs(y1 - y2)

# ------------------ Jugador (cazador) ------------------
jugador_x = 1
jugador_y = 1

# Posición de renderizado (animación suave, EN PIXELES de la grilla, sin offset)
player_render_x = jugador_x * tamaño_celda
player_render_y = jugador_y * tamaño_celda
player_moving = False
player_move_start_time = 0
player_start_px = player_render_x
player_start_py = player_render_y
player_target_px = player_render_x
player_target_py = player_render_y

# ------------------ Enemigos (lista) ------------------
enemigos = []

def posiciones_enemigos():
    """Devuelve un set con las posiciones ocupadas por enemigos."""
    return {(e["x"], e["y"]) for e in enemigos}

def respawnear_enemigo(enemigo):
    """Coloca a un enemigo en una celda libre (no jugador, no salida, no otro enemigo)."""
    posibles = []
    ocupadas = posiciones_enemigos() - {(enemigo["x"], enemigo["y"])}

    for y in range(FILAS):
        for x in range(COLUMNAS):
            if (celda_es_caminable_enemigo(x, y)
                and (x, y) != (jugador_x, jugador_y)
                and (x, y) != (salida_x, salida_y)
                and (x, y) not in ocupadas):
                posibles.append((x, y))

    if not posibles:
        return

    nuevo_x, nuevo_y = random.choice(posibles)
    enemigo["x"] = nuevo_x
    enemigo["y"] = nuevo_y
    enemigo["prev_x"] = None
    enemigo["prev_y"] = None

    # iniciar posición de renderizado en píxeles (SIN offset)
    enemigo["render_x"] = enemigo["x"] * tamaño_celda
    enemigo["render_y"] = enemigo["y"] * tamaño_celda
    enemigo["moving"] = False
    enemigo["move_start_time"] = 0
    enemigo["start_px"] = enemigo["render_x"]
    enemigo["start_py"] = enemigo["render_y"]
    enemigo["target_px"] = enemigo["render_x"]
    enemigo["target_py"] = enemigo["render_y"]

def comprobar_captura():
    """Si el jugador y algún enemigo están en la misma celda, lo captura (gana puntos y energía)."""
    global puntos, energia_segmentos

    if juego_terminado:
        return

    for enemigo in enemigos:
        if (jugador_x, jugador_y) == (enemigo["x"], enemigo["y"]):
            print("¡Enemigo atrapado! +200 puntos. Respawn...")
            puntos += PUNTOS_POR_CAPTURA

            if energia_segmentos < ENERGIA_MAX_SEGMENTOS:
                energia_segmentos += 1

            respawnear_enemigo(enemigo)

def comprobar_salida():
    """Si un enemigo llega a la salida, se considera que escapó (pierde puntos)."""
    global puntos, juego_terminado

    if juego_terminado:
        return

    for enemigo in enemigos:
        if (enemigo["x"], enemigo["y"]) == (salida_x, salida_y):
            print("Un enemigo cruzó la salida. -100 puntos. Respawn...")
            puntos -= PUNTOS_POR_ESCAPE
            respawnear_enemigo(enemigo)

    if puntos <= 0 and not juego_terminado:
        puntos = 0
        game_over(motivo="puntos")

def mover_un_enemigo(enemigo):
    """IA híbrida para UN enemigo (misma lógica que tenías)."""
    if juego_terminado:
        return

    ex, ey = enemigo["x"], enemigo["y"]
    dist_jugador = distancia_manhattan(ex, ey, jugador_x, jugador_y)

    candidatos = []
    for dx, dy in [(0,-1), (0,1), (-1,0), (1,0)]:
        nx = ex + dx
        ny = ey + dy
        if not celda_es_caminable_enemigo(nx, ny):
            continue

        if any((nx == e2["x"] and ny == e2["y"] and e2 is not enemigo) for e2 in enemigos):
            continue

        d_exit = distancia_manhattan(nx, ny, salida_x, salida_y)
        d_player = distancia_manhattan(nx, ny, jugador_x, jugador_y)
        candidatos.append((d_exit, d_player, nx, ny))

    if candidatos:
        if enemigo["prev_x"] is not None and enemigo["prev_y"] is not None:
            filtrados = [
                c for c in candidatos
                if not (c[2] == enemigo["prev_x"] and c[3] == enemigo["prev_y"])
            ]
            if filtrados:
                candidatos = filtrados

        if dist_jugador <= RADIO_PELIGRO:
            candidatos.sort(key=lambda c: (-c[1], c[0]))
        else:
            candidatos.sort(key=lambda c: (c[0], -c[1]))

        mejor_d_exit, mejor_d_player, mejor_x, mejor_y = candidatos[0]

        # animación suave entre casillas
        enemigo["start_px"]  = enemigo["x"] * tamaño_celda
        enemigo["start_py"]  = enemigo["y"] * tamaño_celda
        enemigo["target_px"] = mejor_x * tamaño_celda
        enemigo["target_py"] = mejor_y * tamaño_celda
        enemigo["move_start_time"] = pygame.time.get_ticks()
        enemigo["moving"] = True

        enemigo["prev_x"] = enemigo["x"]
        enemigo["prev_y"] = enemigo["y"]
        enemigo["x"] = mejor_x
        enemigo["y"] = mejor_y

def mover_enemigos_tick():
    if juego_terminado:
        return
    for enemigo in enemigos:
        mover_un_enemigo(enemigo)
    comprobar_captura()
    comprobar_salida()

def game_over(motivo="puntos"):
    global juego_terminado
    if juego_terminado:
        return
    juego_terminado = True

def fin_partida_por_tiempo():
    global juego_terminado
    if juego_terminado:
        return
    juego_terminado = True

# ------------------ Movimiento del jugador ------------------
def mover_jugador(dx, dy):
    """Mueve al jugador una casilla si no hay muro (con animación suave)."""
    global jugador_x, jugador_y, jugador_dir_dx, jugador_dir_dy
    global player_moving, player_move_start_time
    global player_start_px, player_start_py, player_target_px, player_target_py

    if juego_terminado or corriendo:
        return

    nuevo_x = jugador_x + dx
    nuevo_y = jugador_y + dy

    if not celda_es_caminable(nuevo_x, nuevo_y):
        return  # hay muro o fuera del mapa

    # animación suave del jugador (sin offset, solo grilla)
    player_start_px  = jugador_x * tamaño_celda
    player_start_py  = jugador_y * tamaño_celda
    player_target_px = nuevo_x * tamaño_celda
    player_target_py = nuevo_y * tamaño_celda
    player_move_start_time = pygame.time.get_ticks()
    player_moving = True

    jugador_x = nuevo_x
    jugador_y = nuevo_y
    jugador_dir_dx = dx
    jugador_dir_dy = dy

    comprobar_captura()

def dash_paso(pasos_restantes):
    """Implementación del dash paso a paso en Pygame (misma lógica)."""
    global jugador_x, jugador_y, corriendo, dash_pasos_restantes

    if pasos_restantes <= 0 or juego_terminado:
        corriendo = False
        dash_pasos_restantes = 0
        return

    nx = jugador_x + jugador_dir_dx
    ny = jugador_y + jugador_dir_dy

    if not celda_es_caminable(nx, ny):
        corriendo = False
        dash_pasos_restantes = 0
        return

    jugador_x = nx
    jugador_y = ny
    comprobar_captura()
    dash_pasos_restantes = pasos_restantes

def activar_carrera():
    """Usa la barra de energía para correr 4 casillas en la última dirección."""
    global energia_segmentos, corriendo, dash_pasos_restantes

    if juego_terminado:
        return
    if corriendo:
        return
    if energia_segmentos < ENERGIA_MAX_SEGMENTOS:
        return
    if jugador_dir_dx == 0 and jugador_dir_dy == 0:
        return

    energia_segmentos = 0
    corriendo = True
    dash_pasos_restantes = 4   # 4 casillas

# --------- REINICIAR PARTIDA ---------
def reiniciar_partida():
    global puntos, tiempo_restante, juego_terminado
    global energia_segmentos, corriendo, jugador_dir_dx, jugador_dir_dy
    global laberinto, salida_x, salida_y
    global jugador_x, jugador_y
    global player_render_x, player_render_y, player_moving
    global player_move_start_time, player_start_px, player_start_py
    global player_target_px, player_target_py
    global enemigos
    global last_enemy_tick, last_timer_tick, dash_pasos_restantes, last_dash_step_tick

    puntos = PUNTOS_INICIALES
    tiempo_restante = TIEMPO_INICIAL
    juego_terminado = False

    energia_segmentos = ENERGIA_MAX_SEGMENTOS
    corriendo = False
    jugador_dir_dx = 0
    jugador_dir_dy = 0

    # regenerar mapa y salida
    laberinto, salida_x, salida_y = crear_laberinto_basico()

    # reiniciar jugador
    jugador_x = 1
    jugador_y = 1
    player_render_x = jugador_x * tamaño_celda
    player_render_y = jugador_y * tamaño_celda
    player_moving = False
    player_move_start_time = 0
    player_start_px = player_render_x
    player_start_py = player_render_y
    player_target_px = player_render_x
    player_target_py = player_render_y

    # reiniciar enemigos
    enemigos.clear()
    for _ in range(NUM_ENEMIGOS):
        enemigo = {
            "x": 0, "y": 0,
            "prev_x": None, "prev_y": None,
            "render_x": 0, "render_y": 0,
            "moving": False,
            "move_start_time": 0,
            "start_px": 0, "start_py": 0,
            "target_px": 0, "target_py": 0
        }
        enemigos.append(enemigo)
        respawnear_enemigo(enemigo)

    # reset ticks
    now = pygame.time.get_ticks()
    last_enemy_tick = now
    last_timer_tick = now
    dash_pasos_restantes = 0
    last_dash_step_tick = now

# --- misma función que en modo_escapa para volver al menú ---
def return_to_menu():
    menu_path = os.path.join(BASE_DIR, "main.py")
    try:
        if os.path.exists(menu_path):
            subprocess.Popen([sys.executable, menu_path], cwd=BASE_DIR)
    except Exception as ex:
        print("Error al relanzar menú:", ex)
    pygame.quit()
    sys.exit(0)

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
                color = (34, 139, 34)   # verde para liana
            elif celda == mapa.TUNEL:
                color = (120, 85, 40)   # marrón para túnel
            else:
                color = COLOR_CAMINO
            pygame.draw.rect(surface, color, (x, y, tamaño_celda, tamaño_celda))

def dibujar_leyenda(surface):
    """Panel lateral con explicación del modo Cazador."""
    panel_w = PANEL_W - 24
    panel_h = alto - 20
    panel_x = offset_x + ancho + 12   # justo a la derecha del área de juego
    panel_y = offset_y + 10
    panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    pygame.draw.rect(surface, (18, 18, 18), panel, border_radius=8)
    pygame.draw.rect(surface, (80, 80, 80), panel, 2, border_radius=8)

    small = pygame.font.SysFont("consolas", 16)

    x = panel_x + 14
    y = panel_y + 14
    gap = 34
    box_size = 18

    titulo = font.render("Modo 2: Cazador", True, (230, 230, 230))
    surface.blit(titulo, (x, y))
    y += 40

    items = [
        (COLOR_CAMINO, "Camino — pasan jugador y enemigos"),
        (COLOR_MURO,   "Muro — bloquea el paso"),
        (COLOR_SALIDA, "Salida — los enemigos escapan aquí"),
        ((34,139,34),  "Liana — solo jugador"),
        ((120,85,40),  "Túnel — solo enemigos"),
    ]

    for col, label in items:
        # Cuadradito de color
        box_y = y
        pygame.draw.rect(surface, col, (x, box_y, box_size, box_size))

        # Texto a la derecha del cuadro, con salto de línea automático
        text_x = x + box_size + 10
        # margen interno derecho del panel (20 píxeles aprox)
        max_text_width = (panel_x + panel_w - 20) - text_x  

        y = draw_text_wrapped(
            surface,
            label,
            text_x, box_y,
            small,
            (230, 230, 230),
            max_text_width
        )

        # pequeño espacio vertical entre un item y otro
        y += 6


    # Texto explicativo con salto de línea automático
    y += 10
    max_text_width = panel_w - 40  # margen interno para que no toque el borde

    y = draw_text_wrapped(
        surface,
        "Objetivo: atrapar enemigos antes de que crucen la salida.",
        x, y, small, (220, 220, 220),
        max_text_width
    )

    y = draw_text_wrapped(
        surface,
        "Flechas: mover al cazador. Shift: correr 4 casillas.",
        x, y, small, (200, 200, 200),
        max_text_width
    )

    y = draw_text_wrapped(
        surface,
        "La barra verde se vacía al correr y se rellena con enemigos capturados.",
        x, y, small, (200, 200, 200),
        max_text_width
    )

    y = draw_text_wrapped(
        surface,
        "+200 puntos por captura. -100 puntos si un enemigo escapa.",
        x, y, small, (200, 200, 200),
        max_text_width
    )


def dibujar_jugador(surface):
    px = offset_x + player_render_x
    py = offset_y + player_render_y
    margin = 6
    rect = pygame.Rect(
        px + margin,
        py + margin,
        tamaño_celda - 2 * margin,
        tamaño_celda - 2 * margin
    )
    pygame.draw.ellipse(surface, COLOR_JUGADOR, rect)
    pygame.draw.ellipse(surface, (255, 255, 255), rect, 2)

def dibujar_enemigos(surface):
    margin = 6
    for enemigo in enemigos:
        ex = offset_x + enemigo.get("render_x", enemigo["x"] * tamaño_celda)
        ey = offset_y + enemigo.get("render_y", enemigo["y"] * tamaño_celda)
        rect = pygame.Rect(
            ex + margin,
            ey + margin,
            tamaño_celda - 2 * margin,
            tamaño_celda - 2 * margin
        )
        pygame.draw.ellipse(surface, COLOR_ENEMIGO, rect)
        pygame.draw.ellipse(surface, (255, 255, 255), rect, 2)

def dibujar_textos(surface):
    # Puntos centrados sobre el área de juego
    center_x = offset_x + ancho // 2
    txt = font.render(f"Puntos: {puntos}", True, (255, 255, 255))
    rect = txt.get_rect(center=(center_x, offset_y + 20))
    surface.blit(txt, rect)

    # Timer en la esquina superior derecha del área de juego
    txt2 = font.render(f"Tiempo: {tiempo_restante}s", True, (255, 255, 255))
    rect2 = txt2.get_rect(midright=(offset_x + ancho - 10, offset_y + 20))
    surface.blit(txt2, rect2)

def dibujar_barra_energia(surface):
    base_x = offset_x + jugador_x * tamaño_celda
    base_y = offset_y + jugador_y * tamaño_celda - 8  # encima de la cabeza
    seg_width = tamaño_celda / ENERGIA_MAX_SEGMENTOS - 2
    for i in range(ENERGIA_MAX_SEGMENTOS):
        x0 = base_x + 2 + i * (seg_width + 1)
        y0 = base_y
        rect = pygame.Rect(x0, y0, seg_width, 6)
        if i < energia_segmentos:
            color = COLOR_ENERGIA_LLENA
        else:
            color = COLOR_ENERGIA_VACIA
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, (255, 255, 255), rect, 1)

def dibujar_game_over(surface):
    global btn_menu_rect, btn_retry_rect, btn_exit_rect

    if not juego_terminado:
        return
    # overlay que cubre TODA la pantalla
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

    full_center_x = screen_width // 2
    center_y = screen_height // 2

    if tiempo_restante <= 0:
        titulo = "¡Tiempo agotado!"
        linea = "Fin de la partida"
        resumen = f"Puntos finales: {puntos}"
        color_titulo = (255, 255, 0)
    else:
        titulo = "GAME OVER"
        linea = "Te quedaste sin puntos"
        tiempo_jugado = TIEMPO_INICIAL - max(tiempo_restante, 0)
        min_j, seg_j = divmod(tiempo_jugado, 60)
        resumen = f"Tiempo: {min_j:02d}:{seg_j:02d}   Puntos: {puntos}"
        color_titulo = (255, 0, 0)

    t1 = font.render(titulo, True, color_titulo)
    t2 = font.render(linea, True, (255, 255, 255))
    t3 = font.render(resumen, True, (255, 255, 255))

    r1 = t1.get_rect(center=(full_center_x, center_y - 60))
    r2 = t2.get_rect(center=(full_center_x, center_y - 25))
    r3 = t3.get_rect(center=(full_center_x, center_y + 10))

    surface.blit(t1, r1)
    surface.blit(t2, r2)
    surface.blit(t3, r3)

    # --- Botones: Volver al menú, Reiniciar, Salir ---
    btn_w, btn_h = 200, 40
    espacio = 15
    start_y = center_y + 60

    btn_menu_rect  = pygame.Rect(full_center_x - btn_w // 2, start_y, btn_w, btn_h)
    btn_retry_rect = pygame.Rect(full_center_x - btn_w // 2, start_y + (btn_h + espacio), btn_w, btn_h)
    btn_exit_rect  = pygame.Rect(full_center_x - btn_w // 2, start_y + 2 * (btn_h + espacio), btn_w, btn_h)

    def dibujar_boton(rect, texto):
        pygame.draw.rect(surface, (60, 60, 60), rect, border_radius=8)
        pygame.draw.rect(surface, (200, 200, 200), rect, 2, border_radius=8)
        txt = font.render(texto, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=rect.center)
        surface.blit(txt, txt_rect)

    dibujar_boton(btn_menu_rect,  "Volver al menú")
    dibujar_boton(btn_retry_rect, "Reiniciar")
    dibujar_boton(btn_exit_rect,  "Salir")

# --- Animaciones suaves ---
def actualizar_animacion_enemigos(now):
    for enemigo in enemigos:
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
dash_pasos_restantes = 0
last_dash_step_tick = 0
DASH_STEP_MS = 60

# Crear enemigos iniciales
for _ in range(NUM_ENEMIGOS):
    enemigo = {
        "x": 0, "y": 0,
        "prev_x": None, "prev_y": None,
        "render_x": 0, "render_y": 0,
        "moving": False,
        "move_start_time": 0,
        "start_px": 0, "start_py": 0,
        "target_px": 0, "target_py": 0
    }
    enemigos.append(enemigo)
    respawnear_enemigo(enemigo)

# ------------------ Bucle principal ------------------
running = True
while running:
    dt = clock.tick(60)  # FPS máximo
    now = pygame.time.get_ticks()

    # Eventos
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if not juego_terminado and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            if event.key == pygame.K_UP:
                mover_jugador(0, -1)
            elif event.key == pygame.K_DOWN:
                mover_jugador(0, 1)
            elif event.key == pygame.K_LEFT:
                mover_jugador(-1, 0)
            elif event.key == pygame.K_RIGHT:
                mover_jugador(1, 0)
            elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                activar_carrera()

        # Clic en botones de game over
        if juego_terminado and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if btn_menu_rect is not None and btn_menu_rect.collidepoint(mx, my):
                return_to_menu()
            elif btn_retry_rect is not None and btn_retry_rect.collidepoint(mx, my):
                reiniciar_partida()
            elif btn_exit_rect is not None and btn_exit_rect.collidepoint(mx, my):
                pygame.quit()
                sys.exit()

    # Lógica de dash paso a paso
    if corriendo and dash_pasos_restantes > 0:
        if now - last_dash_step_tick >= DASH_STEP_MS:
            last_dash_step_tick = now
            dash_pasos_restantes -= 1
            dash_paso(dash_pasos_restantes)

    # Tick de enemigos (decisión de casilla)
    if not juego_terminado and now - last_enemy_tick >= ENEMY_TICK_MS:
        last_enemy_tick = now
        mover_enemigos_tick()

    # Actualizar animaciones
    actualizar_animacion_enemigos(now)
    actualizar_animacion_jugador(now)

    # Tick de timer
    if not juego_terminado and now - last_timer_tick >= 1000:
        last_timer_tick = now
        if tiempo_restante > 0:
            tiempo_restante -= 1
        if tiempo_restante <= 0:
            tiempo_restante = 0
            fin_partida_por_tiempo()

    # Dibujar
    screen.fill(COLOR_FONDO)
    dibujar_laberinto(screen)
    dibujar_enemigos(screen)
    dibujar_jugador(screen)
    dibujar_barra_energia(screen)
    dibujar_textos(screen)
    dibujar_leyenda(screen)
    dibujar_game_over(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
