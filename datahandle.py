__author__ = 'thorvald'


from collections import namedtuple,OrderedDict,Counter
import json


def makecolor(*rgb):
    return tuple(int(min(max(float(i), 0), 255)) for i in rgb)



Metal = namedtuple("Metal", "name,color,key")
Solvent = namedtuple("Solvent", "name,color,key,mintemp,maxtemp,minpress,maxpress,creaturename,citycolor")
Plan = namedtuple("Plan", "name,index,key,cost")
Ship = namedtuple("Ship","name,color,key,power,defence,build,cost")
# empty = Plan("none", 0, "", {})

class Substances:
    instance = None

    def __init__(self):
        Substances.instance = self
        self.data = json.load(open("data.json"), object_pairs_hook=OrderedDict)
        self.metals = list(self.get_metals())
        self.solvents = list(self.get_solvents())
        self.plans = list(self.get_plans())
        self.ships = list(self.get_ships())
        print(self.solvents)

    def get_metals(self, key=None):
        for k, v in self.data["metals"].items():
            if key is None or key == v["key"]:
                yield (Metal(k, makecolor(*v["color"]), v["key"]))

    def get_solvents(self, key=None):
        for k, v in self.data["solvents"].items():
            if key is None or key == v["key"]:
                yield (Solvent(k, makecolor(*v["color"]), v["key"],
                               float(v["temp"][0]), float(v["temp"][1]),
                               float(v["press"][0]), float(v["press"][1]),
                               v["creature"],makecolor(*v["creature_color"])
                               ))

    def get_plans(self, key=None):
        for k, v in self.data["plans"].items():
            if key is None or key == v["key"]:
                yield (Plan(k, v["action"], v["key"],
                            Counter({[m for m in self.metals if m.key == kk][0]: vv for kk, vv in v["cost"].items()})))

    def get_ships(self, key=None):
        for k, v in self.data["ships"].items():
            if key is None or key == v["key"]:
                yield (Ship(k, makecolor(*v["color"]), v["key"],
                               v["power"],v["defence"],v["build"],
                               Counter({[m for m in self.metals if m.key == kk][0]: vv for kk, vv in v["cost"].items()})
                               ))

Substances()


def metals():
    return Substances.instance.metals


def solvents():
    return Substances.instance.solvents


def plans():
    return Substances.instance.plans


def ships():
    return Substances.instance.ships



def metal(key):
    for i in metals():
        if i.key == key:
            return (i)


def solvent(key):
    for i in solvents():
        if i.key == key:
            return (i)


def plan(key):
    for i in plans():
        if i.key == key:
            return (i)

def ship(key):
    for i in ships():
        if i.key == key:
            return (i)

emptyplan = plan("")
