#!/usr/bin/env python3
"""Builds assets/activity.svg — a monochrome dot-matrix GitHub activity card.

Data source, in order:
  1. GitHub GraphQL contributions calendar (needs GITHUB_TOKEN, used in Actions);
  2. the public contributions page github.com/users/<login>/contributions (no token).
Run with --sample to render random data for a local preview.
Standard library only.
"""
import argparse, datetime as dt, html, json, math, os, random, re, sys, urllib.request

LOGIN = os.environ.get('GH_LOGIN', 'Dev-Angel-7553')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'activity.svg')

BG, LINE, OFF, MID, FG = '#0a0a0a', '#222222', '#1f1f1f', '#888888', '#ffffff'
MONO = "ui-monospace, 'SF Mono', SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
MONTHS = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

# ---------------------------------------------------------------- data
def from_graphql(token):
    q = {'query': 'query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{'
                  'weeks{contributionDays{date contributionCount}}}}}}', 'variables': {'l': LOGIN}}
    req = urllib.request.Request('https://api.github.com/graphql', data=json.dumps(q).encode(),
                                 headers={'Authorization': f'bearer {token}', 'User-Agent': 'activity-card'})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    weeks = data['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
    return [[(d['date'], d['contributionCount']) for d in w['contributionDays']] for w in weeks]

def from_html():
    req = urllib.request.Request(f'https://github.com/users/{LOGIN}/contributions', headers={'User-Agent': 'activity-card'})
    page = urllib.request.urlopen(req, timeout=30).read().decode()
    tips = {m.group(1): m.group(2) for m in re.finditer(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page)}
    days = {}
    for m in re.finditer(r'<td[^>]*data-date="(\d{4}-\d\d-\d\d)"[^>]*>', page):
        tag = m.group(0)
        idm = re.search(r'id="([^"]+)"', tag)
        tip = html.unescape(tips.get(idm.group(1), '')) if idm else ''
        n = re.match(r'(\d+) contribution', tip)
        days[m.group(1)] = int(n.group(1)) if n else 0
    return weeks_from_days(days)

def weeks_from_days(days):
    dates = sorted(days)
    start = dt.date.fromisoformat(dates[0]); end = dt.date.fromisoformat(dates[-1])
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)          # weeks start on Sunday, like GitHub
    weeks, cur, d = [], [], start
    while d <= end:
        cur.append((d.isoformat(), days.get(d.isoformat(), 0)))
        if len(cur) == 7: weeks.append(cur); cur = []
        d += dt.timedelta(days=1)
    if cur: weeks.append(cur)
    return weeks

def sample():
    end = dt.date.today(); days = {}
    for i in range(365):
        d = end - dt.timedelta(days=i)
        days[d.isoformat()] = random.choice([0] * 7 + [1, 1, 2, 3, 6])
    return weeks_from_days(days)

# ---------------------------------------------------------------- stats
def stats(weeks):
    flat = [c for w in weeks for _, c in w]
    total, active, best = sum(flat), sum(1 for c in flat if c), max(flat or [0])
    streak, seq = 0, flat[:]
    if seq and seq[-1] == 0: seq = seq[:-1]                         # today may still be empty
    for c in reversed(seq):
        if not c: break
        streak += 1
    return total, active, best, streak

# ---------------------------------------------------------------- svg
DIGITS = {
    '0': ['01110', '10001', '10011', '10101', '11001', '10001', '01110'],
    '1': ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
    '2': ['01110', '10001', '00001', '00010', '00100', '01000', '11111'],
    '3': ['11110', '00001', '00001', '01110', '00001', '00001', '11110'],
    '4': ['00010', '00110', '01010', '10010', '11111', '00010', '00010'],
    '5': ['11111', '10000', '11110', '00001', '00001', '10001', '01110'],
    '6': ['00110', '01000', '10000', '11110', '10001', '10001', '01110'],
    '7': ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
    '8': ['01110', '10001', '10001', '01110', '10001', '10001', '01110'],
    '9': ['01110', '10001', '10001', '01111', '00001', '00010', '01100'],
}

def dot_number(n, x, y, cell=7.0, r=2.6):
    out = []
    for i, ch in enumerate(str(n)):
        for row in range(7):
            for col in range(5):
                lit = DIGITS[ch][row][col] == '1'
                out.append(f'<circle cx="{x + (i * 6 + col) * cell + cell / 2:.1f}" cy="{y + row * cell + cell / 2:.1f}" '
                           f'r="{r if lit else r * .55:.2f}" fill="{FG if lit else OFF}"/>')
    return ''.join(out)

def render(weeks):
    W, H = 1000, 396
    total, active, best, streak = stats(weeks)
    # levels by quartiles of non-zero days (like GitHub), so one busy day doesn't dim the rest
    nz = sorted(c for w in weeks for _, c in w if c)
    qs = [nz[min(len(nz) - 1, int(len(nz) * f))] for f in (.25, .5, .75)] if nz else [1, 1, 1]
    level = lambda c: 0 if c == 0 else 1 + sum(c > q for q in qs)
    weeks = weeks[-53:]
    b = [f'<rect width="{W}" height="{H}" rx="16" fill="{BG}"/>',
         f'<rect width="{W}" height="{H}" rx="16" fill="url(#dots)"/>',
         f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15.5" fill="none" stroke="{LINE}"/>',
         f'<text x="32" y="44" class="mono lbl">( 01 ) // АКТИВНОСТЬ</text>',
         f'<text x="260" y="44" class="mono lbl" style="fill:#555555">ОБНОВЛЕНО {dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).strftime("%d.%m.%Y")}</text>',
         f'<circle cx="{968 - len(f"{total} ЗА ГОД") * 8.8 - 12:.1f}" cy="40" r="3.2" fill="{FG}" class="pulse"/>',
         f'<text x="968" y="44" text-anchor="end" class="mono lbl">{total} ЗА ГОД</text>',
         f'<path d="M32 64.5H968" stroke="{LINE}"/>']

    # heatmap: one column per week, dot size + brightness by level
    cell = (968 - 32) / 53
    x0, y0 = 32 + (53 - len(weeks)) * cell, 108
    LEVELS = [(1.5, '#262626'), (2.6, '#555555'), (3.5, '#8a8a8a'), (4.4, '#c4c4c4'), (5.4, FG)]
    last_month = None
    for wi, week in enumerate(weeks):
        cx = x0 + wi * cell + cell / 2
        first = dt.date.fromisoformat(week[0][0])
        if first.month != last_month and first.day <= 7 and wi < len(weeks) - 2:
            b.append(f'<text x="{cx - cell / 2:.1f}" y="96" class="mono" font-size="11" fill="{MID}">{MONTHS[first.month - 1]}</text>')
        last_month = first.month if first.day <= 7 else last_month
        dots = []
        for date, c in week:
            wd = (dt.date.fromisoformat(date).weekday() + 1) % 7
            lvl = level(c)
            r, col = LEVELS[lvl]
            dots.append(f'<circle cx="{cx:.1f}" cy="{y0 + wd * cell + cell / 2:.1f}" r="{r}" fill="{col}"/>')
        b.append(f'<g class="on" style="animation-delay:{.2 + wi * .012:.3f}s">{"".join(dots)}</g>')

    # stats row
    y1 = 276
    b.append(f'<path d="M32 {y1 - 18.5}H968" stroke="{LINE}"/>')
    items = [(total, 'КОНТРИБУЦИЙ'), (active, 'АКТИВНЫХ ДНЕЙ'), (best, 'ЛУЧШИЙ ДЕНЬ'), (streak, 'СЕРИЯ, ДНЕЙ')]
    colw = (968 - 32) / 4
    for i, (n, label) in enumerate(items):
        x = 32 + i * colw
        if i: b.append(f'<path d="M{x - 16 + .5:.1f} {y1 - 4}V{H - 28}" stroke="{LINE}"/>')
        b.append(f'<g class="on" style="animation-delay:{1.0 + i * .12:.2f}s">{dot_number(n, x, y1)}</g>')
        b.append(f'<text x="{x}" y="{y1 + 49 + 30}" class="mono lbl">{label}</text>')


    css = f"""
  .mono {{ font-family: {MONO}; }}
  .lbl {{ font-size: 11px; letter-spacing: 2.2px; fill: {MID}; }}
  .pulse {{ animation: pulse 1.6s linear infinite; }}
  .on {{ animation: on .01s steps(1) both; }}
  @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: .25; }} }}
  @keyframes on {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
"""
    label = f'активность на гитхабе: {total} контрибуций за год, {active} активных дней, лучший день {best}, серия {streak}'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{label}">\n'
            f'<title>{label}</title>\n<style>{css}</style>\n'
            f'<defs><pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="10" cy="10" r=".8" fill="#1a1a1a"/></pattern></defs>\n'
            + '\n'.join(b) + '\n</svg>\n')

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', action='store_true', help='random data for a local preview')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    if a.sample:
        weeks = sample()
    else:
        weeks = None
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            try: weeks = from_graphql(token)
            except Exception as e: print('graphql failed, falling back to html:', e, file=sys.stderr)
        if weeks is None: weeks = from_html()
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write(render(weeks))
    print('written', a.out, stats(weeks))

if __name__ == '__main__':
    main()
