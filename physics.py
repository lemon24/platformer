import attr
import pyxel


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

class Static(Rect): pass
    
@attr.s
class Dynamic(Rect):
    velocity = attr.ib(default=attr.Factory(Vec2))


@attr.s
class World:
    things = attr.ib(default=attr.Factory(list))
    gravity = attr.ib(default=0)
    
    def dynamic_and_static_pairs(self):
        for one in self.things:
            if not hasattr(one, 'velocity'):
                continue
            for two in self.things:
                if hasattr(two, 'velocity'):
                    continue
                yield one, two
                
    def simulate(self):
        for one in self.things:
            if not hasattr(one, 'velocity'):
                continue
            one.velocity.y += self.gravity
            one.x = int(one.x + one.velocity.x)
            one.y = int(one.y + one.velocity.y)




world = World([
    Dynamic(20, 20, 4, 4),
    Static(10, 40, 40, 4),
], 1)
    
def update():
    if pyxel.btnp(pyxel.KEY_Q):
        pyxel.quit()
    world.simulate()
    
def draw():
    pyxel.cls(0)  
    for thing in world.things:
        pyxel.rectb(thing.x,
                    thing.y,
                    thing.x + thing.w - 1,
                    thing.y + thing.h - 1,
                    1)
    
pyxel.init(160, 120, fps=4)

pyxel.run(update, draw)
