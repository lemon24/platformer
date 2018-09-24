import itertools
import abc

import attr
import pyxel


class GraphicsComponent(abc.ABC):

    @abc.abstractmethod
    def render(self, offset_x, offset_y):
        raise NotImplementedError

class InputComponent(abc.ABC):

    @abc.abstractmethod
    def process_input(self):
        raise NotImplementedError

class PhysicsComponent(abc.ABC):

    @abc.abstractmethod
    def simulate(self):
        raise NotImplementedError


@attr.s
class Rect:
    x = attr.ib(default=0)
    y = attr.ib(default=0)
    w = attr.ib(default=0)
    h = attr.ib(default=0)

    @property
    def r(self):
        return self.x + self.w

    @property
    def b(self):
        return self.y + self.h


class Tile(GraphicsComponent, Rect):

    def render(self, offset_x, offset_y):
        pyxel.rect(offset_x + self.x,
                   offset_y + self.y,
                   offset_x + self.r - 1,
                   offset_y + self.b - 1,
                   1)


@attr.s
class Map:
    tiles = attr.ib(factory=list)
    spawn_point = attr.ib(default=(0, 0))
    w = attr.ib(default=0)
    h = attr.ib(default=0)


def parse_map(string, tile_size):
    tiles = []
    spawn_point = None
    width = None

    for j, line in enumerate(string.strip().splitlines()):
        chars = line.split()
        if j == 0:
            width = len(chars)
        else:
            assert len(chars) == width, "wrong width at row %i" % j
        for i, char in enumerate(chars):
            if char == '.':
                continue
            elif char == '@':
                assert spawn_point is None, "already have one spawn point"
                spawn_point = i * tile_size, j * tile_size
            elif char == 't':
                tiles.append(Tile(i * tile_size, j * tile_size, tile_size, tile_size))
            else:
                assert False, "unknown tile char: %r" % char

    height = j + 1

    return Map(tiles, spawn_point, width * tile_size, height * tile_size)



TILE_SIZE = 8

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

""", TILE_SIZE)


SCREEN_W, SCREEN_H = 160, 120


@attr.s(init=False)
class GuyInputComponent(InputComponent):

    left_pressed = attr.ib(default=False)
    right_pressed = attr.ib(default=False)

    def process_input(self):
        self.left_pressed = pyxel.btn(pyxel.KEY_LEFT)
        self.right_pressed = pyxel.btn(pyxel.KEY_RIGHT)


@attr.s(init=False)
class GuyPhysicsComponent(PhysicsComponent):

    def simulate(self):
        if self.left_pressed:
            self.x -= 1
        if self.right_pressed:
            self.x += 1


class Guy(GuyPhysicsComponent, GuyInputComponent, GraphicsComponent, Rect):

    def render(self, offset_x, offset_y):
        pyxel.rectb(offset_x + self.x,
                    offset_y + self.y,
                    offset_x + self.x + self.w - 1,
                    offset_y + self.y + self.h - 1,
                    2)


guy_x, guy_y = MAP.spawn_point

GUY = Guy(guy_x, guy_y, 3, 7)

del guy_x, guy_y


MAX_JUMP_HEIGHT = TILE_SIZE * 3 + 2
JUMP_HEIGHT = 0
MAX_JUMP_FRAME = 10
JUMP_FRAME = 0
JUMP_STATE = 'falling'


def have_guy_collision():
    for tile in MAP.tiles:
        h_collision = GUY.x < tile.r and GUY.r > tile.x
        v_collision = GUY.y < tile.b and GUY.b > tile.y
        if h_collision and v_collision:
            return True
    return False


def jump_state_machine():
    global JUMP_HEIGHT, JUMP_FRAME, JUMP_STATE

    if JUMP_STATE != 'none':
        print(JUMP_STATE, JUMP_HEIGHT, JUMP_FRAME, GUY.y)

    if JUMP_STATE != 'jumping':
        # gravity
        GUY.y += 1

    if JUMP_STATE == 'none':
        if pyxel.btnp(pyxel.KEY_CONTROL):
            JUMP_STATE = 'jumping'
            return jump_state_machine()
        if have_guy_collision():
            return True
        else:
            JUMP_STATE = 'falling'
            return False

    elif JUMP_STATE == 'jumping':
        if pyxel.btn(pyxel.KEY_CONTROL):
            new_jump_height = min(JUMP_HEIGHT + 3, MAX_JUMP_HEIGHT)
            GUY.y -= new_jump_height - JUMP_HEIGHT
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
    if pyxel.btnp(pyxel.KEY_Q):
        pyxel.quit()
    if pyxel.btnp(pyxel.KEY_C):
        cycle_camera()

    orig_x, orig_y = GUY.x, GUY.y

    for entity in filter_entities(ENTITIES, InputComponent):
        entity.process_input()
    for entity in filter_entities(ENTITIES, PhysicsComponent):
        entity.simulate()

    if have_guy_collision():
        GUY.x = orig_x

    if jump_state_machine():
        GUY.y = orig_y


def center_on_guy():
    return -GUY.x + SCREEN_W // 2, -GUY.y + SCREEN_H // 2

def center_on_map():
    return - MAP.w // 2 + SCREEN_W // 2, - MAP.h // 2 + SCREEN_H // 2



CENTER_FUNC_ITER = itertools.cycle([center_on_guy, center_on_map])

def cycle_camera():
    global CENTER_FUNC
    CENTER_FUNC = next(CENTER_FUNC_ITER)

CENTER_FUNC = None
cycle_camera()


def draw():
    pyxel.cls(0)
    offset_x, offset_y = CENTER_FUNC()
    for entity in filter_entities(ENTITIES, GraphicsComponent):
        entity.render(offset_x, offset_y)


ENTITIES = [GUY] + MAP.tiles

def filter_entities(entities, *classinfos):
    for entity in entities:
        if all(isinstance(entity, ci) for ci in classinfos):
            yield entity


pyxel.init(SCREEN_W, SCREEN_H)
pyxel.run(update, draw)

