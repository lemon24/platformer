import itertools

import pyxel


def parse_map(string):
    map = []
    for line in string.strip().splitlines():
        map.append(line.split())
    assert len(set(len(row) for row in map)) == 1
    return map

MAP = parse_map("""

t . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . t t t . . . . . . t t t t t t . . .
. . . . . . . . @ . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. t t t t t t t t t t t t t t t t t t .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . t

""")

def guy_map_pos():
    for j, row in enumerate(MAP):
        for i, tile in enumerate(row):
            if tile == '@':
                return j * TILE_SIZE, i * TILE_SIZE

TILE_SIZE = 8

MAP_W, MAP_H = len(MAP[0]) * TILE_SIZE, len(MAP) * TILE_SIZE

SCREEN_W, SCREEN_H = 160, 120


GUY_W, GUY_H = 3, 7
GUY_X, GUY_Y = guy_map_pos()

MAX_JUMP_HEIGHT = TILE_SIZE * 3 + 2
JUMP_HEIGHT = 0
MAX_JUMP_FRAME = 10
JUMP_FRAME = 0
JUMP_STATE = 'none'


def have_guy_collision():
    guy_r, guy_b = GUY_X + GUY_W, GUY_Y + GUY_H

    for j, row in enumerate(MAP):
        for i, tile in enumerate(row):
            if tile != 't':
                continue
            tile_x, tile_y = i * TILE_SIZE, j * TILE_SIZE
            tile_r, tile_b = tile_x + TILE_SIZE, tile_y + TILE_SIZE

            h_collision = GUY_X < tile_r and guy_r > tile_x
            v_collision = GUY_Y < tile_b and guy_b > tile_y
            if h_collision and v_collision:
                return True

    return False


def jump_state_machine():
    global JUMP_HEIGHT, JUMP_FRAME, JUMP_STATE, GUY_Y

    if JUMP_STATE != 'none':
        print(JUMP_STATE, JUMP_HEIGHT, JUMP_FRAME, GUY_Y)

    if JUMP_STATE != 'jumping':
        # gravity
        GUY_Y += 1

    if JUMP_STATE == 'none':
        if pyxel.btnp(pyxel.KEY_CONTROL):
            JUMP_STATE = 'jumping'
            return jump_state_machine()
        return have_guy_collision()

    elif JUMP_STATE == 'jumping':
        if pyxel.btn(pyxel.KEY_CONTROL):
            new_jump_height = min(JUMP_HEIGHT + 3, MAX_JUMP_HEIGHT)
            GUY_Y -= new_jump_height - JUMP_HEIGHT
            JUMP_HEIGHT = new_jump_height

            if have_guy_collision():
                print('collision during jump')
                JUMP_STATE = 'falling'
                return True

            JUMP_FRAME += 1
            if JUMP_FRAME > MAX_JUMP_FRAME:
                print('max frame reached')
                JUMP_STATE = 'falling'
                return False

            return False
        else:
            print('ctrl not pressed anymore')
            JUMP_STATE = 'falling'
            return False

    elif JUMP_STATE == 'falling':
        if have_guy_collision():
            print('collision during fall')
            JUMP_STATE = 'none'
            JUMP_FRAME = 0
            JUMP_HEIGHT = 0
            return True
        return False

    else:
        assert False


def update():
    global GUY_X, GUY_Y
    if pyxel.btnp(pyxel.KEY_Q):
        pyxel.quit()
    if pyxel.btnp(pyxel.KEY_C):
        cycle_camera()

    orig_x, orig_y = GUY_X, GUY_Y

    if pyxel.btn(pyxel.KEY_LEFT):
        GUY_X -= 1
    if pyxel.btn(pyxel.KEY_RIGHT):
        GUY_X += 1
    if have_guy_collision():
        GUY_X = orig_x

    if jump_state_machine():
        GUY_Y = orig_y


def draw_map(offset_x, offset_y):
    for j, row in enumerate(MAP):
        for i, tile in enumerate(row):
            if tile in '.@':
                pass
            elif tile == 't':
                pyxel.rect(offset_x + i * TILE_SIZE,
                           offset_y + j * TILE_SIZE,
                           offset_x + (i+1) * TILE_SIZE - 1,
                           offset_y + (j+1) * TILE_SIZE - 1,
                           1)
            else:
                assert False, "unknown tile: %r" % tile

def draw_guy(offset_x, offset_y):
    pyxel.rectb(offset_x + GUY_X,
                offset_y + GUY_Y,
                offset_x + GUY_X + GUY_W - 1,
                offset_y + GUY_Y + GUY_H - 1,
                2)


def center_on_guy():
    return -GUY_X + SCREEN_W // 2, -GUY_Y + SCREEN_H // 2

def center_on_map():
    return - MAP_W // 2 + SCREEN_W // 2, - MAP_H // 2 + SCREEN_H // 2



CENTER_FUNC_ITER = itertools.cycle([center_on_guy, center_on_map])

def cycle_camera():
    global CENTER_FUNC
    CENTER_FUNC = next(CENTER_FUNC_ITER)

CENTER_FUNC = None
cycle_camera()


def draw():
    pyxel.cls(0)

    offset_x, offset_y = CENTER_FUNC()

    draw_map(offset_x, offset_y)
    draw_guy(offset_x, offset_y)






pyxel.init(SCREEN_W, SCREEN_H)
pyxel.run(update, draw)

