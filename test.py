import itertools
import abc

import attr
import pyxel

from physics import Static, Dynamic, World, Vec2


class GraphicsComponent(abc.ABC):

    @abc.abstractmethod
    def render(self, offset_x, offset_y):
        raise NotImplementedError

class InputComponent(abc.ABC):

    @abc.abstractmethod
    def process_input(self):
        raise NotImplementedError

class PhysicsComponent(abc.ABC):

    pass


@attr.s
class TileGraphicsComponent(GraphicsComponent):

    fill = attr.ib(default=True)
    color = attr.ib(default=1)

    def render(self, offset_x, offset_y):
        func = pyxel.rect if self.fill else pyxel.rectb
        func(offset_x + self.x,
             offset_y + self.y,
             self.w,
             self.h,
             self.color)

@attr.s
class Tile(TileGraphicsComponent, PhysicsComponent, Static):

    def to_shadow_tile(self, **kwargs):
        return ShadowTile(x=self.x, y=self.y, w=self.w, h=self.h, **kwargs)


@attr.s
class ShadowTile(TileGraphicsComponent, Static):
    pass


@attr.s
class Map:
    tiles = attr.ib(factory=list)
    spawn_points = attr.ib(factory=list)
    w = attr.ib(default=0)
    h = attr.ib(default=0)

@attr.s
class MapList:
    maps = attr.ib(factory=list)
    current_index = attr.ib(default=0)

    @property
    def current(self):
        return self.maps[self.current_index]

    @property
    def previous(self):
        if self.current_index > 0:
            return self.maps[self.current_index - 1]
        return None

    @property
    def next(self):
        if self.current_index < len(self.maps) - 1:
            return self.maps[self.current_index + 1]
        return None

    def move_back(self):
        if self.previous:
            self.current_index -= 1

    def move_forward(self):
        if self.next:
            self.current_index += 1


def parse_map(string, tile_size):
    tiles = []
    spawn_points = []
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
                spawn_points.append((i * tile_size, j * tile_size))
            elif char == 't':
                tiles.append(Tile(
                    x=i * tile_size,
                    y=j * tile_size,
                    w=tile_size,
                    h=tile_size,
                ))
            else:
                assert False, "unknown tile char: %r" % char

    height = j + 1

    return Map(tiles, spawn_points, width * tile_size, height * tile_size)


TILE_SIZE = 8

MAP_LIST = MapList([

parse_map("""
t . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . t t t t .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . @ . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . t t t . . . . . . t t t t t t . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . @ . . . .
. t t t t t t t t t t t t t t t t t . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . t t
""", TILE_SIZE),

parse_map("""
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . t t t t . . . . . . . . .
. . . . @ . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. t t t t t . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . @ . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . t t t . . .
. . . . . . . . . . . . . . . . . . . .
""", TILE_SIZE),

parse_map("""
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . t t t . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . @ . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . @ . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . t t t t t t t t t . . . . . . .
. . . . . . . . . . . . . . . . . . . .
""", TILE_SIZE),

])


SCREEN_W, SCREEN_H = 160, 120


@attr.s
class GuyInputComponent(InputComponent):

    """Implements moving based on input.

    Features:

    * horizontal movement (constant velocity)
    * jumping
        * jump higher if jump key is pressed longer

    """


    left_pressed = attr.ib(default=False)
    right_pressed = attr.ib(default=False)
    jump_pressed = attr.ib(default=False)
    jump_pressed_now = attr.ib(default=False)

    keymap = attr.ib(factory=lambda: dict(
        left=pyxel.KEY_LEFT,
        right=pyxel.KEY_RIGHT,
        jump=pyxel.KEY_CONTROL,
    ))

    jump_frame = attr.ib(default=0)
    _jump_state = attr.ib(default='falling')

    @property
    def jump_state(self):
        return self._jump_state

    @jump_state.setter
    def jump_state(self, value):
        print("{:10} -> {:10}  {:>3} {:>3} {:>3}".format(
            self._jump_state, value, self.y, self.velocity.y, self.jump_frame))
        self._jump_state = value

    def _jump_state_machine(self):

        if self.jump_state == 'standing':
            self.velocity.y = 0
            if not self.had_collision:
                self.jump_state = 'falling'
                return

            if self.jump_pressed_now:
                self.jump_state = 'jumping'
                self.had_collision = False
                return self._jump_state_machine()

        elif self.jump_state == 'jumping':

            if self.had_collision:
                self.jump_frame = 0
                self.jump_state = 'falling'
                return

            if self.jump_pressed:
                self.velocity.y = JUMP_VELOCITY
                self.jump_frame += 1
                if self.jump_frame > MAX_JUMP_FRAME:
                    self.jump_frame = 0
                    self.jump_state = 'falling'

        elif self.jump_state == 'falling':
            if self.had_collision:
                self.jump_state = 'standing'
                return

        else:
            assert False, "invalid state: %s" % self.jump_state

    def process_input(self):
        self.left_pressed = pyxel.btn(self.keymap['left'])
        self.right_pressed = pyxel.btn(self.keymap['right'])
        self.jump_pressed = pyxel.btn(self.keymap['jump'])
        self.jump_pressed_now = pyxel.btnp(self.keymap['jump'])

        if self.left_pressed + self.right_pressed == 1:
            if self.left_pressed:
                self.velocity.x = -HORIZONTAL_VELOCITY
            if self.right_pressed:
                self.velocity.x = +HORIZONTAL_VELOCITY
        else:
            self.velocity.x = 0

        self._jump_state_machine()


HORIZONTAL_VELOCITY = 1.2
MAX_JUMP_FRAME = 5
JUMP_VELOCITY = -3.6
GRAVITY = Vec2(0, .5)


@attr.s
class GuyGraphicsComponent(GraphicsComponent):

    color = attr.ib(default=2)

    def render(self, offset_x, offset_y):
        pyxel.rectb(round(offset_x + self.x),
                    round(offset_y + self.y),
                    round(self.w),
                    round(self.h),
                    self.color)


@attr.s
class Guy(GuyInputComponent, GuyGraphicsComponent, PhysicsComponent, Dynamic): pass


def update():
    if pyxel.btnp(pyxel.KEY_Q):
        pyxel.quit()
    if pyxel.btnp(pyxel.KEY_C):
        cycle_camera()

    if pyxel.btnr(pyxel.KEY_Z):
        MAP_LIST.move_back()
    if pyxel.btnr(pyxel.KEY_X):
        MAP_LIST.move_forward()

    update_entities()

    for entity in filter_entities(ENTITIES, InputComponent):
        entity.process_input()

    WORLD.simulate()



def center_on_guy():
    return -GUY.x + SCREEN_W // 2, -GUY.y + SCREEN_H // 2

def center_on_map():
    MAP = MAP_LIST.current
    return - MAP.w // 2 + SCREEN_W // 2, - MAP.h // 2 + SCREEN_H // 2



CENTER_FUNC_ITER = itertools.cycle([center_on_map, center_on_guy])

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


def filter_entities(entities, *classinfos):
    for entity in entities:
        if all(isinstance(entity, ci) for ci in classinfos):
            yield entity


pyxel.init(SCREEN_W, SCREEN_H)

GUY = Guy(x=MAP_LIST.current.spawn_points[0][0], y=MAP_LIST.current.spawn_points[0][1], w=3, h=7)
TWO = Guy(x=MAP_LIST.current.spawn_points[1][0], y=MAP_LIST.current.spawn_points[1][1], w=3, h=7,
          color=3,
          keymap=dict(left=pyxel.KEY_A, right=pyxel.KEY_D, jump=pyxel.KEY_SPACE))


ENTITIES = None
WORLD = None

def update_entities():
    global ENTITIES, WORLD
    ENTITIES = []

    # TODO: we shouldn't process input here
    # TODO: avoid copying tiles needlessly (a real ECS wouldn't?)
    if pyxel.btn(pyxel.KEY_Z):
        if MAP_LIST.previous:
            ENTITIES.extend(
                t.to_shadow_tile(fill=False, color=5)
                for t in MAP_LIST.previous.tiles
            )

    ENTITIES.extend(MAP_LIST.current.tiles)
    ENTITIES.append(GUY)

    if pyxel.btn(pyxel.KEY_X):
        if MAP_LIST.next:
            ENTITIES.extend(
                t.to_shadow_tile(fill=False, color=7)
                for t in MAP_LIST.next.tiles
            )

    WORLD = World(filter_entities(ENTITIES, PhysicsComponent), GRAVITY)

update_entities()



pyxel.run(update, draw)

