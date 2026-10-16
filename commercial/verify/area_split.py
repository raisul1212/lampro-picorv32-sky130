#!/usr/bin/env python3
"""Standard-cell area of the shipped netlists, from the tt liberty only (adapted from the Lampro AI
campaign release script tools/area_split.py, commit 818d913e586ad6e11418ba5b776a564db61887de).

  area_split.py --liberty sky130_fd_sc_hd__tt_025C_1v80.lib [--lef sky130_fd_sc_hd.lef] [--out DIR]

For each of netlist/picorv32.synth.v, picorv32.routed.v and picorv32.routed.pg.v it counts every
instance once, classifies it, and sums the liberty area. Tap, fill and decap cells are counted and
reported but excluded from the comparison total (area of cells absent from the liberty is read from the
LEF SIZE when --lef is given). A cell master that is not in the liberty and is not tap/fill/decap is
refused, not dropped. Antenna diodes and every other class are included and reported. Sums are exact
decimals; areas are displayed to four decimals. This is a liberty-based cell-area sum: it is not die
area or utilization.

Writes DIR/cells.csv, DIR/summary.json and DIR/provenance.json (default: reports/area).
Needs only the standard library.
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
import hashlib
from pathlib import Path
import re
import shlex
import sys


CLASSES = ('Flops', 'Mux', 'Complex gates', 'Simple gates', 'Buffers',
           'Clock tree', 'Hold buffers', 'Diodes', 'Tie')
PHYSICAL = ('Tap', 'Fill', 'Decap')
ZERO = Decimal(0)
IDENT = r'(?:\\[^\s]+\s+|[A-Za-z_$][\w$]*)'
INSTANCE = re.compile(rf'\s*({IDENT})\s+({IDENT})\s*\((.*)\)\s*', re.S)
PIN = re.compile(r'\s*\.([\w$]+)\s*\(([^()]*)\)\s*', re.S)


@dataclass
class Cell:
    area: Decimal
    sequential: bool
    clocks: tuple


@dataclass
class Instance:
    cell: str
    name: str
    pins: dict


def family(cell):
    if not cell.startswith('sky130_fd_sc_hd__'):
        raise ValueError(f'not a sky130 HD cell: {cell}')
    return cell.split('__', 1)[1].rsplit('_', 1)[0]


def physical(cell):
    if not cell.startswith('sky130_fd_sc_hd__'):
        return None
    f = family(cell)
    return {'tapvpwrvgnd': 'Tap', 'fill': 'Fill', 'decap': 'Decap'}.get(f)


def liberty(path):
    text = path.read_text(encoding='utf-8')
    starts = list(re.finditer(r'\bcell\s*\(\s*"?([^"\s)]+)"?\s*\)\s*\{', text))
    result = {}
    for i, match in enumerate(starts):
        block = text[match.end():starts[i + 1].start() if i + 1 < len(starts) else len(text)]
        area = re.search(r'\barea\s*:\s*([\d.]+)\s*;', block)
        if not area or match[1] in result:
            raise ValueError(f'missing area or duplicate liberty cell: {match[1]}')
        pins = list(re.finditer(r'\bpin\s*\(\s*"?([^"\s)]+)"?\s*\)\s*\{', block))
        clocks = []
        for j, pin in enumerate(pins):
            body = block[pin.end():pins[j + 1].start() if j + 1 < len(pins) else len(block)]
            if re.search(r'\bclock\s*:\s*"?true"?\s*;', body):
                clocks.append(pin[1])
        result[match[1]] = Cell(Decimal(area[1]), bool(re.search(r'\b(?:ff|latch)\s*\(', block)), tuple(clocks))
    if not result:
        raise ValueError(f'no liberty cells: {path}')
    return result


def signal(text):
    return text.strip().removeprefix('\\').replace(' ', '')


def netlist(path):
    text = path.read_text(encoding='utf-8')
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    if len(re.findall(r'\bmodule\b', text)) != 1:
        raise ValueError(f'expected one flat module: {path}')
    instances, aliases, names = [], [], set()
    for statement in text.split(';'):
        statement = statement.strip()
        if not statement or statement == 'endmodule':
            continue
        keyword = statement.split(None, 1)[0]
        if keyword in ('module', 'input', 'output', 'inout', 'wire'):
            continue
        if keyword == 'assign':
            alias = re.fullmatch(rf'assign\s+({IDENT})\s*=\s*({IDENT})\s*', statement)
            if alias:
                aliases.append((signal(alias[1]), signal(alias[2])))
            continue
        match = INSTANCE.fullmatch(statement)
        if not match:
            raise ValueError(f'unsupported netlist statement in {path}: {statement[:100]}')
        cell, name, body = match.groups()
        cell, name = cell.strip().removeprefix('\\'), name.strip().removeprefix('\\')
        if name in names:
            raise ValueError(f'duplicate instance {name} in {path}')
        names.add(name)
        pins = {}
        for connection in body.split(',') if body.strip() else ():
            pin = PIN.fullmatch(connection)
            if not pin or pin[1] in pins:
                raise ValueError(f'unsupported/duplicate pin in {path}: {name}')
            pins[pin[1]] = signal(pin[2])
        instances.append(Instance(cell, name, pins))
    if not instances:
        raise ValueError(f'no cell instances: {path}')
    return instances, aliases


def validate(instances, cells, count_only_physical=False):
    missing = Counter(i.cell for i in instances if i.cell not in cells
                      and not (count_only_physical and physical(i.cell)))
    if missing:
        raise ValueError('missing liberty cells: ' + ', '.join(f'{c} ({n})' for c, n in sorted(missing.items())))


def clock_instances(instances, aliases, cells):
    """Trace backward from liberty clock pins through buffer/inverter nets."""
    nets, drivers = set(), defaultdict(list)
    for i in instances:
        if i.cell in cells:
            nets.update(i.pins[p] for p in cells[i.cell].clocks if p in i.pins)
        if i.cell.startswith('sky130_fd_sc_hd__'):
            f = family(i.cell)
            if f.startswith(('buf', 'clkbuf', 'clkinv', 'inv', 'clkdlybuf', 'dlygate')):
                for p in ('X', 'Y'):
                    if p in i.pins:
                        drivers[i.pins[p]].append(i)
    adjacency = defaultdict(set)
    for a, b in aliases:
        adjacency[a].add(b)
        adjacency[b].add(a)
    pending, seen, clock = list(nets), set(), set()
    while pending:
        net = pending.pop()
        if net in seen:
            continue
        seen.add(net)
        pending.extend(adjacency[net] - seen)
        for i in drivers[net]:
            clock.add(i.name)
            if 'A' in i.pins:
                pending.append(i.pins['A'])
    return clock


def classify(i, cells, clock):
    excluded = physical(i.cell)
    if excluded:
        return excluded
    f = family(i.cell)
    if cells[i.cell].sequential:
        return 'Flops'
    if f.startswith(('clkdlybuf', 'dlygate', 'dlymetal')) or re.fullmatch(r'hold\d+', i.name):
        return 'Hold buffers'
    if (i.name in clock or i.name.startswith(('clkbuf_', 'clknet_'))
            or re.fullmatch(r'clkload\d+', i.name)):
        return 'Clock tree'
    if f.startswith(('mux2', 'mux4')):
        return 'Mux'
    if re.match(r'[ao]\d', f) or f in ('ha', 'fa', 'fah', 'fahcin', 'fahcon', 'maj3'):
        return 'Complex gates'
    if f.startswith(('nand', 'nor', 'and', 'or', 'xor', 'xnor', 'inv', 'clkinv')):
        return 'Simple gates'
    if f.startswith(('buf', 'clkbuf')):
        return 'Buffers'
    if f == 'diode':
        return 'Diodes'
    if f == 'conb':
        return 'Tie'
    raise ValueError(f'unclassified cell family: {i.cell}')


def measure(parsed, cells, count_only_physical):
    instances, aliases = parsed
    validate(instances, cells, count_only_physical)
    clock = clock_instances(instances, aliases, cells)
    counts, areas, unavailable = Counter(), defaultdict(lambda: ZERO), set()
    for i in instances:
        cls = classify(i, cells, clock)
        counts[cls] += 1
        if i.cell in cells:
            areas[cls] += cells[i.cell].area
        else:
            unavailable.add(cls)
    return counts, areas, unavailable


def lef_sizes(path):
    """MACRO name -> area from the SIZE statement (um2)."""
    sizes, cur = {}, None
    for line in path.read_text(encoding='utf-8').splitlines():
        m = re.match(r'\s*MACRO\s+(\S+)', line)
        if m:
            cur = m[1]
        m = re.match(r'\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', line)
        if m and cur:
            sizes[cur] = Decimal(m[1]) * Decimal(m[2])
            cur = None
    return sizes


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--liberty', type=Path, required=True)
    parser.add_argument('--lef', type=Path)
    parser.add_argument('--pkg', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    out = args.out or args.pkg / 'reports' / 'area'
    try:
        cells = liberty(args.liberty)
        lef = lef_sizes(args.lef) if args.lef else {}
        names = ('picorv32.synth.v', 'picorv32.routed.v', 'picorv32.routed.pg.v')
        rows, summary = [], {}
        for name in names:
            path = args.pkg / 'netlist' / name
            inst, aliases = netlist(path)
            validate(inst, cells, True)
            clock = clock_instances(inst, aliases, cells)
            per = Counter()
            cls_of = {}
            for i in inst:
                c = classify(i, cells, clock) if i.cell in cells else physical(i.cell) or classify(i, cells, clock)
                per[(i.cell, c)] += 1
            by_class, counts, excluded = defaultdict(lambda: ZERO), Counter(), {}
            for (cell, c), n in sorted(per.items()):
                if cell in cells:
                    unit, src = cells[cell].area, 'liberty'
                elif cell in lef:
                    unit, src = lef[cell], 'LEF SIZE'
                else:
                    unit, src = None, 'not in liberty or LEF'
                inc = c in CLASSES
                contrib = None if unit is None else unit * n
                rows.append((name, cell, c, n, '' if unit is None else f'{unit:.4f}', '' if contrib is None else f'{contrib:.4f}',
                             'included' if inc else 'excluded (tap/fill/decap)', src))
                counts[c] += n
                if inc:
                    by_class[c] += contrib
                else:
                    excluded.setdefault(c, {'instances': 0, 'area_um2': ZERO if unit is not None else None})
                    excluded[c]['instances'] += n
                    if contrib is None:
                        excluded[c]['area_um2'] = None
                    elif excluded[c]['area_um2'] is not None:
                        excluded[c]['area_um2'] += contrib
            total = sum(by_class.values(), ZERO)
            summary[name] = {
                'sha256': sha(path),
                'instances_included': sum(counts[c] for c in CLASSES),
                'instances_all': sum(counts.values()),
                'area_included_um2': f'{total:.4f}',
                'by_class_um2': {c: f'{by_class[c]:.4f}' for c in CLASSES if by_class[c]},
                'by_class_instances': {c: counts[c] for c in CLASSES if counts[c]},
                'excluded': {c: {'instances': v['instances'], 'area_um2': None if v['area_um2'] is None else f"{v['area_um2']:.4f}"}
                             for c, v in excluded.items()},
            }
            if 'Tap' in excluded and excluded['Tap']['area_um2'] is not None:
                summary[name]['area_including_taps_um2'] = f"{total + excluded['Tap']['area_um2']:.4f}"
    except (ValueError, OSError) as error:
        print(f'area_split: REFUSED: {error}', file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    with open(out / 'cells.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(('netlist', 'cell_master', 'class', 'population', 'unit_area_um2', 'contribution_um2', 'inclusion', 'area_source'))
        w.writerows(rows)
    (out / 'summary.json').write_text(json.dumps({
        'definition': 'Sum of liberty cell areas of all instances in the netlist, excluding tap, fill and decap cells; unrounded decimal sums, displayed to four decimals. Not die area or utilization.',
        'netlists': summary}, indent=1) + '\n', encoding='utf-8')
    prov = {'command': 'python3 verify/area_split.py --liberty <tt liberty> [--lef <LEF>]',
            'liberty_sha256': sha(args.liberty), 'liberty_name': args.liberty.name,
            'lef_sha256': sha(args.lef) if args.lef else None,
            'script': 'verify/area_split.py adapted from the Lampro AI campaign release tools/area_split.py, commit 818d913e586ad6e11418ba5b776a564db61887de'}
    (out / 'provenance.json').write_text(json.dumps(prov, indent=1) + '\n', encoding='utf-8')
    for name, s in summary.items():
        print(f"{name}\t{s['instances_included']} instances\t{s['area_included_um2']} um2 (excluding tap/fill/decap)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
