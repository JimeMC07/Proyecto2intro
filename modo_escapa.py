################################################################################################################################
# --------------------------------------------------------- IMPORTS -----------------------------------------------------------#
import pygame
import random
import sys
import os
import json
import mapa
# ------------------------------------------------------ RUTAS Y DIRECTORIOS ---------------------------------------------------#
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCORES_FILE = os.path.join(BASE_DIR, "scores.json")
nombre_jugador_escapa = ""
nivel_actual_escapa = 1  

################################################################################################################################
############################################ PARÁMETROS GENERALES DEL LABERINTO Y JUEGO ########################################
COLUMNAS = 19
FILAS = 13
tamaño_celda = 40

# -------------------------------------------------- PARÁMETROS DE ENEMIGOS --------------------------------------------------#
NUM_ENEMIGOS   = 3
VEL_ENEMIGOS  = 400             
RADIO_PELIGRO  = 99             
DURACION_MOVIMIENTO_ENEMIGOS = 300     

PUNTOS_INICIALES = 0            

# --------------------------------------------------- PARÁMETROS DE TRAMPAS --------------------------------------------------#
MAX_TRAPS = 3                    
RECARGA_TRAMPAS = 5000         
ENEMIGO_RESPAWN = 10000         
BONUS_POR_TRAMPA = 150                 

TIEMPO_INICIAL = 60             

PLAYER_MOVE_DURATION_MS = 120   
ENERGIA_MAX_SEGMENTOS = 4       
DASH_STEP_MS = 60                
################################################################################################################################
############################################### ESTADO GLOBAL (SE REINICIALIZA EN run) #########################################
puntos = PUNTOS_INICIALES
juego_terminado = False
victoria = False
tiempo_restante = TIEMPO_INICIAL

#-------------------------------------------------- ENERGÍA Y CARRERA (DASH) --------------------------------------------------#
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

#---------------------------------------------------- LABERINTO Y SALIDA ------------------------------------------------------#
trampas = []                    
ultima_trampa = -10_000_000   
mensaje = ""                   

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

#-------------------------------------------------- DIMENSIONES DE PANTALLA ---------------------------------------------------#
screen = None
screen_width = 0
screen_height = 0
PANEL_W = 240
MARGEN_X = 40
MARGEN_Y = 40
ancho = 0      
alto = 0       
offset_x = 0   # desplazamiento horizontal del laberinto en pantalla
offset_y = 0   # desplazamiento vertical del laberinto en pantalla


COLOR_FONDO   = (0, 0, 0)
COLOR_CAMINO  = (17, 25, 34)
COLOR_MURO    = (51, 51, 102)
COLOR_SALIDA  = (170, 153, 51)
COLOR_JUGADOR = (0, 200, 200)
COLOR_ENEMIGO = (200, 60, 60)
COLOR_TRAMPA    = (200, 20, 200)
COLOR_ENERGIA_LLENA = (0, 255, 0)
COLOR_ENERGIA_VACIA = (40, 40, 40)

################################################################################################################################
####################################################### HELPERS GENERALES ######################################################
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

# ----------------------------------------------------- Creación del laberinto -------------------------------------------------#
def crear_laberinto_basico():
    lab, sx, sy = mapa.generate_map(COLUMNAS, FILAS, start=(1,1))
    return lab, sx, sy

#------------------------------------------------Calculo de distancia Manhattan-------------------------------------------------#
def distancia_manhattan(x1, y1, x2, y2):
    return abs(x1 - x2) + abs(y1 - y2)

#-----------------------------------------------Comprobaciones de celdas caminables jugador------------------------------------#
def celda_es_caminable(x, y):
    if not (0 <= y < FILAS and 0 <= x < COLUMNAS):
        return False
    v = laberinto[y][x]
    return v in (mapa.CAMINO, mapa.SALIDA, mapa.TUNEL)

#----------------------------------------------Comprobaciones de celdas caminables enemigo-------------------------------------#
def celda_es_caminable_para_enemigo(x, y):
    if not (0 <= y < FILAS and 0 <= x < COLUMNAS):
        return False
    v = laberinto[y][x]
    return v in (mapa.CAMINO, mapa.SALIDA, mapa.LIANA)

################################################################################################################################
####################################################### ENEMIGOS Y TRAMPAS #####################################################
#------------------------------------------------Posiciones de enemigos vivos--------------------------------------------------#
def posiciones_enemigos():
    return {(e["x"], e["y"]) for e in enemigos if e.get("alive", True)}

#----------------------------------------------------- Reaparecer enemigo -----------------------------------------------------#
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

#-------------------------------------------------- Colocar trampa cerca jugador ---------------------------------------------#
def place_trap_near_player(now):
    global ultima_trampa, mensaje
    if len(trampas) >= MAX_TRAPS:
        mensaje = "Máximo de trampas activo."
        return

    if now - ultima_trampa < RECARGA_TRAMPAS:
        remaining = (RECARGA_TRAMPAS - (now - ultima_trampa))//1000 + 1
        mensaje = f"Trampa en cooldown ({remaining}s)"
        return

    #---------------------------------Busca casillas alrededor del jugador (arriba, abajo, izq, der)---------------------------#
    for dx, dy in [(1,0),(-1,0),(0,-1),(0,1)]:
        tx = jugador_x + dx
        ty = jugador_y + dy
        if 0 <= tx < COLUMNAS and 0 <= ty < FILAS:
            if (not trap_at(tx, ty)
                and celda_es_caminable_para_enemigo(tx, ty)
                and (tx, ty) != (salida_x, salida_y)
                and (tx, ty) != (jugador_x, jugador_y)
                and (tx, ty) not in posiciones_enemigos()):
                trampas.append({"x":tx,"y":ty,"placed_time":now})
                ultima_trampa = now
                mensaje = f"Trampa colocada en ({tx},{ty})"
                return

    mensaje = "No hay casilla válida cerca para colocar trampa."

#----------------------------------------------------- Ver trampa en casilla --------------------------------------------------#
def trap_at(x, y):
    for t in trampas:
        if t["x"] == x and t["y"] == y:
            return t
    return None

#-------------------------------------------------- Matar enemigo en trampa --------------------------------------------------#
def enemigo_en_trampa(enemigo, now):
    global puntos, mensaje
    if not enemigo.get("alive", True):
        return False

    t = trap_at(enemigo["x"], enemigo["y"])
    if t is not None:
        try:
            trampas.remove(t)
        except ValueError:
            pass

        enemigo["alive"] = False
        enemigo["dead_time"] = now
        puntos += BONUS_POR_TRAMPA
        mensaje = f"Eliminado enemigo (+{BONUS_POR_TRAMPA})"
        return True

    return False

###############################################################################################################################
########################################### PUNTAJES MODO ESCAPA (scores.json) ################################################
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
        print("Error cargando scores.json en modo_escapa:", e)
        return {"escapa": [], "cazador": []}

#------------------------------------------------- Registrar puntaje escapa --------------------------------------------------#
def registrar_puntaje_escapa(nombre, puntaje):
    data = cargar_puntajes()
    if "escapa" not in data:
        data["escapa"] = []

    data["escapa"].append({"name": nombre, "score": puntaje})
    data["escapa"] = sorted(
        data["escapa"],
        key=lambda e: e.get("score", 0),
        reverse=True
    )[:5]

    try:
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error guardando scores.json en modo_escapa:", e)

#-------------------------------------------------- Registrar puntaje final --------------------------------------------------#
def registrar_puntaje_final():
    if nombre_jugador_escapa:
        registrar_puntaje_escapa(nombre_jugador_escapa, puntos)

#--------------------------------------------------- Calcular bonus por tiempo --------------------------------------------------#
def calcular_bonus_tiempo():
    base_mult = 10  
    nivel_mult = 1.0 + 0.5 * (nivel_actual_escapa - 1)  
    if nivel_mult < 1.0:
        nivel_mult = 1.0
    segundos = max(tiempo_restante, 0)
    return int(segundos * base_mult * nivel_mult)

###############################################################################################################################
######################################################### IA DE LOS ENEMIGOS ##################################################
#----------------------------------------------------- Mover un enemigo ------------------------------------------------------#
def mover_un_enemigo(enemigo):
    if juego_terminado:
        return
    if not enemigo.get("alive", True):
        return

    ex, ey = enemigo["x"], enemigo["y"]
    candidatos = []

    #------------------------------------Evalúa casillas adyacentes caminables------------------------------------------------#
    for dx, dy in [(0,-1),(0,1),(-1,0),(1,0)]:
        nx = ex + dx
        ny = ey + dy
        if not celda_es_caminable_para_enemigo(nx, ny):
            continue

        #-------------------------------Evita casillas ocupadas por otros enemigos--------------------------------------------#
        if any((nx == e2["x"] and ny == e2["y"] and e2 is not enemigo and e2.get("alive", True)) for e2 in enemigos):
            continue

        d_player = distancia_manhattan(nx, ny, jugador_x, jugador_y)
        d_exit = distancia_manhattan(nx, ny, salida_x, salida_y)
        candidatos.append((d_player, d_exit, nx, ny))

    if candidatos:
        if enemigo.get("prev_x") is not None and enemigo.get("prev_y") is not None:
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

#-------------------------------------------------- Mover enemigos en tick ---------------------------------------------------#
def mover_enemigos_tick(now):
    if juego_terminado:
        return

    for enemigo in enemigos:
        mover_un_enemigo(enemigo)

    for enemigo in enemigos:
        if not enemigo.get("alive", True):
            continue
        if enemigo_en_trampa(enemigo, now):
            continue

    comprobar_captura()

###############################################################################################################################
############################################### COMPROBACIONES DE ESTADO DEL JUGADOR ##########################################
#-------------------------------------------------- Comprobar captura jugador ------------------------------------------------#
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

#-------------------------------------------------- Comprobar llegada a salida ------------------------------------------------#
def comprobar_llegada_salida():
    global juego_terminado, victoria, puntos
    if juego_terminado:
        return
    if (jugador_x, jugador_y) == (salida_x, salida_y):
        juego_terminado = True
        victoria = True

        # Bonus por tiempo restante, escalado por nivel
        bonus_tiempo = calcular_bonus_tiempo()
        puntos += bonus_tiempo

        registrar_puntaje_final()
        return

###############################################################################################################################
################################################## MOVIMIENTO DEL JUGADOR #####################################################
#----------------------------------------------------- Mover jugador ---------------------------------------------------------#
def mover_jugador(dx, dy):
    global jugador_x, jugador_y
    global player_moving, player_move_start_time
    global player_start_px, player_start_py, player_target_px, player_target_py
    global jugador_dir_dx, jugador_dir_dy

    if juego_terminado or corriendo:
        return

    nx = jugador_x + dx
    ny = jugador_y + dy

    #.------------------------------Comprueba si la celda destino es caminable-----------------------------------------------#
    if not celda_es_caminable(nx, ny):
        return

    player_start_px = jugador_x * tamaño_celda
    player_start_py = jugador_y * tamaño_celda
    player_target_px = nx * tamaño_celda
    player_target_py = ny * tamaño_celda
    player_move_start_time = pygame.time.get_ticks()
    player_moving = True

    jugador_x = nx
    jugador_y = ny

    jugador_dir_dx = dx
    jugador_dir_dy = dy

    comprobar_llegada_salida()
    comprobar_captura()

#----------------------------------------------------- Paso de carrera -----------------------------------------------------#
def dash_paso(pasos_restantes):
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
    comprobar_llegada_salida()
    comprobar_captura()
    dash_pasos_restantes = pasos_restantes

#---------------------------------------------------- Activar carrera -------------------------------------------------------#
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

###############################################################################################################################
####################################################### REINICIO DE LA PARTIDA ################################################
#---------------------------------------------------- Reiniciar partida ------------------------------------------------------#
def reiniciar_partida():
    global puntos, tiempo_restante, juego_terminado, victoria
    global energia_segmentos, corriendo, jugador_dir_dx, jugador_dir_dy
    global laberinto, salida_x, salida_y
    global jugador_x, jugador_y
    global player_render_x, player_render_y, player_moving
    global player_move_start_time, player_start_px, player_start_py
    global player_target_px, player_target_py
    global enemigos, trampas, ultima_trampa, mensaje
    global last_enemy_tick, last_timer_tick
    global dash_pasos_restantes, last_dash_step_tick
    global pre_count, pre_count_active, pre_last_tick

    puntos = PUNTOS_INICIALES
    tiempo_restante = TIEMPO_INICIAL
    juego_terminado = False
    victoria = False

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

    trampas.clear()
    ultima_trampa = -10_000_000
    mensaje = ""

    enemigos.clear()
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

    now = pygame.time.get_ticks()
    last_enemy_tick = now
    last_timer_tick = now
    dash_pasos_restantes = 0
    last_dash_step_tick = now

    pre_count = 3
    pre_count_active = True
    pre_last_tick = now

#-------------------------------------------------- Volver al menú principal --------------------------------------------------#
def return_to_menu():
    global running
    running = False

###############################################################################################################################
###################################################### DIBUJADO EN PANTALLA ###################################################
#----------------------------------------------------- Dibujar laberinto -----------------------------------------------------#
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

#-------------------------------------------------- Dibujar leyenda lateral --------------------------------------------------#
def dibujar_leyenda(surface, font_local):
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

    titulo = font_local.render("Modo 1: Escapa", True, (230,230,230))
    surface.blit(titulo, (x, y))
    y += 40

    items = [
        (COLOR_CAMINO, "Camino — transitable por jugador y enemigos"),
        (COLOR_MURO,   "Muro — bloqueado"),
        (COLOR_SALIDA, "Salida — objetivo del jugador"),
        ((34,139,34),  "Liana — solo enemigos"),
        ((120,85,40),  "Túnel — solo jugador"),
        (COLOR_TRAMPA,   "Trampa — coloca con T o SPACE"),
    ]

    for col, label in items:
        box_y = y
        pygame.draw.rect(surface, col, (x, box_y, box_size, box_size))
        text_x = x + box_size + 10
        max_text_width = (panel_x + panel_w - 20) - text_x
        y = texto_con_saltos(surface, label, text_x, box_y, small, (230,230,230), max_text_width)
        y += 6

    text_x = panel_x + 14
    max_text_width = panel_w - 40
    y_bottom = panel_y + panel_h - 140
    y_bottom = texto_con_saltos(surface, "Colocar trampa: T o SPACE", text_x, y_bottom, small, (220,220,220), max_text_width)
    y_bottom = texto_con_saltos(surface, f"Máx {MAX_TRAPS} trampas, CD: {RECARGA_TRAMPAS//1000}s", text_x, y_bottom, small, (200,200,200), max_text_width)
    y_bottom = texto_con_saltos(surface, "Cazadores reaparecen +10s tras morir", text_x, y_bottom, small, (200,200,200), max_text_width)

#----------------------------------------------------- Dibujar trampas ------------------------------------------------------#
def dibujar_traps(surface):
    for t in trampas:
        rx = offset_x + t["x"] * tamaño_celda
        ry = offset_y + t["y"] * tamaño_celda
        margin = tamaño_celda // 4
        rect = pygame.Rect(rx + margin, ry + margin, tamaño_celda - 2*margin, tamaño_celda - 2*margin)
        pygame.draw.rect(surface, COLOR_TRAMPA, rect)

#----------------------------------------------------- Dibujar jugador -------------------------------------------------------#
def dibujar_jugador(surface):
    px = offset_x + player_render_x
    py = offset_y + player_render_y
    margin = 6
    rect = pygame.Rect(px + margin, py + margin, tamaño_celda - 2*margin, tamaño_celda - 2*margin)
    pygame.draw.ellipse(surface, COLOR_JUGADOR, rect)
    pygame.draw.ellipse(surface, (255,255,255), rect, 2)

#--------------------------------------------------- Dibujar barra de energía -------------------------------------------------#
def dibujar_barra_energia(surface):
    base_x = offset_x + jugador_x * tamaño_celda
    base_y = offset_y + jugador_y * tamaño_celda - 8
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
        pygame.draw.rect(surface, (255,255,255), rect, 1)

#--------------------------------------------------- Dibujar enemigos vivos --------------------------------------------------#
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

#----------------------------------------------------- Dibujar textos -------------------------------------------------------#
def dibujar_textos(surface, font_local):
    txt = font_local.render(f"Tiempo: {tiempo_restante}s", True, (255,255,255))
    surface.blit(txt, (offset_x + 10, offset_y + 10))

    txt2 = font_local.render(f"Puntos: {puntos}", True, (255,255,255))
    surface.blit(txt2, (offset_x + ancho - txt2.get_width() - 10, offset_y + 10))

    now = pygame.time.get_ticks()
    cooldown_left = max(0, (RECARGA_TRAMPAS - (now - ultima_trampa))//1000)
    tinfo = font_local.render(f"Trampas: {len(trampas)}/{MAX_TRAPS}  CD: {cooldown_left}s", True, (255,255,255))
    surface.blit(tinfo, (offset_x + 10, offset_y + alto - 28))

#-------------------------------------------------- Dibujar resultado final --------------------------------------------------#
def dibujar_resultado(surface, font_local):
    global btn_menu_rect, btn_retry_rect, btn_exit_rect

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

    t1 = font_local.render(titulo, True, color_t)
    t2 = font_local.render(linea, True, (255,255,255))
    t3 = font_local.render(resumen, True, (255,255,255))

    r1 = t1.get_rect(center=(full_center_x, center_y - 60))
    r2 = t2.get_rect(center=(full_center_x, center_y - 25))
    r3 = t3.get_rect(center=(full_center_x, center_y + 10))

    surface.blit(t1, r1)
    surface.blit(t2, r2)
    surface.blit(t3, r3)

    btn_w, btn_h = 220, 42
    espacio = 15
    start_y = center_y + 60

    btn_menu_rect  = pygame.Rect(full_center_x - btn_w // 2, start_y, btn_w, btn_h)
    btn_retry_rect = pygame.Rect(full_center_x - btn_w // 2, start_y + (btn_h + espacio), btn_w, btn_h)
    btn_exit_rect  = pygame.Rect(full_center_x - btn_w // 2, start_y + 2 * (btn_h + espacio), btn_w, btn_h)

    def dibujar_boton(rect, texto):
        pygame.draw.rect(surface, (60, 60, 60), rect, border_radius=8)
        pygame.draw.rect(surface, (200, 200, 200), rect, 2, border_radius=8)
        txt = font_local.render(texto, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=rect.center)
        surface.blit(txt, txt_rect)

    dibujar_boton(btn_menu_rect,  "Volver al menú")
    dibujar_boton(btn_retry_rect, "Reiniciar partida")
    dibujar_boton(btn_exit_rect,  "Salir (ESC)")

###############################################################################################################################
########################################################## ANIMACIONES ########################################################
#------------------------------------------------ Actualizar animación enemigos ----------__----------------------------------#
def actualizar_animacion_enemigos(now):
    for enemigo in enemigos:
        if not enemigo.get("alive", True):
            continue

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

#------------------------------------------------- Actualizar animación jugador ------------------------------------------------#
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

###############################################################################################################################
################################################ BUCLE PRINCIPAL: run() #######################################################
#----------------------------------------------------- Bucle principal -------------------------------------------------------#
def run(nombre_jugador="", nivel=1):
    global screen, screen_width, screen_height
    global ancho, alto, offset_x, offset_y, tamaño_celda
    global laberinto, salida_x, salida_y
    global jugador_x, jugador_y
    global player_render_x, player_render_y, player_moving
    global last_enemy_tick, last_timer_tick, dash_pasos_restantes, last_dash_step_tick
    global pre_count, pre_count_active, pre_last_tick
    global puntos, tiempo_restante, juego_terminado, victoria, energia_segmentos
    global corriendo, jugador_dir_dx, jugador_dir_dy
    global mensaje, ultima_trampa
    global running
    global nombre_jugador_escapa, nivel_actual_escapa

    nombre_jugador_escapa = nombre_jugador
    nivel_actual_escapa = nivel

    #--------------------------------Inicialización de Pygame y pantalla completa--------------------------------------------#
    screen = pygame.display.get_surface()
    if screen is None:
        pygame.init()
        screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)

    screen_width, screen_height = screen.get_size()
    pygame.display.set_caption("Modo 1: Escapa - Pygame (sin imágenes)")

    #------------------------------Inicialización de música de fondo---------------------------------------------------------#
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

    usable_width  = screen_width  - PANEL_W - 2 * MARGEN_X
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

    trampas.clear()
    ultima_trampa = -10_000_000
    mensaje = ""

    enemigos.clear()
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

    clock = pygame.time.Clock()
    now = pygame.time.get_ticks()
    last_enemy_tick = now
    last_timer_tick = now
    dash_pasos_restantes = 0
    last_dash_step_tick = now
    pre_count = 3
    pre_count_active = True
    pre_last_tick = now

    running = True
    while running:
        dt = clock.tick(60) 
        now = pygame.time.get_ticks()

        # --------------------------------------------------- EVENTOS ------------------------------------------------------#
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if juego_terminado:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if btn_menu_rect is not None and btn_menu_rect.collidepoint(mx, my):
                        running = False
                    elif btn_retry_rect is not None and btn_retry_rect.collidepoint(mx, my):
                        reiniciar_partida()
                    elif btn_exit_rect is not None and btn_exit_rect.collidepoint(mx, my):
                        pygame.quit()
                        sys.exit()
                continue

            if not pre_count_active and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_UP:
                    mover_jugador(0, -1)
                elif event.key == pygame.K_DOWN:
                    mover_jugador(0, 1)
                elif event.key == pygame.K_LEFT:
                    mover_jugador(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    mover_jugador(1, 0)
                elif event.key in (pygame.K_t, pygame.K_SPACE):
                    place_trap_near_player(now)
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    activar_carrera()

        # -------------------------------------------------- LÓGICA DE DASH -----------------------------------------------#
        if corriendo and dash_pasos_restantes > 0 and not juego_terminado and not pre_count_active:
            if now - last_dash_step_tick >= DASH_STEP_MS:
                last_dash_step_tick = now
                dash_pasos_restantes -= 1
                dash_paso(dash_pasos_restantes)

        # ---------------------------------------------- COUNTDOWN PREPARTIDA ---------------------------------------------#
        if pre_count_active:
            if now - pre_last_tick >= 1000:
                pre_last_tick = now
                pre_count -= 1
                if pre_count < 0:
                    pre_count_active = False
                    last_enemy_tick = now
                    last_timer_tick = now

        # ---------------------------------------------- MOVIMIENTO ENEMIGOS ---------------------------------------------#
        if not juego_terminado and not pre_count_active and now - last_enemy_tick >= VEL_ENEMIGOS:
            last_enemy_tick = now
            mover_enemigos_tick(now)

        for enemigo in enemigos:
            if not enemigo.get("alive", True) and enemigo.get("dead_time") is not None:
                if now - enemigo["dead_time"] >= ENEMIGO_RESPAWN:
                    respawnear_enemigo(enemigo)

        actualizar_animacion_enemigos(now)
        actualizar_animacion_jugador(now)

        if not juego_terminado and not pre_count_active and now - last_timer_tick >= 1000:
            last_timer_tick = now
            if tiempo_restante > 0:
                tiempo_restante -= 1
            if energia_segmentos < ENERGIA_MAX_SEGMENTOS:
                energia_segmentos += 1
            if tiempo_restante <= 0:
                tiempo_restante = 0
                juego_terminado = True
                victoria = False
                # IMPORTANTE: no registrar puntaje al perder por tiempo

        # ------------------------------------------------ DIBUJADO EN PANTALLA ----------------------------------------------#
        screen.fill(COLOR_FONDO)
        dibujar_laberinto(screen)
        dibujar_traps(screen)
        dibujar_enemigos(screen)
        dibujar_jugador(screen)
        dibujar_barra_energia(screen)
        dibujar_textos(screen, font_local)
        dibujar_resultado(screen, font_local)
        dibujar_leyenda(screen, font_local)

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
    return
