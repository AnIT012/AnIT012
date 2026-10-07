"""GitHub の草（貢献グラフ）で、たこが波乗りする SVG を作る。文字なし。
1. 中央から3重の波紋。通ったあとの下2段に水がたまる
2. 草のマスが、それぞれの週の列の中で沈んで積もる（列の高さ＝その週に草があった日数）
3. 左から波。積もった草が高い列ほど波も高く、たこも高く乗る。右端で宙返り
4. 水が引いて、草はそれぞれの日に戻る
README の <img> で読まれても動くように、JS は使わず SVG の中の CSS アニメだけで動かす。

使い方:
  GITHUB_TOKEN=... python3 tools/tako_wave.py <ユーザー名> <出力フォルダ>
  python3 tools/tako_wave.py --json contrib.json <出力フォルダ>   # 手元で試す時
"""
import json, math, os, sys, datetime, urllib.request

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""


def load(argv):
    if argv[1] == '--json':
        data = json.load(open(argv[2]))
        return data['data']['user']['contributionsCollection']['contributionCalendar'], argv[3]
    req = urllib.request.Request('https://api.github.com/graphql', data=json.dumps({'query': QUERY, 'variables': {'login': argv[1]}}).encode(),
                                 headers={'Authorization': 'bearer ' + os.environ['GITHUB_TOKEN'], 'Content-Type': 'application/json'})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if 'errors' in data: sys.exit('GitHub API: ' + json.dumps(data['errors'], ensure_ascii=False))
    return data['data']['user']['contributionsCollection']['contributionCalendar'], argv[2]


cal, out = load(sys.argv)
os.makedirs(out, exist_ok=True)
LV = {'NONE': 0, 'FIRST_QUARTILE': 1, 'SECOND_QUARTILE': 2, 'THIRD_QUARTILE': 3, 'FOURTH_QUARTILE': 4}
days = []
for c, w in enumerate(cal['weeks']):
    for d in w['contributionDays']:
        r = (datetime.date.fromisoformat(d['date']).weekday() + 1) % 7
        days.append((c, r, LV[d['contributionLevel']], d['contributionCount'], len(days)))
COLS = len(cal['weeks'])
GRASS = [d for d in days if d[2]]
P, CELL, PAD, TOPM = 13, 10, 12, 34
GW = COLS * P - 3
W = PAD * 2 + GW + 30
H = TOPM + PAD * 2 + 7 * P - 3
def X(c): return PAD + c * P
def Y(r): return TOPM + PAD + r * P

# GitHub の草の色（ライト／ダーク）と、たこの色
THEMES = {
    'light': dict(bg='#ffffff', cells=['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'], tako='#d97757', eye='#1f2328', ink='#2b2320'),
    'dark': dict(bg='#0d1117', cells=['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353'], tako='#e08a6c', eye='#0d1117', ink='#c9d1d9'),
}

# ── 自作のたこ。体・目（表情ごと）・足（2コマ）を分けて、表情を切り替えられるように ──
BODY = ["...1111...", ".11111111.", "1111111111", "1111111111", "1111111111", "1111111111", ".11111111."]
LEGS_A = ["1.1.11.1.1", "1..1..1..1"]
LEGS_B = [".1.1..1.1.", ".1..11..1."]
EYES = {
    'open': [(2, 3), (2, 4), (7, 3), (7, 4)],
    'shut': [(2, 4), (3, 4), (6, 4), (7, 4)],
    'happy': [(1, 4), (2, 3), (3, 4), (6, 4), (7, 3), (8, 4)],
    'wow': [(2, 2), (3, 2), (2, 3), (3, 3), (2, 4), (3, 4), (6, 2), (7, 2), (6, 3), (7, 3), (6, 4), (7, 4)],
}


def rects(cells, px, y0=0, fill=None):
    f = f' fill="{fill}"' if fill else ''
    return ''.join(f'<rect x="{x*px:.2f}" y="{(y0+y)*px:.2f}" width="{px+.05:.2f}" height="{px+.05:.2f}"{f}/>' for (x, y) in cells)


def grid_of(rows):
    return [(x, y) for y, row in enumerate(rows) for x, ch in enumerate(row) if ch != '.']


def tako(t, px, eyes=('open',), eye_cls=None, body_cls='', legs=True):
    """eyes に出す表情、eye_cls に表情ごとの class（表示の切り替え用）"""
    w, h = 10 * px, 9 * px
    s = [f'<g transform="translate({-w/2:.2f},{-h/2:.2f})">']
    s.append(f'<g class="{body_cls}" fill="{t["tako"]}">{rects(grid_of(BODY), px)}')
    if legs:
        s.append(f'<g class="la">{rects(grid_of(LEGS_A), px, 7)}</g><g class="lb">{rects(grid_of(LEGS_B), px, 7)}</g>')
    s.append('</g>')
    for e in eyes:
        cls = (eye_cls or {}).get(e, '')
        s.append(f'<g class="{cls}" fill="{t["eye"]}">{rects(EYES[e], px)}</g>')
    s.append('</g>')
    return ''.join(s)


LEG_CSS = '.la{animation:la .45s steps(1) infinite}.lb{animation:lb .45s steps(1) infinite}@keyframes la{50%{opacity:0}}@keyframes lb{0%{opacity:0}50%{opacity:1}}'


WATER = {
    'light': dict(foam='#b3dbff', w=['#7cbdf4', '#3f95e3', '#2570c2', '#174e94']),
    'dark': dict(foam='#cae8ff', w=['#3d8fe0', '#2a6fc9', '#1d54a3', '#123a75']),
}
DUR = 20
R0 = 4                    # 波紋の始まり
RV = .2                   # 波紋が1マス進む時間（%）
CENTER = ((COLS - 1) / 2, 3)
S0 = 15                   # 草が沈み始める
T0, T1 = 30, 76           # 波の頂上が左の外→右の外へ
X0, X1 = -4.0, COLS + 2.0
D0 = 86                   # 水が引き始める
U0 = 88                   # 草が浮かんで戻り始める
BASE = 2                  # たまる水の深さ（下から2段）

# 列ごとの床の高さ（その週に草があった日数）と、草それぞれの行き先
floor = {}
dest = {}
for c in range(COLS):
    g = sorted([d for d in GRASS if d[0] == c], key=lambda d: d[1])
    floor[c] = len(g)
    for k, d in enumerate(g):
        dest[d[4]] = 7 - len(g) + k


def kf(name, stops):
    st = {}
    for p, v in stops: st[round(max(0, min(100, p)), 3)] = v
    return f'@keyframes {name}{{' + ''.join(f'{p:g}%{{{v}}}' for p, v in sorted(st.items())) + '}'


def tr(x, y, extra=''): return f'transform:translate({x:.1f}px,{y:.1f}px){extra}'


def ripple_at(c, r): return R0 + math.hypot(c - CENTER[0], (r - CENTER[1]) * 1.0) * RV


def crest(p): return X0 + (X1 - X0) * (p - T0) / (T1 - T0)


def floor_s(x):
    """沈んだ草の高さを、となりの列となめらかにつないだもの"""
    def f(c): return floor.get(min(COLS - 1, max(0, c)), 0)
    c0 = math.floor(x); u = x - c0
    a = (f(c0 - 1) + 2 * f(c0) + f(c0 + 1)) / 4
    b = (f(c0) + 2 * f(c0 + 1) + f(c0 + 2)) / 4
    return a + (b - a) * u


def crest_h(x):
    """波の頂上の高さ（マス）。沈んだ草が高い列ほど、波も高い"""
    return min(7.0, 3.6 + 1.1 * floor_s(x))


def level(c, r, p):
    """その時刻の水面の高さ（下からのマス数）"""
    h = 0.0
    if ripple_at(c, 6) + 2.6 <= p < D0 + (6 - BASE) * 0:  # 波紋が通ったら、たまる
        h = BASE
    if D0 <= p < D0 + 2: h = 1
    if p >= D0 + 2: h = 0
    if T0 <= p <= T1 + 10:
        x = crest(p); d = x - c
        hc = crest_h(x)
        w = 0.0
        if -1.6 <= d <= 0: w = hc * (1 + d / 1.6) ** .7
        elif 0 < d <= 2.5: w = hc - .4 * max(0, d - 1)
        elif d > 2.5:
            hp = crest_h(c + 2.5) - .6      # この列を通った時の高さから下がっていく
            w = BASE + (hp - BASE) * math.exp(-(d - 2.5) / 6) + .9 * math.exp(-d / 12) * (1 + math.sin(d * .9)) / 2
        h = max(h, w)
    return int(h + .35)


def lip(c, p):
    if not (T0 <= p <= T1): return set()
    x = crest(p); d = x - c
    top = 7 - int(crest_h(x) + .35)
    if crest_h(x) < 3.5: return set()
    if -2.6 <= d < -1.6: return {top}
    if -3.3 <= d < -2.6: return {top + 1}
    return set()


def water_color(wt, r, h):
    k = r - (7 - h)
    if h >= 3:
        return wt['foam'] if k == 0 else wt['w'][min(3, k)]
    return wt['w'][min(3, k)]


def build(t, wt):
    body, css = [], []
    css.append('rect.c{transform-box:fill-box;transform-origin:center}')
    empty = t['cells'][0]
    # ── 下地のマス（水になる） ──
    steps = [i * .25 for i in range(401)]
    for c, r, l, n, idx in days:
        ra = ripple_at(c, r)
        st = [(0, f'fill:{empty};transform:scale(1)')]
        prev = (empty, 1.0)
        for p in steps:
            h = level(c, r, p)
            onfloor = r >= 7 - floor[c] and p >= S0 + 6 and p < U0 + 6
            if r in lip(c, p): col = wt['foam']
            elif h > 0 and r >= 7 - h and not onfloor: col = water_color(wt, r, h)
            else: col = empty
            sc = 1.0
            for lag, amp, wc in ((0, .6, wt['w'][2]), (1.6, .4, wt['w'][1]), (3.4, .22, wt['w'][0])):   # 3重の輪
                u = (p - ra - lag) / .8
                if 0 <= u <= 1:
                    sc = max(sc, 1 + amp * math.sin(math.pi * u))
                    if col == empty: col = wc
            sc = round(sc, 2)
            if (col, sc) != prev:
                if col != prev[0]: st.append((p - .01, f'fill:{prev[0]};transform:scale({prev[1]})'))
                st.append((p, f'fill:{col};transform:scale({sc})'))
                prev = (col, sc)
        st.append((100, f'fill:{empty};transform:scale(1)'))
        css.append(kf(f'b{idx}', st))
        body.append(f'<rect class="c" x="{X(c)}" y="{Y(r)}" width="{CELL}" height="{CELL}" rx="2" fill="{empty}" style="animation:b{idx} {DUR}s linear infinite"/>')
    # ── 草のマス：波紋で揺れて、沈んで床に、最後に浮かんで戻る ──
    for c, r, l, n, idx in GRASS:
        col = t['cells'][l]
        ra = ripple_at(c, r)
        dy = (dest[idx] - r) * P
        st = [(0, tr(0, 0, ' scale(1)'))]
        for lag, amp in ((0, .6), (1.6, .4), (3.4, .22)):
            for k in range(0, 6):
                u = k / 5
                st.append((ra + lag + .8 * u, tr(0, 0, f' scale({1 + amp * math.sin(math.pi * u):.2f})')))
        s = S0 + (c % 9) * .5 + (r * .25)
        fall = 2.5 + 1.2 * math.sqrt(abs(dy) / P)
        st.append((s, tr(0, 0, ' scale(1)')))
        for k in range(1, 9):
            u = k / 8
            st.append((s + fall * u, tr(0, dy * u * u, ' scale(1)')))
        st += [(s + fall + .5, tr(0, dy - 2.5, ' scale(1.05,.95)')), (s + fall + 1.1, tr(0, dy, ' scale(1)'))]
        # 波が上を通る時、床がほんの少し沈む
        pc = T0 + (T1 - T0) * (c - X0) / (X1 - X0)
        st += [(pc - .5, tr(0, dy, ' scale(1)')), (pc + .3, tr(0, dy + 1.5, ' scale(1)')), (pc + 1.5, tr(0, dy, ' scale(1)'))]
        a = U0 + (COLS - 1 - c) * .06 + (6 - r) * .15
        st.append((a, tr(0, dy, ' scale(1)')))
        for k in range(1, 9):
            u = k / 8
            e = 1 - (1 - u) ** 2
            st.append((a + 4 * u, tr(0, dy * (1 - e), ' scale(1)')))
        st.append((100, tr(0, 0, ' scale(1)')))
        st.sort(key=lambda x: x[0])
        css.append(kf(f'g{idx}', st))
        body.append(f'<rect class="c" x="{X(c)}" y="{Y(r)}" width="{CELL}" height="{CELL}" rx="2" fill="{col}" style="animation:g{idx} {DUR}s linear infinite"/>')
    # ── しぶき（頂上から四角が後ろへ） ──
    k = 0
    for i in range(16):
        p = T0 + 3 + (T1 - T0 - 6) * i / 15
        xc = X(0) + crest(p) * P
        for j in range(2):
            dx, dy = -10 - 8 * j - (i % 3) * 3, -16 - 6 * j - (i % 2) * 5
            sz = 3 if j else 4
            css.append(kf(f'sp{k}', [(0, 'opacity:0;' + tr(0, 0)), (p, 'opacity:0;' + tr(0, 0)), (p + .2, 'opacity:1;' + tr(0, 0)), (p + 4, 'opacity:0;' + tr(dx, dy)), (100, 'opacity:0;' + tr(dx, dy))]))
            body.append(f'<rect x="{xc:.1f}" y="{Y(7 - int(crest_h(crest(p)) + .35)) - 2}" width="{sz}" height="{sz}" rx=".6" fill="{wt["foam"] if j else wt["w"][0]}" style="animation:sp{k} {DUR}s ease-out infinite"/>')
            k += 1
    # ── たこ ──
    Yb = Y(1) - 17
    st = [(0, tr(X(0) - 30, Yb, ' rotate(0deg)') + ';opacity:0'), (T0 + 1.4, tr(X(0) - 30, Yb, ' rotate(0deg)') + ';opacity:0')]
    for i in range(0, 81):
        p = T0 + 1.5 + (T1 - 6 - T0 - 1.5) * i / 80
        yb = Y(7 - crest_h(crest(p))) - 17
        st.append((p, tr(X(0) + crest(p) * P + 4, yb + 1.5 * math.sin(i * .8), f' rotate({-8 + 6 * math.sin(i * .55):.0f}deg)') + ';opacity:1'))
    xe = X(0) + crest(T1 - 6) * P + 4
    Yb = Y(7 - crest_h(crest(T1 - 6))) - 17
    for i in range(1, 13):
        u = i / 12
        st.append((T1 - 6 + 9 * u, tr(xe + 18 * u, Yb - 30 * math.sin(math.pi * u) + 46 * u * u, f' rotate({360 * u:.0f}deg)') + ';opacity:1'))
    st += [(T1 + 3.1, tr(xe + 18, Yb + 46, ' rotate(360deg)') + ';opacity:0'), (100, tr(X(0) - 30, Yb, ' rotate(0deg)') + ';opacity:0')]
    css.append(kf('sf', st) + f'.sf{{animation:sf {DUR}s linear infinite}}')
    board = f'<rect x="-14" y="9.5" width="28" height="3.6" rx="1.8" fill="{t["ink"]}"/>'
    body.append(f'<g class="sf"><g transform="translate(0,-4)">{tako(t, 2.0, eyes=("happy",))}</g>{board}</g>')
    sx, sy = xe + 18, Y(3)
    for i in range(18):
        ang = math.pi * (1.05 + .9 * i / 17)
        dist = 16 + (i % 4) * 9
        dx, dy = math.cos(ang) * dist, math.sin(ang) * dist - 6
        a = T1 + 3
        css.append(kf(f'dr{i}', [(0, 'opacity:0;' + tr(0, 0)), (a, 'opacity:0;' + tr(0, 0)), (a + .3, 'opacity:1;' + tr(0, 0)), (a + 3, 'opacity:1;' + tr(dx, dy)), (a + 6, 'opacity:0;' + tr(dx * 1.2, dy + 14)), (100, 'opacity:0;' + tr(0, 0))]))
        sz = 4 if i % 2 else 3
        body.append(f'<rect x="{sx:.1f}" y="{sy}" width="{sz}" height="{sz}" rx=".6" fill="{wt["foam"] if i % 3 == 0 else wt["w"][i % 2]}" style="animation:dr{i} {DUR}s ease-out infinite"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<style>{LEG_CSS}{"".join(css)}@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>'
            f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>{"".join(body)}</svg>')


for th, t in THEMES.items():
    open(os.path.join(out, f'tako-wave-{th}.svg'), 'w').write(build(t, WATER[th]))
print('ok', COLS, 'weeks', len(GRASS), 'days with grass')
