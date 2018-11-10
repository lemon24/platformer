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

            one.velocity.y += self.gravity
            one.x = one.x + one.velocity.x
            one.y = one.y + one.velocity.y

            one.had_collision = False

            if self.check_dynamic_static_collision(one):
                one.had_collision = True

                one.x = one.old_position.x
                one.velocity.x = 0

                if self.check_dynamic_static_collision(one):
                    one.y = one.old_position.y
                    one.velocity.y = 0




WORLD = World([
    Dynamic(20, 20, 4, 4),
    Static(10, 40, 40, 4),

    Dynamic(70, 20, 4, 4),
    Static(60, 80, 40, 4),

    Dynamic(90, 50, 4, 4, velocity=Vec2(2, 0)),
    Static(100, 40, 4, 40),

], 1)

def update():
    if pyxel.btnp(pyxel.KEY_Q):
        pyxel.quit()
    WORLD.simulate()

def draw():
    pyxel.cls(0)
    for thing in WORLD.things:
        pyxel.rectb(int(thing.x),
                    int(thing.y),
                    int(thing.x + thing.w - 1),
                    int(thing.y + thing.h - 1),
                    2 if hasattr(thing, 'velocity') else 1)



if __name__ == '__main__':
    import pyxel
    pyxel.init(160, 120, fps=4)
    pyxel.run(update, draw)

