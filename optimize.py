#! /usr/bin/env python3

import argparse
import collections
import csv
import math
from frozendict import frozendict
import heapq
import sys
import time
from tqdm import tqdm
from typing import *

parser = argparse.ArgumentParser(description='Generate an optimal Cookie Clicker build')
parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
parser.add_argument('end_time', type=int, help="Game time to generate a plan for")
parser.add_argument('-r', '--report_interval', type=int, default=0,
    help='Report progress every N seconds (0=off)')
parser.add_argument('--human', action='store_true', help="Simulate a human clicker (and don't start with a cursor)")
args = parser.parse_args()

end_time = args.end_time
DEBUG = args.debug


Thing = collections.namedtuple('Thing', ['name', 'base_cost', 'rate'])

BUILDABLES = []

with open('things.csv', 'r') as f:
    for row in csv.DictReader(f):
        obj = Thing(
            name=row['name'],
            base_cost=int(row['base_cost']),
            rate=float(row['rate']))
        BUILDABLES.append(obj)

THINGS = [Thing('Human', math.inf, 4)] + BUILDABLES
THINGNAMES = {t.name:t for t in THINGS}
THINGNAMES_SORTED = [t.name for t in THINGS]

def cost(thing, count):
    return math.ceil(thing.base_cost * (1.15 ** count))

def rate(thing, count):
    return thing.rate * count

class State:
    def __init__(self, data=None, parent=None, step=None):
        self._data = {thing:0 for thing in THINGS}
        if data is not None:
            assert all(k in THINGS for k in data)
            self._data.update(data)

        self._data = frozendict(self._data)
        self._parent = parent
        self.step = step

    def __hash__(self):
        return hash(self._data)

    def __eq__(self, other):
        return self._data == other._data

    def __quantity_key(self):
        k=[]
        for n in THINGNAMES_SORTED:
            if n in self._data:
                k.append(self._data[n])
            else:
                k.append(0)
        return tuple(k)

    def __lt__(self, other):
        """WARNING: this is a hack to enable heapq to deal with heaps involving this class"""
        return self.__quantity_key() < other.__quantity_key()

    def __str__(self):
        return '{' + ', '.join('{}:{}'.format(t.name, self._data[t]) for t in THINGS if self._data[t]>0) + '}'

    def __repr__(self):
        return self.__str__()

    def add(self, thing):
        data = {t:self._data[t] for t in THINGS}
        data[thing] += 1
        return State(data=data, parent=self, step=thing)

    def decrement(self, thing):
        data = {t:self._data[t] for t in THINGS}
        data[thing] -= 1
        # Not super clear that parent or step are meaningful in this context
        return State(data=data, parent=None, step=None)

    def rate(self):
        return sum(rate(t, self._data[t]) for t in THINGS)

    def cost(self, thing):
        return cost(thing, self._data[thing])

    def plan(self):
        if self._parent is None:
            return [self]
        else:
            return self._parent.plan() + [self]

    def dominated_states(self):
        """Returns a list of states that are strictly worse than the current state.

        Note that this only returns states that have one less of a buildable than the current state;
        you'll need to roll the recursive case on your own.
        """
        # Intentionally using BUILDABLES not THINGS here because the latter may include a "human",
        # which you cannot buy and hence cannot remove.
        return [self.decrement(thing) for thing in BUILDABLES if self._data[thing] > 0]

min_times = {}
next_heap = []
best_rate = 0
best_state = None

def enqueue(state, time):
    if state in min_times and min_times[state] < time:
        return

    heapq.heappush(next_heap, (time, state))
    min_times[state] = time

if args.human:
    enqueue(
        State(
            {
                THINGNAMES['Human']:1,
            },
            parent=None,
            step=THINGNAMES['Human']),
        0)
else:
    enqueue(
        State(
            {
                THINGNAMES['Cursor']:1,
            },
            parent=None,
            step=THINGNAMES['Cursor']),
        0)

def vprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def vpn(*args, **kwargs):
    vprint(*args, end=' ', **kwargs)

now = 0

def find_dominated_states() -> Set[State]:
    """Find the set of states that are dominated by some other state."""
    dominated_states = set()
    for state in tqdm([k for k in min_times.keys() if min_times[k] <= now], desc='Enumerating dominated states'):
        todo = state.dominated_states()
        while len(todo) > 0:
            s = todo.pop()
            if s not in dominated_states:
                dominated_states.add(s)
                todo.extend(x for x in s.dominated_states() if x not in dominated_states)

    return [s for _, s in next_heap if s in dominated_states]

count = 0
expanded = 0
skipped = 0
earliest_after_end = math.inf
last_report = time.time()
with tqdm(total=end_time) as pbar:
    while now <= end_time:
        count += 1
        now, state = heapq.heappop(next_heap)
        pbar.n = now
        pbar.set_description(
            f'{count}/{len(next_heap)}/{len(next_heap)+count} {len(min_times)} visited {expanded}/{expanded+skipped} expanded')
        vpn(now, len(next_heap), state)
        vpn('BEST:', best_rate, best_state)

        if args.report_interval > 0 and time.time() - last_report > args.report_interval:
            last_report = time.time()
            # Print best to stderr
            print(f'BEST: {best_rate} {best_state}', file=sys.stderr)

        if state in min_times and min_times[state] < now:
            vprint('SKIP', min_times[state])
            skipped += 1
            continue

        vprint()

        r = state.rate()
        if r > best_rate:
            best_rate = r
            best_state = state

        expanded += 1
        for option in BUILDABLES:
            time_reached = state.cost(option) / r + now

            if time_reached > end_time:
                earliest_after_end = min(earliest_after_end, time_reached)
                if time_reached > earliest_after_end:
                    continue

            newstate = state.add(option)
            enqueue(newstate, time_reached)
            vprint(' ->', time_reached, newstate)




print(' BEST PLAN:', best_rate, best_state)
for state in best_state.plan():
    print('  -', min_times[state], state.step.name, '->', state, state.rate())
