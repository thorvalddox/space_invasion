__author__ = 'thorvald'

import random
import math
import time
from collections import Counter, namedtuple, OrderedDict
from functools import partial
from itertools import islice,chain

import pygame

from names import generate_name
from datahandle import Metal,metal,metals,Solvent,solvent,solvents,Plan,plan,plans,emptyplan,Ship,ship,ships
from datahandle import makecolor

import xml.etree.ElementTree as ET
import json


# class OrderedCounter(Counter, OrderedDict):
#	pass

def lograndom(mini, maxi):
    rel = math.log(maxi / mini)
    relrand = random.random() * rel

    return (mini * math.exp(relrand))


def log_to_rel(value, mini, maxi):
    return (math.log(value / mini)) / (math.log(maxi / mini))

def sign(x):
    return (x>0)-(x<0)

def smash(x,level):
    return(max(min(x,level),-level))

Button = namedtuple("Button", "rect,shortcut,command,alt")


class KeyHandler:
    def __init__(self):
        self.keys = json.load(open("key_bindings.json"))

    def __getitem__(self, item):
        return self.keys.get(item, "")


class Graphics:
    instance = None

    def __init__(self, defaultview, update):
        assert Graphics.instance is None, "Multuple objects handling the same window"
        self.view = defaultview
        self.gameupdate = update
        self.screen = pygame.display.set_mode((800, 600))
        self.screen.fill((0, 0, 0))
        self.infoview = pygame.Surface((400, 600))
        self.butview = pygame.Surface((400, 200))
        pygame.font.init()
        self.font = pygame.font.SysFont("monospace", 15)
        self.largefont = pygame.font.SysFont("monospace", 30)
        self.buttons = []
        self.keyhandler = KeyHandler()
        self.trade_connect = None
        self.battle_connect = None
        self.last_fleet = None
        self.planetdisp = ((10,0),(5,10),(-10,-15))
        self.x = 0
        self.y = 0
        Graphics.instance = self

    def mainloop(self):
        while True:
            stoptime = time.time() + 1 / 60
            self.step()
            pygame.display.flip()

            while True:
                pygame.event.pump()
                for e in pygame.event.get():
                    if e.type == pygame.QUIT:
                        pygame.display.quit()
                        return
                    elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        self.runbuttons(e.pos)
                    elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 2:
                        self.view.escape()
                    elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
                        self.runbuttons(e.pos,right=True)
                    elif e.type == pygame.KEYDOWN:
                        if e.key == pygame.K_ESCAPE:
                            self.view.escape()
                        else:
                            self.runkeys(e.key)
                if not time.time() < stoptime:
                    break

    def step(self):
        self.buttons.clear()
        self.draw_battle_state()
        self.infoview.fill((127, 127, 255))
        self.butview.fill((0, 0, 127))
        self.view.draw()
        self.view.draw_button("back", (350, 0, 50, 20), self.view.escape)
        self.screen.blit(self.infoview, (400, 0))
        self.screen.blit(self.butview, (0, 400))
        self.gameupdate()
        self.fixpos()
        # print("updated")

    def relpos(self,x,y):
        return (x-self.x,y-self.y)

    def fixpos(self):
        gx, gy = self.find_selected_star().pos
        self.x += smash(gx-self.x-200,5)
        self.y += smash(gy-self.y-200,5)

    def draw_battle_state(self):
        self.screen.fill((0, 0, 0), (0, 0, 400, 400))
        for s in Star.all_:
            x,y = self.relpos(*s.pos)
            if not (0<x<400 and 0<y<400):
                continue
            pygame.draw.circle(self.screen, s.color, (x,y), 5)
            for i, (p,(rx,ry)) in enumerate(zip(s.planets,self.planetdisp)):
                pygame.draw.circle(self.screen, p.teamcolor(), (x + rx, y +ry), 2)
                self.make_button((x+rx-2,y+ry-2,4,4),p.show,"",p.perform)
            self.make_button((x - 5, y - 5, 10, 10), s.click)
        s = self.find_selected_star()
        if s is not None:
            pygame.draw.circle(self.screen, (255, 255, 255), self.relpos(*s.pos), 10, 1)
        p = self.find_planet_pos()
        if p is not None:
            pygame.draw.circle(self.screen, (255, 255, 255), p, 4, 1)
        p = self.find_planet_pos(self.trade_connect)
        if p is not None:
            pygame.draw.circle(self.screen, (0, 0, 255), p, 6, 1)
        p = self.find_planet_pos(self.battle_connect)
        if p is not None:
            pygame.draw.circle(self.screen, (255, 0, 0), p, 12, 1)
        for t in TradeRoute.all_:
            pygame.draw.line(self.screen,(63,63,255),self.find_planet_pos(t.begin),self.find_planet_pos(t.end))
        for t in FleetFlying.all_:
            pygame.draw.line(self.screen,(255,63,63),self.find_planet_pos(t.start),self.find_planet_pos(t.target))
            positions = t.displaypos(self.find_planet_pos(t.start),self.find_planet_pos(t.target))
            pygame.draw.circle(self.screen,(255,63,63),next(positions),3)
            for i in positions:
                pygame.draw.circle(self.screen,(63,127,63),i,3)
        for t in FleetBattle.all_:
            p = self.find_planet_pos(t.loc)
            if p is not None:
                pygame.draw.circle(self.screen, (255, 0, 0), p, 8, 3)

    def runbuttons(self, pos, right=False):
        for i in self.buttons:
            if i.rect.collidepoint(pos):
                if not right:
                    i.command()
                else:
                    i.alt()

    def runkeys(self, key):
        print(key)
        for i in self.buttons:
            if self.keyhandler[i.shortcut] == key:
                if not pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    i.command()
                else:
                    i.alt()

    def make_button(self, coords, command, shortcut="",alt=lambda :None):
        if not isinstance(coords, pygame.Rect):
            rect = pygame.Rect(*coords)
        else:
            rect = coords
        self.buttons.append(Button(rect, shortcut, command, alt))

    def connect_trade_route(self,planet):
        if not planet.can_trade:
            return
        if self.trade_connect is None:
            self.trade_connect = planet
        else:
            TradeRoute.build(self.trade_connect,planet)
            self.trade_connect = None

    def settarget(self,planet):
        if self.last_fleet is None:
            print("No fleet selected")
        else:
            self.last_fleet.launch(planet)

    def find_selected_star(self,selection=...):
        if selection is ...:
            selection = self.view
        v = selection
        while not isinstance(v, Star):
            try:
                v = v.parent
            except AttributeError:
                return (None)
        return (v)

    def find_selected_planet(self,selection=...):
        if selection is ...:
            selection = self.view
        v = selection
        while not isinstance(v, Planet):
            try:
                v = v.parent
            except AttributeError:
                return (None)
        return (v)

    def find_planet_pos(self,selection=...):
        planet = self.find_selected_planet(selection)
        if planet is None:
            return None
        index= planet.parent.planets.index(planet)
        x,y = self.relpos(*planet.parent.pos)
        rx,ry = self.planetdisp[index]
        return x+rx,y+ry

class ViewPort():  # Used to pass to main as draw object.
    @property
    def screen(self):
        return Graphics.instance.infoview

    @property
    def banner(self):
        return Graphics.instance.butview

    @property
    def graph(self):
        return Graphics.instance

    def draw(self):
        pass

    def show(self):
        Graphics.instance.view = self

    def escape(self):
        pass

    def draw_text(self, text, pos, color=(0, 0, 0), large=False, align=0, valign=0,
                  surface=...):  # 0 = left, 1=mid , 2 = right
        label = [self.graph.font, self.graph.largefont][large].render(text, True, color)
        x, y = pos
        w, h = label.get_size()
        x -= align * w / 2
        y -= valign * h / 2
        if surface == ...:
            surface = self.screen
        surface.blit(label, (x, y))

    def draw_text_banner(self, *args, **kwargs):
        self.draw_text(*args, surface=self.banner, **kwargs)

    def draw_button(self, text, coords, command, shortcut="", alt=lambda:None):
        rect = pygame.Rect(*coords)
        self.screen.fill((127, 127, 127), rect)
        pygame.draw.rect(self.screen, (0, 0, 0), rect, 2)
        self.draw_text(text, rect.center, align=1, valign=1)
        self.graph.make_button(rect.move(400, 0), command, shortcut, alt)

    def draw_button_disabled(self, text, coords, command=lambda:None, alt=lambda:None):
        rect = pygame.Rect(*coords)
        self.screen.fill((127, 127, 127), rect)
        pygame.draw.rect(self.screen, (0, 0, 0), rect, 2)
        self.draw_text(text, rect.center, color=(192, 192, 192), align=1, valign=1)

    def draw_directory(self, dir, y, color=(0, 0, 0)):
        for i, (k, v) in enumerate(dir.items()):
            self.draw_text(k, (140, y + i * 15), color, align=2)
            self.draw_text(v, (150, y + i * 15), color)

    def draw_bar_directory(self, dir, y, color=(0, 0, 0)):
        for i, (k, (v, c)) in enumerate(dir.items()):
            self.draw_text(k, (140, y + i * 15), color, align=2)
            pygame.draw.rect(self.screen, (127, 127, 127), (150, y + i * 15, 200, 10))
            pygame.draw.rect(self.screen, c, (150, y + i * 15, 200 * v, 10))

    def draw_index_button(self,text,index,width=400,command=None,disabled=False,alt=lambda:None):
        if not disabled and command is not None:
            self.draw_button("{}: {}".format(index + 1, text), (0, index * 50+50, width, 50),
                                     command,"select_{}".format(index),alt)
        else:
            self.draw_button_disabled("X: {}".format(text), (0, index * 50+50, width, 50),alt)

    def draw_tuples(self,iter,y):
        for i, d in enumerate(iter):
            k,v = d[:2]
            color = d[2] if len(d) >= 3 else (0,0,0)
            self.draw_text(k, (140, y + i * 15), color, align=2)
            self.draw_text(v, (150, y + i * 15), color)

    def draw_bar_tuples(self,iter,y):
        for i, d in enumerate(iter):
            k,v = d[2:]
            color = d[3] if len(d) >= 3 else (0,0,0)
            pygame.draw.rect(self.screen, (127, 127, 127), (150, y + i * 15, 200, 10))
            pygame.draw.rect(self.screen, color, (150, y + i * 15, 200 * v, 10))


def usecolorstring(value, clist):
    itemlenght = 1 / (len(clist) - 1)
    index = math.floor(value / itemlenght)
    offset = value - index * itemlenght
    prev, next = clist[index:index + 2]
    return makecolor(*(p * offset + n * (1 - offset) for p, n in zip(prev, next)))


class Star(ViewPort):
    all_ = []

    def __init__(self,clustersize):
        self.name = generate_name()
        self.pos = (random.randrange(clustersize), random.randrange(clustersize))
        while Star.all_ and min(self.distance(s) for s in Star.all_) < 40:
            self.pos = (random.randrange(clustersize), random.randrange(clustersize))
        self.mass = lograndom(0.7, 1.4)
        self.color = usecolorstring((self.mass - 0.7) / 0.7,
                                    [(0, 128, 255), (255, 255, 255), (255, 255, 0), (255, 0, 0)])
        self.planets = [Planet(self, i) for i in range(3)]
        Star.all_.append(self)

    def distance(self, other):
        return math.sqrt((self.pos[0] - other.pos[0]) ** 2 + (self.pos[1] - other.pos[1]) ** 2)

    def click(self):
        self.show()

    def draw(self):
        self.banner.fill((0, 0, 60))
        pygame.draw.circle(self.banner, self.color, (-50, 100), 100)
        self.draw_text_banner(self.name, (0, 0), (255, 255, 255))
        for i, p in enumerate(self.planets):
            self.graph.make_button((p.dispdist - p.dispsize, 400, 2 * p.dispsize, 200), p.show,
                                   "select_{}".format(i),p.perform)
            pygame.draw.circle(self.banner, p.teamcolor(), (-50, 100), int(p.dispdist) + 50, 1)
            pygame.draw.circle(self.banner, p.color, (int(p.dispdist), 100), int(p.dispsize))
        for i, k in enumerate(["right", "down", "left", "up"]):
            self.graph.make_button((0, 0, 0, 0), partial(self.detect_nearby, i), k)
        self.screen.fill((127, 127, 255))
        self.draw_text(self.name, (0, 0), large=True)
        self.draw_tuples(self.getinfo(), 50)

    def getinfo(self):
        yield ("mass", "{:.2f} \u2609".format(self.mass))
        for i, p in enumerate(self.planets):
            yield ("planet {}".format(i + 1), p.name)

    def detect_nearby(self, direction):  # right, down, left, up
        distance = 400
        target = None
        for s in Star.all_:
            if s is self:
                continue
            relx, rely = [b - a for a, b in zip(self.pos, s.pos)]
            if direction == 1:
                relx, rely = rely, -relx
            elif direction == 2:
                relx, rely = -relx, -rely
            elif direction == 3:
                relx, rely = -rely, relx
            if abs(rely) > relx:
                continue
            if relx < distance:
                distance = relx
                target = s
        if target is not None:
            target.show()
        else:
            print("stuck :(")

    def gametick(self):
        for p in self.planets:
            if p.buildable:
                p.gametick()



def find_solvent(temp, press):
    for i in solvents():
        if i.mintemp < temp < i.maxtemp:
            if i.minpress < press < i.maxpress:
                return i
            else:
                return None
    return None


InfoBar = namedtuple("InfoBar", "value,color")


class Planet(ViewPort):
    all_ = []

    def __init__(self, parent, index):
        self.parent = parent
        self.mass = lograndom(10 ** -2, 70) * 10 ** index
        self.distance = lograndom(0.03, 0.3) * 10 ** index
        self.metals = OrderedDict((m, random.random() ** 3) for m in metals())
        self.solvents = OrderedDict((s, random.random() ** 3) for s in solvents())
        self.dispsize = (log_to_rel(self.mass, 10 ** -2, 7000) + 0.1) * 20
        self.dispdist = log_to_rel(self.distance, 0.03, 300) * 300 + 100
        self.color = usecolorstring(log_to_rel(self.mass, 10 ** -2, 7000), [(127, 127, 127), (255, 255, 127)])
        self.structures = [Structure(self) for _ in range(5)]
        self.name = generate_name()
        self.owner = None
        self.storage = Counter(self.solvents.keys())
        self.storage.update(self.metals.keys())
        self.population = 0
        self.temperature_max = 300 / self.distance / self.parent.mass
        self.temperature_min = self.temperature_max * 0.8
        self.pressure = self.mass ** 1 / 3
        self.active_solvent = find_solvent(self.temperature_max, self.pressure)
        self.buildable = self.active_solvent is not None
        self.autofire = True
        self.counter = 0

    def draw(self):
        self.screen.fill((127, 127, 255))
        self.draw_text(self.name, (0, 0), large=True)
        self.draw_tuples(self.getinfo(), 50)
        self.draw_bar_directory(OrderedDict(self.getgraph()), 400)
        self.draw_structures()
        if self.owner != Team.UI_base and self.buildable:
            self.draw_index_button("attack", 3, 400, partial(self.graph.settarget, self))


    def draw_structures(self):
        self.banner.fill(self.color, (0, 100, 400, 100))
        for i, s in enumerate(self.structures):
            s.draw_far(i)
        index = 0
        for f in self.get_battles():
            if f.loc != self:
                continue
            for s,c in f.ships.items():
                for _ in range(c):
                    index += 1
                    pygame.draw.circle(self.banner,ship(s).color,(index*25,25),10)

    def getinfo(self):

        yield ("mass", "{:.2f} µ\u2609".format(self.mass))
        yield ("solar distance", "{:.2f} AU".format(self.distance))
        yield ("solar system", self.parent.name)
        yield ("", "")
        yield ("highest temp.", "{:.2f} °C".format(self.temperature_max - 273))
        yield ("lowest temp.", "{:.2f} °C".format(self.temperature_min - 273))
        yield ("surface press.", "{:.2f} Pa".format(self.pressure))
        yield ("", "")
        yield ("owner", self.owner.name if self.owner else "nobody")
        yield ("lifeform", self.active_solvent.creaturename if self.active_solvent is not None else "none")

    def getgraph(self):
        if not self.buildable:
            yield ("not buildable", InfoBar(0, (0, 0, 0)))
            return
        for k, v in self.solvents.items():
            yield (k.name, InfoBar(v, k.color))
        for k, v in self.metals.items():
            yield (k.name, InfoBar(v, k.color))

    def teamcolor(self):
        if not self.buildable:
            return (127, 127, 127)
        # return(self.active_solvent.color)
        if self.owner is None:
            return (255, 255, 255)
        else:
            return self.owner.color

    def escape(self):
        self.parent.show()

    def gametick(self):

        if all(s.plan == plan("") for s in self.structures):
            self.owner = None
        self.counter += 1
        for k in self.storage:
            if self.storage[k] > 9999:
                self.storage[k] = 9999
        for s in self.structures:
            s.gametick()
        if self.autofire and 1 == self.counter*sum((s.plan == plan("S") for s in self.structures))% 360:
                for f in FleetFlying.all_:
                    if f.target == self:
                        cost = {metal("I"):80,metal("M"):40,metal("G"):20}
                        if all(v >= cost.get(k, 0) for k, v in self.storage.items()):
                            f.create_missile()

    def perform(self):
        if self.owner == Team.UI_base:
            self.graph.connect_trade_route(self)
        else:
            self.graph.settarget(self)

    @property
    def can_trade(self):
        return any(s.plan == plan("T") for s in self.structures)

    def get_battles(self):
        for f in FleetBattle.all_:
            if f.loc == self:
                yield f


class Team(ViewPort):
    all_ = []
    UI_base = None

    def __init__(self, ai=None, name="AI"):
        self.color = [(0, 127, 127), (255, 127, 0), (0, 127, 0), (255, 255, 0), (0, 127, 127)][len(Team.all_)]
        self.name = name
        Team.all_.append(self)
        if Team.UI_base is None:
            Team.UI_base = self

        self.find_planet()
        self.ai = ai(self) if ai is not None else None

    def find_planet(self):
        for s in Star.all_:
            for p in s.planets:
                if p.active_solvent is not None and p.solvents[p.active_solvent]>0.5 and p.owner is None:
                    p.owner = self
                    for s,l in zip(p.structures,"TCMLS"):
                        s.plan = plan(l)
                        s.health = 100


                    p.storage += {m:5000 for m in metals()}

                    if Team.UI_base is self:
                        p.show()
                    return True
        return False

    def draw(self):
        pass

    def gametick(self):
        self.check_lose()
        if self.ai is not None:
            self.ai.gametick()

    def check_lose(self):
        planets = chain(*(s.planets for s in Star.all_))
        if not any(p.owner == self and any(s.plan == plan("C") for s in p.structures) for p in planets):
            for p in planets:
                if p.owner == self:
                    p.owner = None

class Structure(ViewPort):
    def __init__(self, parent):
        self.parent = parent
        self.plan = emptyplan
        self.active = 0
        self.fleet = None
        self.health = 0

    def draw_far(self, i):
        if not self.parent.buildable:
            return
        bcolor = self.parent.active_solvent.citycolor
        color = self.parent.owner.color if self.parent.owner is not None else (0,0,0)
        self.graph.make_button((30 + 70 * i, 400, 60, 600), self.show, "select_{}".format(i),self.perform)
        pygame.draw.rect(self.banner, (255,0,0), (35 + 70 * i, 160, 60, 10))
        pygame.draw.rect(self.banner, (0,127,0), (35 + 70 * i, 160, int(0.6*self.health), 10))
        if self.plan.index == 0:
            pygame.draw.ellipse(self.banner, bcolor, (30 + 70 * i, 110, 60, 40))
        elif self.plan.index == 1:
            pygame.draw.ellipse(self.banner, bcolor, (30 + 70 * i, 110, 60, 40))
            pygame.draw.rect(self.banner, color, (35 + 70 * i, 80, 15, 55))
            pygame.draw.rect(self.banner, color, (52 + 70 * i, 70, 15, 55))
            pygame.draw.rect(self.banner, color, (70 + 70 * i, 80, 15, 55))
        elif self.plan.index == 2:
            pygame.draw.ellipse(self.banner, bcolor, (30 + 70 * i, 110, 60, 40))
            pygame.draw.rect(self.banner, color, (54 + 70 * i, 70, 15, 75))
            pygame.draw.polygon(self.banner, color,
                                [(30 + 70 * i, 130), (46 + 70 * i, 130), (60 + 70 * i, 90), (75 + 70 * i, 130),
                                 (90 + 70 * i, 130), (60 + 70 * i, 50)])
        elif self.plan.index == 3:
            pygame.draw.ellipse(self.banner, bcolor, (30 + 70 * i, 110, 60, 40))
            pygame.draw.rect(self.banner, color, (35 + 70 * i, 95, 20, 35))
            pygame.draw.rect(self.banner, color, (65 + 70 * i, 95, 20, 35))
            pygame.draw.rect(self.banner, color, (55 + 70 * i, 110, 20, 20))
        elif self.plan.index == 4:
            pygame.draw.ellipse(self.banner, bcolor, (30 + 70 * i, 110, 60, 40))
            pygame.draw.rect(self.banner, color, (30 + 70 * i, 110, 60, 20))
            pygame.draw.rect(self.banner, color, (50 + 70 * i, 100, 20, 20))
        elif self.plan.index == 5:
            pygame.draw.ellipse(self.banner, bcolor, (30 + 70 * i, 110, 60, 40))
            pygame.draw.rect(self.banner, color, (60 + 70 * i, 85, 10, 45))
            pygame.draw.rect(self.banner, color, (30 + 70 * i, 80, 35, 10))
            pygame.draw.circle(self.banner, color, (65 + 70 * i, 85),10)


    def draw(self):
        self.parent.draw_structures()
        self.draw_text(self.plan.name, (0, 0), large=True)
        self.draw_tuples(self.getstoregraph(), 400)

        if self.parent.owner != Team.UI_base:
            self.draw_button_disabled("you are not the owner", (0, 50, 400, 50))
            return
        if self.plan.index == 0:
            for i, p in enumerate(plans()):
                if p is emptyplan:
                    continue
                self.draw_index_button("build {}".format(p.name),i-1,300,partial(self.build, p.key),
                                       not all(v >= p.cost.get(k, 0) for k, v in self.parent.storage.items()))
                # if all(v >= p.cost.get(k, 0) for k, v in self.parent.storage.items()):
                #     self.draw_button("{}: build {}".format(i + 1, p.name), (0, i * 50, 300, 50),
                #                      partial(self.build, p.key))
                # else:
                #     self.draw_button_disabled("{}: cannot build {}".format(i, p.name), (0, i * 50, 300, 50))
                for j, (k, v) in enumerate(p.cost.items()):
                    self.draw_text("{}:{:>4}/{:>4.0f}".format(k.name[0].upper(), v, self.parent.storage[k]),
                                   (300, i * 50 + 15 * j + 3),
                                   (0, 63, 0) if v <= self.parent.storage[k] else (255, 0, 0))
        else:
            self.draw_index_button("destroy", 0, 400, partial(self.build, ""))
            self.draw_index_button("repair", 1, 400, partial(self.repair))
        if self.plan.index == 1:
            pass
        elif self.plan.index == 2:
            pass
        elif self.plan.index == 3:
            self.draw_index_button("start trade route" if self.graph.trade_connect is None else "connect trade route",
                             2, 400,partial(self.graph.connect_trade_route,self.parent))
        elif self.plan.index == 4:
            self.draw_index_button("build fleet" if self.fleet is None else "edit fleet",
                             2, 400, partial(self.buildfleet,self))

    def build(self, key):
        if not all(v >= plan(key).cost.get(k, 0) for k, v in self.parent.storage.items()):
            return
        self.plan = plan(key)
        self.parent.storage -= self.plan.cost
        self.health = 100*(self.plan != emptyplan)

    def repair(self):
        if not all(v >= self.plan.cost.get(k, 0)*(1-self.health/100) for k, v in self.parent.storage.items()):
            return
        self.parent.storage -= {k:self.plan.cost.get(k, 0)*(1-self.health/100) for k, v in self.parent.storage.items()}
        self.health = 100*(self.plan != emptyplan)

    def escape(self):
        self.parent.show()

    def getstoregraph(self):
        yield ("population", str(self.parent.population))
        for k in self.parent.solvents:
            yield (k.name, "{:>10.3f} kt".format(self.parent.storage[k]))
        for k in self.parent.metals:
            yield (k.name, "{:>10.3f} kt".format(self.parent.storage[k]))

    def gametick(self):
        self.parent.storage += self.parent.solvents
        if self.plan.index == 0:
            self.health = 0
            return
        self.parent.storage -= {self.parent.active_solvent: 0.1}
        if self.health <= 0:
            self.plan = emptyplan
            self.health = 0
        if self.parent.storage[self.parent.active_solvent] < 0.1:
            self.plan = emptyplan
            self.parent.storage[self.parent.active_solvent] += 300

        if self.plan.index == 2:
            self.parent.storage += self.parent.metals


    def buildfleet(self,parent):
        if self.fleet is None:
            self.fleet = FleetBuilder(parent)
        self.fleet.show()
    def perform(self):
        if self.plan == plan("L"):
            self.buildfleet(self)

def distance(source,target):
    return math.sqrt((source.pos[0]- target.parent.pos[0])**2 +
                              (source.pos[1]- target.parent.pos[1])**2)

class TradeRoute:
    all_ = []
    @classmethod
    def build(cls,begin,end):
        if not (begin.can_trade and end.can_trade):
            return None
        if begin == end:
            return None
        for t in TradeRoute.all_:
            if {t.begin,t.end} == {begin,end}:
                return None
        counter = 0
        for t in TradeRoute.all_:
            if {t.begin,t.end} & {begin,end}:
                counter += 1
        if counter >= 3:
            return None
        return cls(begin,end)

    def __init__(self, begin, end):
        self.begin = begin
        self.end = end
        TradeRoute.all_.append(self)

    def gametick(self):
        if self.begin.owner != self.end.owner:
            TradeRoute.all_.remove(self)
            del self
            return
        for k in self.begin.storage:
            TradeRoute.handle(k,1,[self.begin,self.end])

    @staticmethod
    def handle(kind,amount,planets):
        planets.sort(key=lambda x: x.storage[kind])
        low, high = planets
        if low.storage[kind] + amount > high.storage[kind]:
            return
        low.storage[kind] += amount
        high.storage[kind] -= amount

    @classmethod
    def autoconnect(cls,target):
        planets = chain(*(s.planets for s in Star.all_))
        team = target.owner
        closest = sorted((p for p in planets if p.owner == team and target != p and
                          sum(p in (f.begin,f.end) for f in TradeRoute.all_) <= 3),
                                 key=lambda x:distance(target.parent,x))[0]
        return cls(closest,target)

class FleetBuilder(ViewPort):
    def __init__(self,parent):
        self.parent = parent
        self.planet = self.parent.parent
        self.ships = Counter({s.key:0 for s in ships()})

    def draw(self):
        self.planet.draw_structures()
        self.graph.last_fleet = self
        self.draw_text("Build fleet", (0, 0), large=True)
        for i,s in enumerate(ships()):
            self.draw_index_button("build {:>15} x{}".format(s.name,self.ships[s.key]), i, 300,
                                     partial(self.add_ship, s),alt=partial(self.add_ship, s, -1))
            for j, (k, v) in enumerate(s.cost.items()):
                self.draw_text("{}:{:>4}/{:>4.0f}".format(k.name[0].upper(), v, self.planet.storage[k]),
                               (300, i * 50 + 15 * j + 53),
                               (0, 63, 0) if v <= self.planet.storage[k] else (255, 0, 0))
        #self.draw_index_button("launch".format(s.name), i+1, 300,partial(self.launch, self.graph.battle_connect))
        self.draw_directory(OrderedDict(self.getinfo()),400)
    def add_ship(self,ship,rel=1):
        #if not all(v >= ship.cost.get(k, 0) for k, v in self.planet.storage.items()):
        #    return
        self.ships += {ship.key:rel}



    def getinfo(self):
        for i,m in enumerate(metals()):
            yield (m.name, "{:>4}/{:>4.0f}".format(sum(ship(s).cost.get(m,0) for s in self.ships),self.planet.storage[m]))

    def launch(self,target):
        totcost = sum((ship(s).cost for s in self.ships.elements()),Counter())
        if not all(v >= totcost.get(k, 0) for k, v in self.planet.storage.items()):
            return
        self.planet.storage -= totcost
        if target is None or not any(s for s in self.ships.values()):
            return
        FleetFlying(self,target)
        #self.parent.fleet = None
        #self.escape()
        #del self

    def escape(self):
        self.parent.show()

class FleetFlying:
    all_ = []
    def __init__(self,builder,target):
        self.builder = builder
        self.ships = builder.ships.copy()
        self.start = builder.planet
        self.target = target
        self.missiles = []
        if self.target == self.start:
            print("Check targets")
        self.distance = math.sqrt((self.start.parent.pos[0]- target.parent.pos[0])**2 +
                                  (self.start.parent.pos[1]- target.parent.pos[1])**2)
        self.traveled = 0
        FleetFlying.all_.append(self)
        if self.distance == 0:
            self.arrive()

    def delete(self):
        FleetFlying.all_.remove(self)

    def gametick(self):
        self.traveled += 0.2
        self.missiles = [i-0.8 for i in self.missiles]
        if self.missiles and self.missiles[0] < self.traveled:
            self.missiles.pop(0)
            self.ships = FleetBattle.apply_damage(self.ships,10)
            if not any(self.ships.values()):
                self.delete()
                del self
                return

        if self.traveled >= self.distance:
            self.arrive()

    def create_missile(self):
        self.missiles.append(self.distance)

    def displaypos(self,startpos=...,endpos=...):
        if startpos==...:
            startpos = self.start.parent.pos
        if endpos==...:
            endpos = self.target.parent.pos
        for i in (self.traveled,) + tuple(self.missiles):
            reldist = i / self.distance
            relx = (endpos[0] - startpos[0])*reldist + startpos[0]
            rely = (endpos[1] - startpos[1])*reldist + startpos[1]
            yield int(relx),int(rely)

    def arrive(self):
        FleetBattle(self)
        self.delete()
        del self


class FleetBattle:
    all_ = []
    def __init__(self,flyer):
        self.loc = flyer.target
        self.ships = flyer.ships
        self.owner = flyer.start.owner
        self.counter = 0
        FleetBattle.all_.append(self)
    def perform_attack(self):
        #if self.loc.owner == None:
        #    self.victory()
        #    return

        if not any(self.ships.values()):
            self.defeat()
            return

        for s in self.loc.structures:
            s.health -= self.get_power()
            if s.plan == plan("S"):
                self.ships = FleetBattle.apply_damage(self.ships,20)

        if all(s.plan == emptyplan for s in self.loc.structures):
            self.victory()

    def victory(self):
        self.loc.owner = self.owner
        TradeRoute.autoconnect(self.loc)
        self.loc.structures[0].plan = plan("T")
        self.loc.structures[0].health = 100
        if self.get_builder():
            self.loc.structures[2].plan = plan("M")
            self.loc.structures[2].health = 100
        self.loc.storage[self.loc.active_solvent] = 500
        FleetBattle.all_.remove(self)
        del self
        print("victory")

    def defeat(self):
        FleetBattle.all_.remove(self)
        del self
        print("defeat")

    def get_power(self):
        return sum(ship(s).power * v for s,v in self.ships.items())

    def get_builder(self):
        return any(ship(s).build * v for s,v in self.ships.items())

    @staticmethod #can be used for stelular missiles on FleetFlying
    def apply_damage(ships,amount):
        while amount > 0:
            countships = sum(ships.values())
            if countships == 0:
                break
            index = random.randrange(countships)
            targetship = next(islice(ships.elements(), index, None))
            amount -= ship(targetship).defence
            ships[targetship] -= 1
        return ships

    def gametick(self):
        if not self.counter % 60:
            self.perform_attack()
        self.counter += 1

def run_update_tick():
    for s in Star.all_:
        s.gametick()
    for t in TradeRoute.all_:
        t.gametick()
    for f in FleetFlying.all_:
        f.gametick()
    for f in FleetBattle.all_:
        f.gametick()
    for t in Team.all_:
        t.gametick()

