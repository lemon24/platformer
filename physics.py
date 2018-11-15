"""

Implements gravity and collision detection.

Features:

* map collision detection
* vertical movement (2nd degree polynomial)
    * gravity
    * vertical velocity

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

import attr
import pyxel
import click



@attr.s
class Vec2:
    x = attr.ib(default=0)
    y = attr.ib(default=0)

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

    @property
    def position(self):
        return Vec2(self.x, self.y)

    @position.setter
    def position(self, value):
        self.x, self.y = value.x, value.y


class Static(Rect): pass

@attr.s
class Dynamic(Rect):
    velocity = attr.ib(default=attr.Factory(Vec2))
    old_position = attr.ib(default=attr.Factory(Vec2))
    had_collision = attr.ib(default=False)



@attr.s
class World:
    things = attr.ib(default=attr.Factory(list), converter=list)
    gravity = attr.ib(default=0)

    @property
    def static_things(self):
        for one in self.things:
            if not hasattr(one, 'velocity'):
                yield one

    @property
    def dynamic_things(self):
        for one in self.things:
            if hasattr(one, 'velocity'):
                yield one

    @classmethod
    def check_collision(cls, one, two):
        h_collision = one.x < two.r and one.r > two.x
        v_collision = one.y < two.b and one.b > two.y
        if h_collision and v_collision:
            return True
        return False

    def check_dynamic_static_collision(self, one):
        assert hasattr(one, 'velocity')
        for two in self.static_things:
            if self.check_collision(one, two):
                return True
        return False

    def simulate(self):
        for one in self.dynamic_things:
            one.old_position = one.position

            one.had_collision = False

            one.velocity.y += self.gravity

            one.y = one.y + one.velocity.y
            if self.check_dynamic_static_collision(one):
                one.had_collision = True
                one.y = one.old_position.y
                one.velocity.y = 0

            one.x = one.x + one.velocity.x
            if self.check_dynamic_static_collision(one):
                one.had_collision = True
                one.x = one.old_position.x
                one.velocity.x = 0



def right_pulling_gravity(self):
    self.world.things[0].velocity.x = 2


@attr.s
class Scene:
    name = attr.ib()
    offset = attr.ib()
    world = attr.ib()
    updates = attr.ib(default=attr.Factory(list))

    def update(self):
        for update in self.updates:
            update(self)
        self.world.simulate()


SCENES = [
    Scene('normal', Vec2(4, 4), World([
        Dynamic(4, 10, 3, 3),
        Static(0, 30, 12, 3),
    ], 1)),
    Scene('tunnel', Vec2(34, 4), World([
        Dynamic(4, 0, 3, 3, velocity=Vec2(0, 2)),
        Static(0, 30, 12, 3)
    ], 1)),
    Scene('hslide', Vec2(64, 4), World([
        Dynamic(-2, 20, 3, 3, velocity=Vec2(2, 0)),
        Static(0, 30, 12, 3),
    ], 1)),
    Scene('vslide', Vec2(94, 4), World([
        Dynamic(0, 0, 3, 3, velocity=Vec2(2, 0)),
        Static(12, 12, 3, 20),
    ], 1)),
    Scene('vsxvel', Vec2(124, 4), World([
        Dynamic(0, 0, 3, 3),
        Static(12, 12, 3, 20),
    ], 1), [right_pulling_gravity]),
]


def update():
    if pyxel.btnp(pyxel.KEY_Q):
        pyxel.quit()

    for scene in SCENES:
        scene.update()


DO_CLS = True
DO_CLIP = True
DO_FRAME = False

def draw():
    if DO_CLS:
        pyxel.cls(0)

    for scene in SCENES:
        pyxel.clip()

        pyxel.text(scene.offset.x, scene.offset.y, scene.name, 5)

        if DO_FRAME:
            pyxel.rectb(
                scene.offset.x - 1,
                scene.offset.y - 1,
                scene.offset.x + 24 + 1 - 1,
                scene.offset.y + 48 + 1 - 1,
                1)

        if DO_CLIP:
            pyxel.clip(
                scene.offset.x - 0,
                scene.offset.y - 0,
                scene.offset.x + 24 + 0 - 1,
                scene.offset.y + 48 + 0 - 1,
            )

        for thing in scene.world.things:
            if hasattr(thing, 'velocity'):
                color = 2   # purple
            else:
                color = 1   # blue
            if getattr(thing, 'had_collision', False):
                color = 8   # red

            pyxel.rectb(scene.offset.x + int(thing.x),
                        scene.offset.y + int(thing.y),
                        scene.offset.x + int(thing.x + thing.w - 1),
                        scene.offset.y + int(thing.y + thing.h - 1),
                        color)



@click.command()
@click.option('-f', '--fps', type=int, default=4, show_default=True)
@click.option('--cls/--no-cls', default=False, show_default=True)
@click.option('--clip/--no-clip', default=True, show_default=True)
def main(fps, cls, clip):
    global DO_CLS, DO_CLIP
    DO_CLS = cls
    DO_CLIP = clip
    pyxel.init(160, 120, fps=fps)
    pyxel.run(update, draw)

if __name__ == '__main__':
    main()

