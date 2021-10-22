#! /usr/bin/env python3

from frozendict import frozendict
import heapq
import sys
from tqdm import tqdm

_, end_time = sys.argv
end_time = int(end_time)

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

DEBUG=False
def vprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def vpn(*args, **kwargs):
    vprint(*args, end=' ', **kwargs)

now = 0
count = 0
expanded = 0
skipped = 0
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
            newstate = state.add(option)
            enqueue(newstate, time_reached)
            vprint(' ->', time_reached, newstate)




print(' BEST PLAN:', best_rate, best_state)
for state in best_state.plan():
    print('  -', min_times[state], state.step.name, '->', state, state.rate())
