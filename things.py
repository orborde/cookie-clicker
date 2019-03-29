import collections
import csv
import math

Thing = collections.namedtuple('Thing', ['name', 'base_cost', 'rate'])

THINGS = []
THINGNAMES = {}
with open('things.csv', 'r') as f:
    for row in csv.DictReader(f):
        obj = Thing(
            name=row['name'],
            base_cost=int(row['base_cost']),
            rate=float(row['rate']))
        THINGS.append(obj)
        THINGNAMES[obj.name] = obj

def cost(thing, count):
    return math.ceil(thing.base_cost * (1.15 ** count))

def rate(thing, count):
    return thing.rate * count
