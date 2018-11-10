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
    spawn_points = attr.ib(factory=list)
    w = attr.ib(default=0)
    h = attr.ib(default=0)


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
                tiles.append(Tile(i * tile_size, j * tile_size, tile_size, tile_size))
            else:
                assert False, "unknown tile char: %r" % char

    height = j + 1

    return Map(tiles, spawn_points, width * tile_size, height * tile_size)



TILE_SIZE = 8

MAP = parse_map("""

t . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . @ . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . t t t . . . . . . t t t t t t . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . @ . . . .
. t t t t t t t t t t t t t t t t t t .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . t

""", TILE_SIZE)


SCREEN_W, SCREEN_H = 160, 120


@attr.s
class GuyInputComponent(InputComponent):

    left_pressed = attr.ib(default=False)
    right_pressed = attr.ib(default=False)
    jump_pressed = attr.ib(default=False)
    jump_pressed_now = attr.ib(default=False)

    keymap = attr.ib(factory=lambda: dict(
        left=pyxel.KEY_LEFT,
        right=pyxel.KEY_RIGHT,
        jump=pyxel.KEY_CONTROL,
    ))

    def process_input(self):
        self.left_pressed = pyxel.btn(self.keymap['left'])
        self.right_pressed = pyxel.btn(self.keymap['right'])
        self.jump_pressed = pyxel.btn(self.keymap['jump'])
        self.jump_pressed_now = pyxel.btnp(self.keymap['jump'])



HORIZONTAL_VELOCITY = 1
MAX_JUMP_FRAME = 4
JUMP_VELOCITY = -5
GRAVITY = 1


@attr.s
class GuyPhysicsComponent(PhysicsComponent):

    """Implements moving based on input, as well as gravity.

    Features:

    * map collision detection
    * horizontal movement (constant velocity)
    * vertical movement (2nd degree polynomial)
        * gravity
        * jumping
    * jump higher if jump key is pressed longer

    Issues:

    1.  Transition from falling to standing flips back and forth a few times
        until the object stabilizes from being pushed out of the ground due to
        collisions; visible on the animation. Possible solutions:

        * push the object immediately next to the ground instead of back
          to its original location
        * run the physics simulation with a very small timestep (fraction of
          a frame) for a few times to allow the object to stabilize;
          probably means decoupling it from the fixed(?) timestep update()
          is called with

    2.  Jumping/falling is too fast; GRAVITY <1 makes flipping between states
        persistent (the object never stabilizes). Solution: Do physics with
        floats, convert to int only when drawing.


    """


    y_velocity = attr.ib(default=0)
    jump_frame = attr.ib(default=0)
    _jump_state = attr.ib(default='falling')

    had_collision = attr.ib(default=False)

    @property
    def jump_state(self):
        return self._jump_state

    @jump_state.setter
    def jump_state(self, value):
        print("{:10} -> {:10}  {:>3} {:>3} {:>3}".format(
            self._jump_state, value, self.y, self.y_velocity, self.jump_frame))
        self._jump_state = value

    def simulate(self):
        orig_x, orig_y = self.x, self.y

        if self.left_pressed:
            self.x -= HORIZONTAL_VELOCITY
        if self.right_pressed:
            self.x += HORIZONTAL_VELOCITY

        if self._have_map_collision():
            self.x = orig_x

        self._jump_state_machine()

        self.y_velocity += GRAVITY
        self.y = self.y + self.y_velocity

        self.had_collision = self._have_map_collision()
        if self.had_collision:
            self.y = orig_y

    def _have_map_collision(self):
        for tile in MAP.tiles:
            h_collision = self.x < tile.r and self.r > tile.x
            v_collision = self.y < tile.b and self.b > tile.y
            if h_collision and v_collision:
                return True
        return False

    def _jump_state_machine(self):

        if self.jump_state == 'standing':
            self.y_velocity = 0
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
                self.y_velocity = JUMP_VELOCITY
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


@attr.s
class GuyGraphicsComponent(GraphicsComponent):

    color = attr.ib(default=2)

    def render(self, offset_x, offset_y):
        pyxel.rectb(int(offset_x + self.x),
                    int(offset_y + self.y),
                    int(offset_x + self.x + self.w - 1),
                    int(offset_y + self.y + self.h - 1),
                    self.color)


@attr.s
class Guy(GuyPhysicsComponent, GuyInputComponent, GuyGraphicsComponent, Rect): pass


def update():
    if pyxel.btnp(pyxel.KEY_Q):
        pyxel.quit()
    if pyxel.btnp(pyxel.KEY_C):
        cycle_camera()

    for entity in filter_entities(ENTITIES, InputComponent):
        entity.process_input()
    for entity in filter_entities(ENTITIES, PhysicsComponent):
        entity.simulate()


def center_on_guy():
    return -GUY.x + SCREEN_W // 2, -GUY.y + SCREEN_H // 2

def center_on_map():
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

GUY = Guy(x=MAP.spawn_points[0][0], y=MAP.spawn_points[0][1], w=3, h=7)
TWO = Guy(x=MAP.spawn_points[1][0], y=MAP.spawn_points[1][1], w=3, h=7,
          color=3,
          keymap=dict(left=pyxel.KEY_A, right=pyxel.KEY_D, jump=pyxel.KEY_SPACE))

ENTITIES = [GUY, ] + MAP.tiles

pyxel.run(update, draw)

