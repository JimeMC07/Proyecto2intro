################################################################################################################################
#----------------------------------------------------------Imports-------------------------------------------------------------#
import pygame
import random
import sys
import os
import mapa

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COLUMNAS = 19
FILAS = 13

tamaño_celda = 40

# ------------------------------------------------------ Parámetros de enemigos -----------------------------------------------#
NUM_ENEMIGOS   = 3
VEL_ENEMIGOS  = 400
RADIO_PELIGRO  = 3
DURACION_MOVIMIENTO_ENEMIGOS = 300
# ------------------------------------------------------ Parámetros de puntuación ----------------------------------------------#
PUNTOS_INICIALES   = 800
PUNTOS_POR_CAPTURA = 200
PUNTOS_POR_ESCAPE  = 100
# ------------------------------------------------------ Parámetros de tiempo -----------------------------------------------#
TIEMPO_INICIAL = 20
# ------------------------------------------------------ Parámetros de energía ----------------------------------------------#
ENERGIA_MAX_SEGMENTOS = 4
PLAYER_MOVE_DURATION_MS = 120
DASH_STEP_MS = 60

# ------------------------------------------------------ Variables globales de estado ----------------------------------------#
puntos = PUNTOS_INICIALES
juego_terminado = False
tiempo_restante = TIEMPO_INICIAL
energia_segmentos = ENERGIA_MAX_SEGMENTOS
corriendo = False
jugador_dir_dx = 0
jugador_dir_dy = 0
jugador_x = 1
jugador_y = 1

player_render_x = 0
player_render_y = 0
player_moving = False
player_move_start_time = 0
player_start_px = 0
player_start_py = 0
player_target_px = 0
player_target_py = 0

enemigos = []

last_enemy_tick = 0
last_timer_tick = 0
dash_pasos_restantes = 0
last_dash_step_tick = 0

cuenta_regresiva = 3
cuenta_regresiva_activa = True
tick_previo_preconteo = 0

btn_menu_rect = None
btn_retry_rect = None
btn_exit_rect = None

screen = None
screen_width = 0
screen_height = 0
PANEL_W = 240
MARGEN_X = 40
MARGEN_Y = 40
ancho = 0
alto = 0
offset_x = 0
offset_y = 0

################################################################################################################################
################################################## Helpers y funciones #########################################################
#-------------------------------------Función para dibujar texto con salto de línea automático---------------------------------#
def texto_con_saltos(surface, text, x, y, font, color, max_width):
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

# ------------------------------------------------------- Crear laberinto -----------------------------------------------------#
def crear_laberinto_basico():
    lab, sx, sy = mapa.generate_map(COLUMNAS, FILAS, start=(1, 1))
    return lab, sx, sy

#-----------------------------------------------Comprobaciones de celdas caminables jugador------------------------------------#
def celda_es_caminable(x, y, laberinto_local):
    if not (0 <= y < FILAS and 0 <= x < COLUMNAS):
        return False
    v = laberinto_local[y][x]
    return v in (mapa.CAMINO, mapa.SALIDA, mapa.LIANA)

#-----------------------------------------------Comprobaciones de celdas caminables enemigo-------------------------------------#
def celda_es_caminable_enemigo(x, y, laberinto_local):
    if not (0 <= y < FILAS and 0 <= x < COLUMNAS):
        return False
    v = laberinto_local[y][x]
    return v in (mapa.CAMINO, mapa.SALIDA, mapa.TUNEL)

# -------------------------------------------------------- Distancia Manhattan ------------------------------------------------#
def distancia_manhattan(x1, y1, x2, y2):
    return abs(x1 - x2) + abs(y1 - y2)

#------------------------------------------------------- Posiciones enemigos --------------------------------------------------#
def posiciones_enemigos():
    return {(e["x"], e["y"]) for e in enemigos}

# ------------------------------------------------------- Respawnear enemigo --------------------------------------------------#
def respawnear_enemigo(enemigo, laberinto_local, salida_x, salida_y, jugador_x_local, jogador_y_local):
    posibles = []
    ocupadas = posiciones_enemigos() - {(enemigo["x"], enemigo["y"])}
    for y in range(FILAS):
        for x in range(COLUMNAS):
            if (celda_es_caminable_enemigo(x, y, laberinto_local)
                and (x, y) != (jugador_x_local, jogador_y_local)
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
    enemigo["render_x"] = enemigo["x"] * tamaño_celda
    enemigo["render_y"] = enemigo["y"] * tamaño_celda
    enemigo["moving"] = False
    enemigo["move_start_time"] = 0
    enemigo["start_px"] = enemigo["render_x"]
    enemigo["start_py"] = enemigo["render_y"]
    enemigo["target_px"] = enemigo["render_x"]
    enemigo["target_py"] = enemigo["render_y"]

# ----------------------------------------------------- Comprobar captura -----------------------------------------------------#
def comprobar_captura(jugador_x_local, jugador_y_local):
    global puntos, energia_segmentos
    if juego_terminado:
        return
    for enemigo in enemigos:
        if (jugador_x_local, jugador_y_local) == (enemigo["x"], enemigo["y"]):
            puntos += PUNTOS_POR_CAPTURA
            if energia_segmentos < ENERGIA_MAX_SEGMENTOS:
                energia_segmentos += 1
            respawnear_enemigo(enemigo, laberinto, salida_x, salida_y, jugador_x_local, jugador_y_local)

# ------------------------------------------------------ Comprobar salida ------------------------------------------------------#
def comprobar_salida():
    global puntos, juego_terminado
    if juego_terminado:
        return
    for enemigo in enemigos:
        if (enemigo["x"], enemigo["y"]) == (salida_x, salida_y):
            puntos -= PUNTOS_POR_ESCAPE
            respawnear_enemigo(enemigo, laberinto, salida_x, salida_y, jugador_x, jugador_y)
    if puntos <= 0 and not juego_terminado:
        puntos = 0
        game_over(motivo="puntos")

# ------------------------------------------------------- Mover enemigos ------------------------------------------------------#
def mover_un_enemigo(enemigo, jugador_x_local, jugador_y_local):
    if juego_terminado:
        return
    ex, ey = enemigo["x"], enemigo["y"]
    dist_jugador = distancia_manhattan(ex, ey, jugador_x_local, jugador_y_local)

    candidatos = []
    for dx, dy in [(0,-1), (0,1), (-1,0), (1,0)]:
        nx = ex + dx
        ny = ey + dy
        if not celda_es_caminable_enemigo(nx, ny, laberinto):
            continue
        if any((nx == e2["x"] and ny == e2["y"] and e2 is not enemigo) for e2 in enemigos):
            continue
        d_exit = distancia_manhattan(nx, ny, salida_x, salida_y)
        d_player = distancia_manhattan(nx, ny, jugador_x_local, jugador_y_local)
        candidatos.append((d_exit, d_player, nx, ny))

    if candidatos:
        if enemigo.get("prev_x") is not None and enemigo.get("prev_y") is not None:
            filtrados = [c for c in candidatos if not (c[2] == enemigo["prev_x"] and c[3] == enemigo["prev_y"])]
            if filtrados:
                candidatos = filtrados

        if dist_jugador <= RADIO_PELIGRO:
            candidatos.sort(key=lambda c: (-c[1], c[0]))
        else:
            candidatos.sort(key=lambda c: (c[0], -c[1]))

        _, _, mejor_x, mejor_y = candidatos[0]

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

# --------------------------------------------------- Mover enemigos tick ---------------------------------------------------#
def mover_enemigos_tick(jugador_x_local, jugador_y_local):
    if juego_terminado:
        return
    for enemigo in enemigos:
        mover_un_enemigo(enemigo, jugador_x_local, jugador_y_local)
    comprobar_captura(jugador_x_local, jugador_y_local)
    comprobar_salida()

################################################################################################################################
############################################## Animaciones fin de juego ########################################################
# ----------------------------------------------------- Game Over -------------------------------------------------------------#
def game_over(motivo="puntos"):
    global juego_terminado
    if juego_terminado:
        return
    juego_terminado = True

# --------------------------------------------------- Fin partida por tiempo --------------------------------------------------#
def fin_partida_por_tiempo():
    global juego_terminado
    if juego_terminado:
        return
    juego_terminado = True

# -------------------------------------------------------- Mover jugador ------------------------------------------------------#
def mover_jugador(dx, dy):
    global jugador_x, jugador_y, jugador_dir_dx, jugador_dir_dy
    global player_moving, player_move_start_time
    global player_start_px, player_start_py, player_target_px, player_target_py

    if juego_terminado or corriendo:
        return

    nuevo_x = jugador_x + dx
    nuevo_y = jugador_y + dy

    if not celda_es_caminable(nuevo_x, nuevo_y, laberinto):
        return

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

    comprobar_captura(jugador_x, jugador_y)

# -------------------------------------------------------- Dash jugador -------------------------------------------------------#
def dash_paso(pasos_restantes):
    global jugador_x, jugador_y, corriendo, dash_pasos_restantes

    if pasos_restantes <= 0 or juego_terminado:
        corriendo = False
        dash_pasos_restantes = 0
        return

    nx = jugador_x + jugador_dir_dx
    ny = jugador_y + jugador_dir_dy

    if not celda_es_caminable(nx, ny, laberinto):
        corriendo = False
        dash_pasos_restantes = 0
        return

    jugador_x = nx
    jugador_y = ny
    comprobar_captura(jugador_x, jugador_y)
    dash_pasos_restantes = pasos_restantes

def activar_carrera():
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
    dash_pasos_restantes = 4
################################################################################################################################
################################################### Reincio de partida #########################################################
# ----------------------------------------------------- Reiniciar partida ---------------------------------------------------#
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

    laberinto, salida_x, salida_y = crear_laberinto_basico()

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
        respawnear_enemigo(enemigo, laberinto, salida_x, salida_y, jugador_x, jugador_y)

    now = pygame.time.get_ticks()
    last_enemy_tick = now
    last_timer_tick = now
    dash_pasos_restantes = 0
    last_dash_step_tick = now

################################################################################################################################
################################################## Dibujo de elementos #########################################################
# ----------------------------------------------------- Dibujar laberinto ---------------------------------------------------#
def dibujar_laberinto(surface):
    for fila in range(FILAS):
        for col in range(COLUMNAS):
            x = offset_x + col * tamaño_celda
            y = offset_y + fila * tamaño_celda
            celda = laberinto[fila][col]
            if celda == mapa.MURO:
                color = (51, 51, 102)
            elif celda == mapa.SALIDA:
                color = (170, 153, 51)
            elif celda == mapa.LIANA:
                color = (34, 139, 34)
            elif celda == mapa.TUNEL:
                color = (120, 85, 40)
            else:
                color = (17, 25, 34)
            pygame.draw.rect(surface, color, (x, y, tamaño_celda, tamaño_celda))

# ------------------------------------------------- Dibujar panel lateral ----------------------------------------------------#
def dibujar_leyenda(surface, font_local):
    panel_w = PANEL_W - 24
    panel_h = alto - 20
    panel_x = offset_x + ancho + 12
    panel_y = offset_y + 10
    panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    pygame.draw.rect(surface, (18, 18, 18), panel, border_radius=8)
    pygame.draw.rect(surface, (80, 80, 80), panel, 2, border_radius=8)

    small = pygame.font.SysFont("consolas", 16)

    x = panel_x + 14
    y = panel_y + 14
    box_size = 18

    titulo = font_local.render("Modo 2: Cazador", True, (230, 230, 230))
    surface.blit(titulo, (x, y))
    y += 40

    items = [
        ((17,25,34), "Camino — pasan jugador y enemigos"),
        ((51,51,102), "Muro — bloquea el paso"),
        ((170,153,51), "Salida — los enemigos escapan aquí"),
        ((34,139,34), "Liana — solo jugador"),
        ((120,85,40), "Túnel — solo enemigos"),
    ]

    for col, label in items:
        box_y = y
        pygame.draw.rect(surface, col, (x, box_y, box_size, box_size))
        text_x = x + box_size + 10
        max_text_width = (panel_x + panel_w - 20) - text_x
        y = texto_con_saltos(surface, label, text_x, box_y, small, (230,230,230), max_text_width)
        y += 6

    y += 10
    max_text_width = panel_w - 40
    y = texto_con_saltos(surface, "Objetivo: atrapar enemigos antes de que crucen la salida.", x, y, small, (220,220,220), max_text_width)
    y = texto_con_saltos(surface, "Flechas: mover al cazador. Shift: correr 4 casillas.", x, y, small, (200,200,200), max_text_width)
    y = texto_con_saltos(surface, "La barra verde se vacía al correr y se rellena con enemigos capturados.", x, y, small, (200,200,200), max_text_width)
    y = texto_con_saltos(surface, "+200 puntos por captura. -100 puntos si un enemigo escapa.", x, y, small, (200,200,200), max_text_width)

# ----------------------------------------------------- Dibujar jugador ------------------------------------------------------#
def dibujar_jugador(surface):
    px = offset_x + player_render_x
    py = offset_y + player_render_y
    margin = 6
    rect = pygame.Rect(px + margin, py + margin, tamaño_celda - 2*margin, tamaño_celda - 2*margin)
    pygame.draw.ellipse(surface, (0,200,200), rect)
    pygame.draw.ellipse(surface, (255,255,255), rect, 2)

# ----------------------------------------------------- Dibujar enemigos -----------------------------------------------------#
def dibujar_enemigos(surface):
    margin = 6
    for enemigo in enemigos:
        ex = offset_x + enemigo.get("render_x", enemigo["x"] * tamaño_celda)
        ey = offset_y + enemigo.get("render_y", enemigo["y"] * tamaño_celda)
        rect = pygame.Rect(ex + margin, ey + margin, tamaño_celda - 2*margin, tamaño_celda - 2*margin)
        pygame.draw.ellipse(surface, (200,60,60), rect)
        pygame.draw.ellipse(surface, (255,255,255), rect, 2)

# ----------------------------------------------------- Dibujar textos ------------------------------------------------------#
def dibujar_textos(surface, font_local):
    center_x = offset_x + ancho // 2
    txt = font_local.render(f"Puntos: {puntos}", True, (255,255,255))
    rect = txt.get_rect(center=(center_x, offset_y + 20))
    surface.blit(txt, rect)
    txt2 = font_local.render(f"Tiempo: {tiempo_restante}s", True, (255,255,255))
    rect2 = txt2.get_rect(midright=(offset_x + ancho - 10, offset_y + 20))
    surface.blit(txt2, rect2)

# ---------------------------------------------------- Dibujar barra energía ---------------------------------------------------#
def dibujar_barra_energia(surface):
    base_x = offset_x + jugador_x * tamaño_celda
    base_y = offset_y + jugador_y * tamaño_celda - 8
    seg_width = tamaño_celda / ENERGIA_MAX_SEGMENTOS - 2
    for i in range(ENERGIA_MAX_SEGMENTOS):
        x0 = base_x + 2 + i * (seg_width + 1)
        y0 = base_y
        rect = pygame.Rect(x0, y0, seg_width, 6)
        color = (0,255,0) if i < energia_segmentos else (40,40,40)
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, (255,255,255), rect, 1)

# --------------------------------------------------- Dibujar pantalla Game Over ------------------------------------------------#
def dibujar_game_over(surface, font_local):
    global btn_menu_rect, btn_retry_rect, btn_exit_rect
    if not juego_terminado:
        return

    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0,0,0,180))
    surface.blit(overlay, (0,0))

    full_center_x = screen_width // 2
    center_y = screen_height // 2

    if tiempo_restante <= 0:
        titulo = "¡Tiempo agotado!"
        linea = "Fin de la partida"
        resumen = f"Puntos finales: {puntos}"
        color_titulo = (255,255,0)
    else:
        titulo = "GAME OVER"
        linea = "Te quedaste sin puntos"
        tiempo_jugado = TIEMPO_INICIAL - max(tiempo_restante, 0)
        min_j, seg_j = divmod(tiempo_jugado, 60)
        resumen = f"Tiempo: {min_j:02d}:{seg_j:02d}   Puntos: {puntos}"
        color_titulo = (255,0,0)

    t1 = font_local.render(titulo, True, color_titulo)
    t2 = font_local.render(linea, True, (255,255,255))
    t3 = font_local.render(resumen, True, (255,255,255))

    r1 = t1.get_rect(center=(full_center_x, center_y - 60))
    r2 = t2.get_rect(center=(full_center_x, center_y - 25))
    r3 = t3.get_rect(center=(full_center_x, center_y + 10))

    surface.blit(t1, r1)
    surface.blit(t2, r2)
    surface.blit(t3, r3)

    btn_w, btn_h = 200, 40
    espacio = 15
    start_y = center_y + 60

    btn_menu_rect  = pygame.Rect(full_center_x - btn_w // 2, start_y, btn_w, btn_h)
    btn_retry_rect = pygame.Rect(full_center_x - btn_w // 2, start_y + (btn_h + espacio), btn_w, btn_h)
    btn_exit_rect  = pygame.Rect(full_center_x - btn_w // 2, start_y + 2 * (btn_h + espacio), btn_w, btn_h)

    def dibujar_boton(rect, texto):
        pygame.draw.rect(surface, (60,60,60), rect, border_radius=8)
        pygame.draw.rect(surface, (200,200,200), rect, 2, border_radius=8)
        txt = font_local.render(texto, True, (255,255,255))
        txt_rect = txt.get_rect(center=rect.center)
        surface.blit(txt, txt_rect)

    dibujar_boton(btn_menu_rect, "Volver al menú")
    dibujar_boton(btn_retry_rect, "Reiniciar")
    dibujar_boton(btn_exit_rect, "Salir")

##################################################################################################################################
############################################## Animaciones de movimiento #########################################################
# ----------------------------------------------- Actualizar animación enemigos ------------------------------------------------#
def actualizar_animacion_enemigos(now):
    for enemigo in enemigos:
        if not enemigo.get("moving", False):
            enemigo["render_x"] = enemigo["x"] * tamaño_celda
            enemigo["render_y"] = enemigo["y"] * tamaño_celda
            continue
        t = (now - enemigo["move_start_time"]) / DURACION_MOVIMIENTO_ENEMIGOS
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

# ------------------------------------------------- Actualizar animación jugador ------------------------------------------------#
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

##################################################################################################################################
######################################################### Main loop ##############################################################
#--------------------------------------------------------- Run --------------------------------------------------------------#
def run():
    global screen, screen_width, screen_height
    global ancho, alto, offset_x, offset_y, tamaño_celda
    global laberinto, salida_x, salida_y
    global jugador_x, jugador_y
    global player_render_x, player_render_y, player_moving
    global last_enemy_tick, last_timer_tick, dash_pasos_restantes, last_dash_step_tick
    global puntos, tiempo_restante, juego_terminado, energia_segmentos
    global corriendo, jugador_dir_dx, jugador_dir_dy
    global cuenta_regresiva, cuenta_regresiva_activa, tick_previo_preconteo

    screen = pygame.display.get_surface()
    if screen is None:
        pygame.init()
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    screen_width, screen_height = screen.get_size()
    pygame.display.set_caption("Modo 2: Cazador - Pygame (sin imágenes)")

    try:
        music_path = os.path.join(BASE_DIR, "musica_menu.mp3")
        if os.path.exists(music_path):
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)
    except Exception:
        pass

    font_local = pygame.font.SysFont("consolas", 20, bold=True)
    big_font = pygame.font.SysFont("consolas", 96, bold=True)

    usable_width  = screen_width - PANEL_W - 2 * MARGEN_X
    usable_height = screen_height - 2 * MARGEN_Y
    tamaño_celda = min(usable_width // COLUMNAS, usable_height // FILAS)
    if tamaño_celda < 10:
        tamaño_celda = 10

    ancho = COLUMNAS * tamaño_celda
    alto  = FILAS * tamaño_celda
    offset_x = (screen_width - (ancho + PANEL_W)) // 2
    offset_y = (screen_height - alto) // 2

    laberinto, salida_x, salida_y = crear_laberinto_basico()

    jugador_x = 1
    jugador_y = 1
    player_render_x = jugador_x * tamaño_celda
    player_render_y = jugador_y * tamaño_celda
    player_moving = False

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
        respawnear_enemigo(enemigo, laberinto, salida_x, salida_y, jugador_x, jugador_y)

    clock = pygame.time.Clock()
    now = pygame.time.get_ticks()
    last_enemy_tick = now
    last_timer_tick = now
    dash_pasos_restantes = 0
    last_dash_step_tick = now

    cuenta_regresiva = 3
    cuenta_regresiva_activa = True
    tick_previo_preconteo = now

    running = True
    while running:
        dt = clock.tick(60)
        now = pygame.time.get_ticks()

        #---------------------------------------- Manejo de eventos ------------------------------------------------#
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False  

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            if (not juego_terminado 
                and not cuenta_regresiva_activa 
                and event.type == pygame.KEYDOWN):

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

            if juego_terminado and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if btn_menu_rect is not None and btn_menu_rect.collidepoint(mx, my):
                    running = False
                elif btn_retry_rect is not None and btn_retry_rect.collidepoint(mx, my):
                    reiniciar_partida()
                elif btn_exit_rect is not None and btn_exit_rect.collidepoint(mx, my):
                    pygame.quit()
                    sys.exit()

        #---------------------------------------- Lógica de cuenta regresiva ------------------------------------------------#
        if cuenta_regresiva_activa:
            if now - tick_previo_preconteo >= 1000:  
                tick_previo_preconteo = now
                cuenta_regresiva -= 1
                if cuenta_regresiva < 0:
                    cuenta_regresiva_activa = False
                    last_enemy_tick = now
                    last_timer_tick = now

        if corriendo and dash_pasos_restantes > 0 and not cuenta_regresiva_activa:
            if now - last_dash_step_tick >= DASH_STEP_MS:
                last_dash_step_tick = now
                dash_pasos_restantes -= 1
                dash_paso(dash_pasos_restantes)

        if (not juego_terminado 
            and not cuenta_regresiva_activa 
            and now - last_enemy_tick >= VEL_ENEMIGOS):

            last_enemy_tick = now
            mover_enemigos_tick(jugador_x, jugador_y)

        actualizar_animacion_enemigos(now)
        actualizar_animacion_jugador(now)
        #---------------------------------------- Lógica de temporizador ------------------------------------------------#
        if (not juego_terminado 
            and not cuenta_regresiva_activa 
            and now - last_timer_tick >= 1000):

            last_timer_tick = now
            if tiempo_restante > 0:
                tiempo_restante -= 1
            if tiempo_restante <= 0:
                tiempo_restante = 0
                fin_partida_por_tiempo()

        screen.fill((0,0,0))
        dibujar_laberinto(screen)
        dibujar_enemigos(screen)
        dibujar_jugador(screen)
        dibujar_barra_energia(screen)
        dibujar_textos(screen, font_local)
        dibujar_leyenda(screen, font_local)
        dibujar_game_over(screen, font_local)

        if cuenta_regresiva_activa:
            overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            if cuenta_regresiva >= 0:
                txt_surf = big_font.render(str(cuenta_regresiva), True, (255, 255, 255))
                rect = txt_surf.get_rect(center=(screen_width // 2, screen_height // 2))
                screen.blit(txt_surf, rect)

        pygame.display.flip()

    return