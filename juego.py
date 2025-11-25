################################################################################################################################
#----------------------------------------------------------Imports-------------------------------------------------------------#
import os
import sys
import subprocess 
import pygame
import json
import modo_cazador
import modo_escapa
#---------------------------------------------------Inicialización y constantes--------------------------------------------------#
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCREEN = pygame.display.get_surface()
if SCREEN is None:
    pygame.init()
    SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

SIZE = SCREEN.get_size() 

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

# ----------------------------------------------------- Música de fondo ------------------------------------------------------#
try:
    music_path = os.path.join(BASE_DIR, "musica_menu.mp3")
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(0.35)  # volumen entre 0.0 y 1.0
        pygame.mixer.music.play(-1)          # -1 para loop infinito
except Exception as e:
    print("Error cargando música:", e)

# ---------------------------------------------- Variables globales de estado -------------------------------------------------#
player_name = ""        
registered = False       
message = ""            

in_cazador_menu = False
in_escapa_menu = False

PLAYERS_FILE = os.path.join(BASE_DIR, "players.json")

volver_a_menu_principal = False

################################################################################################################################
############################################### Historial simple de jugadores ##################################################
#---------------------------------------------------- Cargar jugadores -------------------------------------------------------#
def cargar_jugadores():
    try:
        if os.path.exists(PLAYERS_FILE):
            with open(PLAYERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

#---------------------------------------------------- Guardar jugadores -------------------------------------------------------#
def guardar_jugadores(name):
    if not name:
        return
    players = cargar_jugadores()
    if name not in players:
        players.append(name)
        try:
            with open(PLAYERS_FILE, "w", encoding="utf-8") as f:
                json.dump(players, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Error guardando players.json:", e)

#------------------------------------------------------- Clase Botón ---------------------------------------------------------#
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

btn_w, btn_h = 360, 56
gap = 18
start_y = SIZE[1]//2 - (btn_h*3 + gap*2)//2 + 40

################################################################################################################################
##################################################### Lógica de la UI ##########################################################
#--------------------------------------------------------- Callback cazador --------------------------------------------------#
def en_cazador():
    global message, in_cazador_menu, in_escapa_menu
    message = ""
    in_escapa_menu = False
    in_cazador_menu = True

#--------------------------------------------------------- Callback escapa ----------------------------------------------------#
def en_escapa():
    global message, in_cazador_menu, in_escapa_menu
    message = ""
    in_cazador_menu = False
    in_escapa_menu = True

#---------------------------------------------------------- Callback salir -----------------------------------------------------#
def salir():
    pygame.quit()
    sys.exit(0)

#--------------------------------------------------------- Volver a registro --------------------------------------------------#
def volver_a_registro():
    global registered, in_cazador_menu, in_escapa_menu, message, player_name
    player_name = ""
    registered = False         
    in_cazador_menu = False   
    in_escapa_menu = False
    message = ""

#--------------------------------------------------------- Volver a menú principal -------------------------------------------#
def marcar_volver_menu_principal():
    global volver_a_menu_principal
    volver_a_menu_principal = True

#----------------------------------------------- Resetear estado de cazador --------------------------------------------------#
def resetear_cazador_estado():
    try:
        modo_cazador.puntos = modo_cazador.PUNTOS_INICIALES
        modo_cazador.tiempo_restante = modo_cazador.TIEMPO_INICIAL
        modo_cazador.juego_terminado = False
        modo_cazador.energia_segmentos = modo_cazador.ENERGIA_MAX_SEGMENTOS
        modo_cazador.corriendo = False
        modo_cazador.jugador_dir_dx = 0
        modo_cazador.jugador_dir_dy = 0
    except AttributeError:
        pass

#----------------------------------------------- Resetear estado de escapa ---------------------------------------------------#
def resetear_escapa_estado():
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

################################################################################################################################
################################################### Callbacks de selección de modo #############################################
#----------------------------------------------- iniciar modo cazador fácil ------------------------------------------------#
def iniciar_cazador_facil():
    global message
    message = ""
    modo_cazador.COLUMNAS = 15
    modo_cazador.FILAS = 11
    modo_cazador.VEL_ENEMIGOS = 500 
    resetear_cazador_estado()
    modo_cazador.run()

#---------------------------------------------- iniciar modo cazador medio ------------------------------------------------#
def iniciar_cazador_medio():
    global message
    message = ""
    modo_cazador.COLUMNAS = 19
    modo_cazador.FILAS = 13
    modo_cazador.VEL_ENEMIGOS = 400
    resetear_cazador_estado()
    modo_cazador.run()

#--------------------------------------------- iniciar modo cazador difícil ------------------------------------------------#
def iniciar_cazador_dificil():
    global message
    message = ""
    modo_cazador.COLUMNAS = 23
    modo_cazador.FILAS = 15
    modo_cazador.VEL_ENEMIGOS = 300 
    resetear_cazador_estado()
    modo_cazador.run()

#-------------------------------------- Callback volver del submenú cazador ------------------------------------------------#
def en_cazador_volver():
    global in_cazador_menu, message
    in_cazador_menu = False
    message = ""

#----------------------------------------------- iniciar modo escapa fácil -------------------------------------------------#
def iniciar_escapa_facil():
    global message
    message = ""
    modo_escapa.VEL_BASE = 2   
    modo_escapa.TIEMPO_INICIAL = 30
    resetear_escapa_estado()
    modo_escapa.run()

#---------------------------------------------- iniciar modo escapa medio -------------------------------------------------#
def iniciar_escapa_medio():
    global message
    message = ""
    modo_escapa.VEL_BASE = 3
    modo_escapa.TIEMPO_INICIAL = 25
    resetear_escapa_estado()
    modo_escapa.run()

#--------------------------------------------- iniciar modo escapa difícil -------------------------------------------------#
def iniciar_escapa_dificil():
    global message
    message = ""
    modo_escapa.VEL_BASE = 4    
    modo_escapa.TIEMPO_INICIAL = 20
    resetear_escapa_estado()
    modo_escapa.run()

#-------------------------------------- Callback volver del submenú escapa -------------------------------------------------#
def en_escapa_volver():
    global in_escapa_menu, message
    in_escapa_menu = False
    message = ""

################################################################################################################################
############################################### Construcción de botones ########################################################
#---------------------------------------------------- Botones menú principal --------------------------------------------------#
buttons = [
    Button((SIZE[0]//2 - btn_w//2, start_y + i*(btn_h + gap), btn_w, btn_h), text, cb)
    for i, (text, cb) in enumerate([
        ("Modo Cazador (1)", lambda: en_cazador()),
        ("Modo Escapa (2)",  lambda: en_escapa()),
        ("Volver",      lambda: volver_a_registro())
    ])
]

#--------------------------------------------- Botones del SUBMENÚ de dificultad del cazador ----------------------------------#
cazador_buttons = [
    Button((SIZE[0]//2 - btn_w//2, start_y + i*(btn_h + gap), btn_w, btn_h), text, cb)
    for i, (text, cb) in enumerate([
        ("Fácil",   iniciar_cazador_facil),
        ("Medio",   iniciar_cazador_medio),
        ("Difícil", iniciar_cazador_dificil),
        ("Volver",  en_cazador_volver),
    ])
]

#---------------------------------------------- Botones del SUBMENÚ de dificultad del escapa -----------------------------------#
escapa_buttons = [
    Button((SIZE[0]//2 - btn_w//2, start_y + i*(btn_h + gap), btn_w, btn_h), text, cb)
    for i, (text, cb) in enumerate([
        ("Fácil",   iniciar_escapa_facil),
        ("Medio",   iniciar_escapa_medio),
        ("Difícil", iniciar_escapa_dificil),
        ("Volver",  en_escapa_volver),
    ])
]
#------------------------------------------------------ Área de input --------------------------------------------------------#
input_rect = pygame.Rect(120, 160, SIZE[0]-240, 44)
input_active = True
max_name_len = 20

################################################################################################################################
################################################ Dibujo de pantallas ###########################################################
#----------------------------------------------------- Dibujo de registro -----------------------------------------------------#
def dibujar_registro():
    SCREEN.fill(COL_BG)
    title = FONT.render("Registro obligatorio", True, COL_TEXT)
    SCREEN.blit(title, title.get_rect(center=(SIZE[0]//2, 80)))
    subtitle = SMALL.render("Introduce tu nombre de jugador (obligatorio) y pulsa Enter o Continuar", True, COL_TEXT)
    SCREEN.blit(subtitle, (SIZE[0]//2 - subtitle.get_width()//2, 110))

    pygame.draw.rect(SCREEN, COL_INPUT_BG, input_rect, border_radius=6)
    pygame.draw.rect(SCREEN, (100,100,100), input_rect, 2, border_radius=6)
    name_surf = FONT.render(
        player_name if player_name else "Escribe tu nombre...",
        True,
        COL_INPUT_TEXT if player_name else (120,120,120)
    )
    SCREEN.blit(name_surf, (input_rect.x + 8, input_rect.y + (input_rect.height - name_surf.get_height())//2))

    cont_btn = Button((SIZE[0]//2 - 140, input_rect.bottom + 20, 280, 48), "Continuar", lambda: enviar_registro())
    cont_btn.draw(SCREEN, enabled=(len(player_name.strip()) > 0))

    volver_btn = Button((SIZE[0]//2 - 170, input_rect.bottom + 80, 340, 48),"Volver al menú principal", marcar_volver_menu_principal)
    volver_btn.draw(SCREEN, enabled=True)

    # --------------------------------------- Historial de jugadores ----------------------------------------#
    players = cargar_jugadores()
    if players:
        hs = SMALL.render("Historial: " + ", ".join(players[-6:]), True, (200,200,200))
        SCREEN.blit(hs, (input_rect.x, input_rect.bottom + 80))

    if message:
        msg_s = SMALL.render(message, True, (220,220,220))
        SCREEN.blit(msg_s, (20, SIZE[1]-30))

#---------------------------------------------------- Dibujo de selección -----------------------------------------------------#
def dibujar_seleccion():
    SCREEN.fill(COL_BG)
    header = FONT.render(f"Jugador: {player_name}", True, COL_TEXT)
    SCREEN.blit(header, header.get_rect(center=(SIZE[0]//2, 48)))

    pygame.draw.rect(SCREEN, COL_PANEL, (40, 120, SIZE[0]-80, SIZE[1]-200), border_radius=10)

    if not in_cazador_menu and not in_escapa_menu:
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

#-------------------------------------------------- Enviar registro --------------------------------------------------------#
def enviar_registro():
    global registered, message
    name = player_name.strip()
    if not name:
        message = "El nombre es obligatorio."
        return
    guardar_jugadores(name)
    registered = True
    message = f"Registro completado: {name}"

#-------------------------------------------------- Manejo de eventos -------------------------------------------------------#
def handle_event(e):
    global player_name, input_active, message, registered, in_cazador_menu, in_escapa_menu
    if e.type == pygame.QUIT:
        pygame.quit()
        sys.exit(0)

    if not registered:
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit(0)
            elif e.key == pygame.K_RETURN:
                enviar_registro()
            elif e.key == pygame.K_BACKSPACE:
                player_name = player_name[:-1]
            else:
                ch = e.unicode
                if ch and len(player_name) < max_name_len and ch.isprintable():
                    player_name += ch
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            cont_btn_rect = pygame.Rect(SIZE[0]//2 - 140, input_rect.bottom + 20, 280, 48)
            if cont_btn_rect.collidepoint(e.pos) and len(player_name.strip()) > 0:
                enviar_registro()
            volver_btn_rect = pygame.Rect(SIZE[0]//2 - 140, input_rect.bottom + 80, 280, 48)
            if volver_btn_rect.collidepoint(e.pos):
                marcar_volver_menu_principal()
    else:
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if in_cazador_menu or in_escapa_menu:
                    in_cazador_menu = False
                    in_escapa_menu = False
                    message = ""
                else:
                    pygame.quit()
                    sys.exit(0)
            if e.key == pygame.K_1 and not in_escapa_menu:
                en_cazador()
            if e.key == pygame.K_2 and not in_cazador_menu:
                en_escapa()

        if in_cazador_menu:
            for b in cazador_buttons:
                b.handle(e, enabled=True)
        elif in_escapa_menu:
            for b in escapa_buttons:
                b.handle(e, enabled=True)
        else:
            for b in buttons:
                b.handle(e, enabled=True)

################################################################################################################################
################################################ Bucle principal ##############################################################
def main():
    global SCREEN, SIZE
    surf = pygame.display.get_surface()
    if surf is not None:
        SCREEN = surf
        SIZE = SCREEN.get_size()

    while True:
        for e in pygame.event.get():
            handle_event(e)
        if volver_a_menu_principal:
            return "menu_principal"
        if not registered:
            dibujar_registro()
        else:
            dibujar_seleccion()
        pygame.display.flip()
        CLOCK.tick(60)

if __name__ == "__main__":
    main()