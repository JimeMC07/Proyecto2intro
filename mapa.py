import random
from collections import deque

# Valores numéricos de casillas (compatibles con código existente)
CAMINO = 0
MURO = 1
SALIDA = 2
LIANA = 3   # solo enemigos pueden pasar
TUNEL = 4   # solo jugador puede pasar

class Tile:
    def walkable_by_player(self):
        return False
    def walkable_by_enemy(self):
        return False
    def value(self):
        return MURO

class CaminoTile(Tile):
    def walkable_by_player(self): return True
    def walkable_by_enemy(self): return True
    def value(self): return CAMINO

class MuroTile(Tile):
    def walkable_by_player(self): return False
    def walkable_by_enemy(self): return False
    def value(self): return MURO

class SalidaTile(Tile):
    def walkable_by_player(self): return True
    def walkable_by_enemy(self): return True
    def value(self): return SALIDA

class LianaTile(Tile):
    def walkable_by_player(self): return False
    def walkable_by_enemy(self): return True
    def value(self): return LIANA

class TunelTile(Tile):
    def walkable_by_player(self): return True
    def walkable_by_enemy(self): return False
    def value(self): return TUNEL

_tile_classes = {
    CAMINO: CaminoTile,
    MURO: MuroTile,
    SALIDA: SalidaTile,
    LIANA: LianaTile,
    TUNEL: TunelTile,
}

def _tile_from_value(v):
    cls = _tile_classes.get(v, CaminoTile)
    return cls()

def _create_random_tile_grid(cols, rows, start, salida, probs=None):
    """
    Crea una grid de objetos Tile con bordes muro y contenido aleatorio en interior.
    probs: diccionario opcional con probabilidades para MURO, LIANA, TUNEL.
    """
    if probs is None:
        probs = {MURO: 0.18, LIANA: 0.07, TUNEL: 0.04}  # por defecto
    grid = [[CaminoTile() for _ in range(cols)] for _ in range(rows)]

    # bordes como muros
    for x in range(cols):
        grid[0][x] = MuroTile()
        grid[rows-1][x] = MuroTile()
    for y in range(rows):
        grid[y][0] = MuroTile()
        grid[y][cols-1] = MuroTile()

    sx, sy = salida
    ix, iy = start
    grid[sy][sx] = SalidaTile()
    grid[iy][ix] = CaminoTile()

    for y in range(1, rows-1):
        for x in range(1, cols-1):
            if (x, y) == start or (x, y) == salida:
                continue
            r = random.random()
            if r < probs[MURO]:
                grid[y][x] = MuroTile()
            elif r < probs[MURO] + probs[LIANA]:
                grid[y][x] = LianaTile()
            elif r < probs[MURO] + probs[LIANA] + probs[TUNEL]:
                grid[y][x] = TunelTile()
            else:
                grid[y][x] = CaminoTile()
    return grid

def _grid_to_numeric(grid):
    return [[grid[y][x].value() for x in range(len(grid[0]))] for y in range(len(grid))]

def _player_bfs_has_path(grid, start, salida):
    cols = len(grid[0]); rows = len(grid)
    sx, sy = start; tx, ty = salida
    if not grid[sy][sx].walkable_by_player(): return False
    if not grid[ty][tx].walkable_by_player(): return False
    q = deque()
    q.append((sx, sy))
    seen = {(sx, sy)}
    while q:
        x, y = q.popleft()
        if (x, y) == (tx, ty):
            return True
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < cols and 0 <= ny < rows and (nx, ny) not in seen:
                if grid[ny][nx].walkable_by_player():
                    seen.add((nx, ny))
                    q.append((nx, ny))
    return False

def generate_map(cols, rows, start=(1,1), salida=None, max_attempts=200, probs=None):
    """
    Genera una matriz numérica (rows x cols) garantizando al menos un camino
    desde start hacia salida. Devuelve (matrix, salida_x, salida_y).
    """
    if salida is None:
        salida = (cols - 2, rows // 2)

    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        tile_grid = _create_random_tile_grid(cols, rows, start, salida, probs=probs)
        if _player_bfs_has_path(tile_grid, start, salida):
            return _grid_to_numeric(tile_grid), salida[0], salida[1]

    # Fallback: mapa limpio con salida y bordes
    mat = [[CAMINO for _ in range(cols)] for _ in range(rows)]
    for x in range(cols):
        mat[0][x] = MURO
        mat[rows-1][x] = MURO
    for y in range(rows):
        mat[y][0] = MURO
        mat[y][cols-1] = MURO
    sx, sy = salida
    mat[sy][sx] = SALIDA
    ix, iy = start
    mat[iy][ix] = CAMINO
    return mat, sx, sy

def is_walkable_by_player(matrix, x, y):
    if not (0 <= y < len(matrix) and 0 <= x < len(matrix[0])): return False
    v = matrix[y][x]
    return v in (CAMINO, SALIDA, TUNEL)

def is_walkable_by_enemy(matrix, x, y):
    if not (0 <= y < len(matrix) and 0 <= x < len(matrix[0])): return False
    v = matrix[y][x]
    return v in (CAMINO, SALIDA, LIANA)