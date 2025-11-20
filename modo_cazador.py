import pygame
import random
import sys
import mapa

# ------------------ Parámetros del laberinto ------------------
tamaño_celda = 40      # píxeles por casilla
COLUMNAS = 15
FILAS = 11

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

# --- NUEVO JUGADOR SUAVE ---
PLAYER_MOVE_DURATION_MS = 120  # duración animación al caminar

# ------------------ Crear laberinto ------------------
# 0 = camino, 1 = muro, 2 = salida
def crear_laberinto_basico():
    lab, sx, sy = mapa.generate_map(COLUMNAS, FILAS, start=(1,1))
    return lab, sx, sy

laberinto, salida_x, salida_y = crear_laberinto_basico()

def celda_es_caminable(x, y):
    return mapa.is_walkable_by_player(laberinto, x, y)

def distancia_manhattan(x1, y1, x2, y2):
    return abs(x1 - x2) + abs(y1 - y2)

# ------------------ Pygame init ------------------
pygame.init()
ancho = COLUMNAS * tamaño_celda
alto  = FILAS * tamaño_celda
screen = pygame.display.set_mode((ancho, alto))
pygame.display.setCaption = pygame.display.set_caption("Modo 2: Cazador - Pygame (sin imágenes)")

clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 20, bold=True)

# Colores
COLOR_FONDO   = (0, 0, 0)
COLOR_CAMINO  = (17, 25, 34)    # #111922
COLOR_MURO    = (51, 51, 102)   # #333366
COLOR_SALIDA  = (170, 153, 51)  # #AA9933
COLOR_JUGADOR = (0, 200, 200)   # cyan
COLOR_ENEMIGO = (200, 60, 60)   # rojo
COLOR_ENERGIA_LLENA = (0, 255, 0)
COLOR_ENERGIA_VACIA = (40, 40, 40)

# ------------------ Jugador (cazador) ------------------
jugador_x = 1
jugador_y = 1

# --- NUEVO JUGADOR SUAVE: posición de dibujado + animación ---
player_render_x = jugador_x * tamaño_celda
player_render_y = jugador_y * tamaño_celda
player_moving = False
player_move_start_time = 0
player_start_px = player_render_x
player_start_py = player_render_y
player_target_px = player_render_x
player_target_py = player_render_y
# --------------------------------------------------------------

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
            if (celda_es_caminable(x, y)
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

    # iniciar posición de renderizado en píxeles
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
    """IA híbrida para UN enemigo (misma lógica que en Tkinter)."""
    if juego_terminado:
        return

    ex, ey = enemigo["x"], enemigo["y"]

    dist_jugador = distancia_manhattan(ex, ey, jugador_x, jugador_y)

    candidatos = []
    for dx, dy in [(0,-1), (0,1), (-1,0), (1,0)]:
        nx = ex + dx
        ny = ey + dy
        if not celda_es_caminable(nx, ny):
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
    """Mueve al jugador una casilla si no hay muro."""
    global jugador_x, jugador_y, jugador_dir_dx, jugador_dir_dy
    global player_moving, player_move_start_time
    global player_start_px, player_start_py, player_target_px, player_target_py

    if juego_terminado or corriendo:
        return

    nuevo_x = jugador_x + dx
    nuevo_y = jugador_y + dy

    if not celda_es_caminable(nuevo_x, nuevo_y):
        return  # hay muro o fuera del mapa

    # --- NUEVO JUGADOR SUAVE: configurar animación ---
    player_start_px = jugador_x * tamaño_celda
    player_start_py = jugador_y * tamaño_celda
    player_target_px = nuevo_x * tamaño_celda
    player_target_py = nuevo_y * tamaño_celda
    player_move_start_time = pygame.time.get_ticks()
    player_moving = True
    # --------------------------------------------------

    jugador_x = nuevo_x
    jugador_y = nuevo_y
    jugador_dir_dx = dx
    jugador_dir_dy = dy

    comprobar_captura()

def dash_paso(pasos_restantes):
    """Implementación del dash paso a paso en Pygame."""
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

    # el dash sigue siendo instantáneo casilla a casilla
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

# ------------------ Dibujo ------------------
def dibujar_laberinto(surface):
    for fila in range(FILAS):
        for col in range(COLUMNAS):
            x = col * tamaño_celda
            y = fila * tamaño_celda
            celda = laberinto[fila][col]
            if celda == 1:
                color = COLOR_MURO
            elif celda == 2:
                color = COLOR_SALIDA
            else:
                color = COLOR_CAMINO
            pygame.draw.rect(surface, color, (x, y, tamaño_celda, tamaño_celda))

def dibujar_jugador(surface):
    # --- NUEVO JUGADOR SUAVE: usar render_x / render_y ---
    px = player_render_x
    py = player_render_y
    # ------------------------------------------------------
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
        ex = enemigo.get("render_x", enemigo["x"] * tamaño_celda)
        ey = enemigo.get("render_y", enemigo["y"] * tamaño_celda)
        rect = pygame.Rect(
            ex + margin,
            ey + margin,
            tamaño_celda - 2 * margin,
            tamaño_celda - 2 * margin
        )
        pygame.draw.ellipse(surface, COLOR_ENEMIGO, rect)
        pygame.draw.ellipse(surface, (255, 255, 255), rect, 2)

def dibujar_textos(surface):
    txt = font.render(f"Puntos: {puntos}", True, (255, 255, 255))
    rect = txt.get_rect(center=(ancho // 2, 20))
    surface.blit(txt, rect)

    txt2 = font.render(f"Tiempo: {tiempo_restante}s", True, (255, 255, 255))
    rect2 = txt2.get_rect(midright=(ancho - 10, 20))
    surface.blit(txt2, rect2)

def dibujar_barra_energia(surface):
    base_x = jugador_x * tamaño_celda
    base_y = jugador_y * tamaño_celda - 8  # encima de la cabeza
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
    if not juego_terminado:
        return
    overlay = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

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

    r1 = t1.get_rect(center=(ancho // 2, alto // 2 - 30))
    r2 = t2.get_rect(center=(ancho // 2, alto // 2))
    r3 = t3.get_rect(center=(ancho // 2, alto // 2 + 30))

    surface.blit(t1, r1)
    surface.blit(t2, r2)
    surface.blit(t3, r3)

# --- Animación suave enemigos ---
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

# --- NUEVO JUGADOR SUAVE ---
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
# -----------------------------------------------------

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
    dibujar_game_over(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
