__author__ = 'thorvald'

from core import *
from itertools import chain

class AI:
    def __init__(self,team,cripple=60):
        self.team = team
        self.ants = [] #ant AI
        self.planets = list(chain(*(s.planets for s in Star.all_)))
        self.counter = 0
        self.cripple = cripple
        for p in self.planets:
            if p.owner is self.team:
                PlanetBuilder(p,self)
    def gametick(self):
        self.counter += 1
        if not self.counter % self.cripple:
            for i in self.ants:
                i.gametick()


class PlanetBuilder:
    @classmethod
    def add(cls,planet,master):
        if planet.owner == master.team:
            cls(planet,master)
        else:
            print("Planet has incorrect owner")
    def __init__(self,planet,master):
        print("Start building planet")
        self.planet = planet
        self.master = master
        self.battler = None
        self.master.ants.append(self)

    def gametick(self):
        self.build_all()
        if self.master.team != self.planet.owner:
            print("Lost planet")
            self.master.ants.remove(self)
        if self.planet.structures[3].plan == plan("L"):
            if self.battler is None:
                self.battler = PlanetBattler.add(self.planet,self.master)

    def build_all(self):
        for i,(k,s) in enumerate(zip("TCMLS",self.planet.structures)):
            if s.plan != plan(k):
                s.build(k)
                return(False)
        return(True)

class PlanetBattler:
    @classmethod
    def add(cls,planet,master):
        if planet.owner == master.team:
            return cls(planet,master)
        else:
            print("Planet has incorrect owner")
    def __init__(self,planet,master):
        print("Start conquering planet")
        self.planet = planet
        self.master = master
        self.takeovers = 0
        self.targetlist = sorted((p for p in self.master.planets
                                  if p.buildable and p.owner != self.master.team and
                                  not any(isinstance(s,type(self)) and p in s.goto_list for s in self.master.ants))
                                 ,key=lambda x:distance(self.planet.parent,x))
        print(self.targetlist)
        self.goto_list = []
        self.master.ants.append(self)


    def gametick(self):
        for t in self.goto_list:
            if t.owner == self.master.team:

                #if self.buildtraderoute(t):
                print("Linked a planet")
                PlanetBuilder(t,self.master)
                self.goto_list.remove(t)
                return
            if not any(f.start == self.planet and f.target == t for f in FleetFlying.all_) and \
                not any(f.loc == t and f.owner == self.master.team for f in FleetBattle.all_):
                self.goto_list.remove(t)
                print("Failed Conquer")
        if len(self.goto_list)<3:#+sum(self.planet in (f.begin,f.end) for f in TradeRoute.all_)<3:
            try:
                t = self.targetlist.pop(0)
            except IndexError:
                print("TARGETTING ERROR")
                self.master.ants.remove(self)
                return
            if any(f.target == t and f.start.owner == self.master.team for f in FleetFlying.all_) or \
                any(f.loc == t and f.owner == self.master.team for f in FleetBattle.all_):
                self.targetlist.append(t)
                return
            if distance(self.planet.parent,t) > 200:
                print("TO FAR")
                return
            if t.owner == self.master.team:
                self.targetlist.append(t)
                return
            self.goto_list.append(t)
            builder = FleetBuilder(self.planet.structures[3])
            if t.owner is None:
                print("started claim")
                builder.add_ship(ship("C"))
            elif t.owner != self:
                print("started attack")
                builder.add_ship(ship("D"))
                builder.add_ship(ship("D"))
                builder.add_ship(ship("C"))
                builder.add_ship(ship("W"))
                builder.add_ship(ship("W"))
                builder.add_ship(ship("B"))
                builder.add_ship(ship("B"))
                builder.add_ship(ship("B"))
                builder.add_ship(ship("B"))
                builder.add_ship(ship("B"))
                builder.add_ship(ship("P"))
                builder.add_ship(ship("P"))
            else:
                print("Already owned")
                self.targetlist.remove(t)
                return
            FleetFlying(builder,t)
    def buildtraderoute(self,target):
        closest = sorted((p for p in self.master.planets if p.owner == self.master.team and target != p and
                          sum(p in (f.begin,f.end) for f in TradeRoute.all_) < 3),
                                 key=lambda x:distance(target.parent,x))[0]
        return TradeRoute.build(closest,target) is not None

