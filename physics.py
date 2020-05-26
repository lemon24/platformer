"""

Implements gravity and collision detection.

The World class implements the main logic.

The World contains a list of entities. All entities are rectangles that
cannot be rotated (axis-aligned bounding boxes).

There are 2 kinds of entities:

Static
    Does not move. Does not have velocity. Does not collide with other static
    bodies.

Dynamic:
    Moves according to its velocity. Collides with static bodies. Does not
    collide with other dynamic bodies.

Collisions are detected by sweeping the object's path a factor of its size
at a time; this should catch most collisions, but won't catch all of them,
especially for larger objects. When a collision happens, the sweep is
repeated/resolved with a sub-unit step.

Collisions are resolved first on the vertical axis, then on the horizontal one.

Known issues:

1.  Objects' corners might tunnel through one another.


"""

from math import ceil

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
    gravity = attr.ib(default=attr.Factory(lambda: Vec2(0, 1)))

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

    def simulate(self, steps_per_frame=1, sweep=True):
        for one in self.dynamic_things:
            self.simulate_one(one, steps_per_frame, sweep)

    def simulate_one(self, one, steps_per_frame, sweep):
        sweep_steps = 1

        if sweep:
            new_x = one.x + one.velocity.x + self.gravity.x
            new_y = one.y + one.velocity.y + self.gravity.y
            length = ((one.x - new_x) ** 2 + (one.y - new_y) ** 2) ** .5
            # hardcoded to half of the smallest dimension, could be better
            sweep_length = min(one.w, one.h) / 2
            sweep_steps = ceil(length / sweep_length)

        dummy = Dynamic(one.x, one.y, one.w, one.h, Vec2(one.velocity.x, one.velocity.y))

        self.simulate_one_step(dummy,  steps_per_frame * sweep_steps)

        if sweep and dummy.had_collision:
            # hardcoded to half a pixel, could be better
            sweep_length = .5
            sweep_steps = ceil(length / sweep_length)
            self.simulate_one_step(one, steps_per_frame * sweep_steps)
        else:
            one.position = dummy.position
            one.velocity = dummy.velocity
            one.had_collision = dummy.had_collision

    def simulate_one_step(self, one, steps_per_frame):
        had_collision = False
        for _ in range(steps_per_frame):
            had_collision = self.simulate_one_substep(one, 1 / steps_per_frame)
            if had_collision:
                one.had_collision = True

    def simulate_one_substep(self, one, steps):
        one.old_position = one.position

        had_collision = False

        one.velocity.x += self.gravity.x * steps
        one.velocity.y += self.gravity.y * steps

        one.y += one.velocity.y * steps
        if self.check_dynamic_static_collision(one):
            had_collision = True
            one.y = one.old_position.y
            one.velocity.y = 0

        one.x += one.velocity.x * steps
        if self.check_dynamic_static_collision(one):
            had_collision = True
            one.x = one.old_position.x
            one.velocity.x = 0

        return had_collision


@attr.s
class Scene:
    name = attr.ib()
    offset = attr.ib()
    world = attr.ib()


SCENES = [
    Scene('normal', Vec2(4, 4), World([
        Dynamic(4, 10, 3, 3),
        Static(0, 30, 16, 3),
    ])),
    Scene('tunnel', Vec2(34, 4), World([
        Dynamic(4, 0, 3, 3, velocity=Vec2(0, 2)),
        Static(0, 30, 16, 3)
    ])),
    Scene('hslide', Vec2(64, 4), World([
        Dynamic(-2, 20, 3, 3, velocity=Vec2(2, 0)),
        Static(0, 30, 16, 3),
    ])),
    Scene('vslide', Vec2(94, 4), World([
        Dynamic(0, 0, 3, 3, velocity=Vec2(2, 0)),
        Static(12, 12, 3, 20),
    ])),
    Scene('vsxvel', Vec2(124, 4), World([
        Dynamic(0, 0, 3, 3),
        Static(12, 12, 3, 20),
    ], Vec2(1, 1))),
    Scene('tnlbig', Vec2(34, 56), World([
        Dynamic(4, -4, 8, 8, velocity=Vec2(0, 20)),
        Static(0, 30, 16, 3)
    ])),
]


DO_CLS = True
DO_CLIP = True
DO_SCENE_FRAME = False
STEPS_PER_FRAME = 1
SWEEP = True


def update():
    if pyxel.btnp(pyxel.KEY_Q):
        pyxel.quit()

    for scene in SCENES:
        scene.world.simulate(STEPS_PER_FRAME, SWEEP)


def draw():
    if DO_CLS:
        pyxel.cls(0)

    status = ' '.join([
        '--steps-per-frame {}'.format(STEPS_PER_FRAME),
        '--sweep' if SWEEP else '--no-sweep',
    ])
    pyxel.text(4, 108, status, 5)

    for scene in SCENES:
        pyxel.clip()

        pyxel.text(scene.offset.x, scene.offset.y, scene.name, 5)

        if DO_SCENE_FRAME:
            pyxel.rectb(
                scene.offset.x - 1,
                scene.offset.y - 1,
                24 + 1 - 1,
                48 + 1 - 1,
                1)

        if DO_CLIP:
            pyxel.clip(
                scene.offset.x - 0,
                scene.offset.y - 0,
                24 + 0 - 1,
                48 + 0 - 1,
            )

        for thing in scene.world.things:
            if hasattr(thing, 'velocity'):
                color = 2   # purple
            else:
                color = 1   # blue
            if getattr(thing, 'had_collision', False):
                color = 8   # red

            pyxel.rectb(scene.offset.x + round(thing.x),
                        scene.offset.y + round(thing.y),
                        round(thing.w),
                        round(thing.h),
                        color)


@click.command()
@click.option('-f', '--fps', type=int, default=4, show_default=True)
@click.option('-s', '--steps-per-frame', type=int, default=1, show_default=True)
@click.option('--sweep/--no-sweep', default=True, show_default=True)
@click.option('--cls/--no-cls', default=False, show_default=True)
@click.option('--clip/--no-clip', default=True, show_default=True)
def main(fps, cls, clip, steps_per_frame, sweep):
    global DO_CLS, DO_CLIP, STEPS_PER_FRAME, SWEEP
    DO_CLS = cls
    DO_CLIP = clip
    STEPS_PER_FRAME = steps_per_frame
    SWEEP = sweep
    pyxel.init(160, 120, fps=fps)
    pyxel.run(update, draw)


if __name__ == '__main__':
    main()

