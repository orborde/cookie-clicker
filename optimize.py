#! /usr/bin/env python3

import argparse
from math import inf
from frozendict import frozendict
import heapq
import sys
import time
from tqdm import tqdm

parser = argparse.ArgumentParser(description='Generate an optimal Cookie Clicker build')
parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
parser.add_argument('end_time', type=int, help="Game time to generate a plan for")
parser.add_argument('-r', '--report_interval', type=int, default=0,
    help='Report progress every N seconds (0=off)')
args = parser.parse_args()

end_time = args.end_time
DEBUG = args.debug

from things import *

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
        return '{' + ', '.join('{}:{}'.format(t.name, self._data[t]) for t in THINGS) + '}'

    def __repr__(self):
        return self.__str__()

    def add(self, thing):
        data = {t:self._data[t] for t in THINGS}
        data[thing] += 1
        return State(data=data, parent=self, step=thing)

    def rate(self):
        return sum(rate(t, self._data[t]) for t in THINGS)

    def cost(self, thing):
        return cost(thing, self._data[thing])

    def plan(self):
        if self._parent is None:
            return [self]
        else:
            return self._parent.plan() + [self]

min_times = {}
next_heap = []
best_rate = 0
best_state = None

def enqueue(state, time):
    if state in min_times and min_times[state] < time:
        return

    heapq.heappush(next_heap, (time, state))
    min_times[state] = time

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
count = 0
expanded = 0
skipped = 0
earliest_after_end = inf
last_report = time.time()
with tqdm(total=end_time) as pbar:
    while now <= end_time:
        count += 1
        new_now, state = heapq.heappop(next_heap)
        pbar.update(new_now - now)
        pbar.set_description(
            f'{count}/{len(next_heap)}/{len(next_heap)+count} {len(min_times)} visited {expanded}/{expanded+skipped} expanded')
        now = new_now
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
