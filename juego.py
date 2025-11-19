import os
import sys
import subprocess  # Para lanzar otros scripts sin bloquear la UI
import pygame

# -------------------------
# Configuración / Constantes
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

pygame.init()
SIZE = (640, 400)
SCREEN = pygame.display.set_mode(SIZE)
pygame.display.set_caption("Seleccionar Modo - Escapa / Cazador")
FONT = pygame.font.SysFont("consolas", 26)
SMALL = pygame.font.SysFont("consolas", 18)
CLOCK = pygame.time.Clock()

COL_BG = (18, 24, 30)
COL_BTN = (40, 120, 200)
COL_BTN_H = (60, 150, 230)
COL_TEXT = (255, 255, 255)
COL_PANEL = (28, 34, 40)

# -------------------------
# Control de instancia única
# -------------------------
game_process = None  # Guarda el proceso lanzado, si existe

# -------------------------
# Clase Button
# -------------------------
class Button:
    def __init__(self, rect, text, cb):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.cb = cb

    def draw(self, surf):
        mx, my = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mx, my)
        col = COL_BTN_H if hover else COL_BTN
        pygame.draw.rect(surf, col, self.rect, border_radius=8)
        txt = FONT.render(self.text, True, COL_TEXT)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            try:
                if callable(self.cb):
                    self.cb()
            except Exception as ex:
                print("Error en callback de botón:", ex)

# -------------------------
# Lanzamiento de scripts con control de instancia
# -------------------------
def launch_script(name):
    """
    Lanza el script indicado solo si no hay otro proceso de juego abierto.
    Si ya hay uno, muestra un mensaje y no lanza otro.
    """
    global game_process
    path = os.path.join(BASE_DIR, name)
    if game_process is not None:
        # Verifica si el proceso sigue vivo
        if game_process.poll() is None:
            return f"Ya hay una ventana de juego abierta."
        else:
            game_process = None  # El proceso terminó, se puede lanzar otro

    if os.path.exists(path):
        try:
            game_process = subprocess.Popen([sys.executable, path], cwd=BASE_DIR)
        except Exception as ex:
            print("Error al lanzar:", ex)
            return f"Error al lanzar {name}"
        return f"Lanzado: {name}"
    else:
        return f"No encontrado: {name}"

message = ""  # Mensaje mostrado en la parte inferior

btn_w, btn_h = 360, 64
gap = 18
start_y = SIZE[1]//2 - (btn_h*3 + gap*2)//2

def set_msg(m):
    global message
    message = m

buttons = [
    Button(
        (SIZE[0]//2 - btn_w//2, start_y + i*(btn_h + gap), btn_w, btn_h),
        text,
        cb
    )
    for i, (text, cb) in enumerate([
        ("Modo Cazador", lambda: set_msg(launch_script("modo_cazador.py"))),
        ("Modo Escapa",  lambda: set_msg(launch_script("modo_escapa.py"))),
        ("Salir (ESC)", lambda: sys.exit(0))
    ])
]

def draw():
    SCREEN.fill(COL_BG)
    header = FONT.render("Elige el modo de juego", True, COL_TEXT)
    SCREEN.blit(header, header.get_rect(center=(SIZE[0]//2, 64)))
    pygame.draw.rect(SCREEN, COL_PANEL, (40, 100, SIZE[0]-80, SIZE[1]-140), border_radius=10)
    for b in buttons:
        b.draw(SCREEN)
    if message:
        txt = SMALL.render(message, True, (220,220,220))
        SCREEN.blit(txt, (20, SIZE[1]-30))

def handle_event(e):
    global message
    if e.type == pygame.QUIT:
        pygame.quit()
        sys.exit(0)

    if e.type == pygame.KEYDOWN:
        if e.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit(0)
        if e.key == pygame.K_1:
            set_msg(launch_script("modo_cazador.py"))
        if e.key == pygame.K_2:
            set_msg(launch_script("modo_escapa.py"))

    for b in buttons:
        b.handle(e)

def main():
    while True:
        for e in pygame.event.get():
            handle_event(e)
        draw()
        pygame.display.flip()
        CLOCK.tick(60)

if __name__ == "__main__":
    try:
        main()
    finally:
        pygame.quit()
        # Al cerrar juego.py, relanza el menú principal
        import subprocess
        import sys
        import os
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        menu_path = os.path.join(BASE_DIR, "main.py")
        if os.path.exists(menu_path):
            subprocess.Popen([sys.executable, menu_path], cwd=BASE_DIR)
        sys.exit(0)