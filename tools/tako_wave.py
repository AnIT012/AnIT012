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
LEFT = PAD + 31            # 左に曜日（本物と同じく、マスの31px左）
FOOT = 123                 # マスの上端から、下の「Learn how…」「Less □ More」の下まで
GW = COLS * P - 3
W = LEFT + GW + PAD + 30
H = TOPM + PAD + FOOT
def X(c): return LEFT + c * P
def Y(r): return TOPM + PAD + r * P

# GitHub の草の色（ライト／ダーク）と、たこの色
THEMES = {
    # 草の色・文字の色は、GitHub のプロフィールの本物から測った値（2026-10-07）
    'light': dict(bg='#ffffff', cells=['#eff2f5', '#aceebb', '#4ac26b', '#2da44e', '#116329'], fg='#1f2328', muted='#59636e', tako='#e2606e', cheek='#ffb0bb', eye='#1f2328', sprout='#2da44e', feet='#b4404d', ink='#2b2320'),
    'dark': dict(bg='#0d1117', cells=['#151b23', '#033a16', '#196c2e', '#2ea043', '#56d364'], fg='#f0f6fc', muted='#9198a1', tako='#e2606e', cheek='#ffb0bb', eye='#1f2328', sprout='#56d364', feet='#b4404d', ink='#c9d1d9'),
}

# ── 自作のたこ。体・目（表情ごと）・足（2コマ）を分けて、表情を切り替えられるように ──
BODY = ["...1111...", ".11111111.", "1111111111", "1111111111", "1111111111", "1111111111", ".11111111."]
LEGS_A = ["1.1.11.1.1", "1..1..1..1"]
LEGS_B = [".1.1..1.1.", ".1..11..1."]
CHEEKS = [(1, 5), (8, 5)]   # ほっぺ
# ── キャラ：ブロックの子（草のマスと同じ四角・頭に芽・べに・ほっぺ）。1=体 e=目 c=ほっぺ g=芽 d=足 ──
CHARA = [".....gg.....", "....g.......", "..11111111..", "..11111111..", "..1e1111e1..", "..1e1111e1..", "..c111111c..", "..11111111..", "...d....d..."]
CHARA_BLINK = [(3, 4), (8, 4)]          # まばたきで隠す目の上の段
CPX = 3.0                               # ドット1つの大きさ


def chara(t, px=CPX, feet=False, blink=False):
    """feet=True なら原点が足の下のまん中、False なら絵のまん中"""
    w, h = 12 * px, 9 * px
    ox, oy = -w / 2, (-h if feet else -h / 2)
    col = {'1': t['tako'], 'e': t['eye'], 'c': t['cheek'], 'g': t['sprout'], 'd': t['feet']}
    r = [f'<rect x="{x*px + ox:.2f}" y="{y*px + oy:.2f}" width="{px+.05:.2f}" height="{px+.05:.2f}" fill="{col[ch]}"/>'
         for y, row in enumerate(CHARA) for x, ch in enumerate(row) if ch != '.']
    if blink:
        r.append('<g class="bk">' + ''.join(f'<rect x="{x*px + ox:.2f}" y="{y*px + oy:.2f}" width="{px+.05:.2f}" height="{px+.05:.2f}" fill="{t["tako"]}"/>' for x, y in CHARA_BLINK) + '</g>')
    return ''.join(r)
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
    s.append(f'<g fill="{t["cheek"]}">{rects(CHEEKS, px)}</g>')
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
DUR_W = 20                # 草の動き1周の秒数
R0 = 4                    # 波紋の始まり
RV = .2                   # 波紋が1マス進む時間（%）
CENTER = ((COLS - 1) / 2, 3)
S0 = 15                   # 草が沈み始める
T0, T1 = 30, 76           # 波の頂上が左の外→右の外へ
X0, X1 = -4.0, COLS + 2.0
D0 = 200                  # （たまった水は、最後に下の「水だけ捌ける」で引く）
BASE = 2                  # たまる水の深さ（下から2段）

# 列ごとの床の高さ（その週に草があった日数）と、草それぞれの行き先
floor = {}
dest = {}
for c in range(COLS):
    g = sorted([d for d in GRASS if d[0] == c], key=lambda d: d[1])
    floor[c] = len(g)
    for k, d in enumerate(g):
        dest[d[4]] = 7 - len(g) + k


TOFF, TSC, PARTS = 0.0, 1.0, False   # 上の大きな絵に入れる時：時刻 p → TOFF + p×TSC、絵の枠を付けずに中身だけ返す


def kf(name, stops):
    st = {}
    stops = sorted(stops, key=lambda q: q[0])
    if TOFF > 0: st[0.0] = stops[0][1]
    for p, v in stops:
        p = TOFF + p * TSC
        st[round(max(0, min(100, p)), 3)] = v
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


XE = X(0) + crest(T1 - 6) * P + 4                  # たこが宙返りして落ちる所
C0 = max(0, min(COLS - 1, round((XE + 18 - LEFT - CELL / 2) / P)))
SPLASH = T1 + 1.5
RC0 = max(1, min(6, 7 - max(level(C0, 0, SPLASH), floor[C0])))
FL0 = SPLASH + 2.6                                  # 冠が上がりきってから、水があふれ始める


def flood_at(c, r):
    """ざぶーんの所から波紋状に、そのマスが水で埋まる時刻"""
    return FL0 + math.hypot(c - C0, (r - RC0) * 1.2) * .12


def drain_at(r):
    """水が上の段から捌けていく時刻"""
    return 90 + r * .9


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
            onfloor = r >= 7 - floor[c] and p >= S0 + 6
            if r in lip(c, p): col = wt['foam']
            elif h > 0 and r >= 7 - h and not onfloor: col = water_color(wt, r, h)
            else: col = empty
            sc = 1.0
            for lag, amp, wc in ((0, .6, wt['w'][2]), (1.6, .4, wt['w'][1]), (3.4, .22, wt['w'][0])):   # 3重の輪
                u = (p - ra - lag) / .8
                if 0 <= u <= 1:
                    sc = max(sc, 1 + amp * math.sin(math.pi * u))
                    if col == empty: col = wc
            tfc = flood_at(c, r)
            if p >= tfc:                                   # ざぶーんのあと、波紋状に水が埋まる → 上から捌ける
                if p >= drain_at(r): col = empty
                elif p < tfc + .6 or (r > 0 and p >= drain_at(r - 1)): col = wt['foam']
                else: col = wt['w'][(0, 0, 1, 1, 2, 2, 3)[r]]
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
        a = flood_at(c, dest[idx]) + .4                    # 水が来たら、ふわっと浮いて自分の日へ
        st.append((a, tr(0, dy, ' scale(1)')))
        for k in range(1, 9):
            u = k / 8
            e = 1 - (1 - u) ** 2
            st.append((a + 3.5 * u, tr(0, dy * (1 - e) - 3 * math.sin(math.pi * u), ' scale(1)')))
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
    board = f'<rect x="-16" y="{9 * CPX / 2 - 4:.1f}" width="32" height="3.6" rx="1.8" fill="{t["ink"]}"/>'
    body.append(f'<g class="sf"><g transform="translate(0,-4)">{chara(t, blink=True)}</g>{board}</g>')
    # ── 最後のざぶーん：草と同じマスで、水が噴き出す（冠 → しずくが上がって落ちる）。そのあと水があふれる ──
    c0, a = C0, SPLASH
    def sfc_at(c, p):                                # その列・その時の水面の行（積もった草より下にはならない）
        c = max(0, min(COLS - 1, c))
        return max(1, min(6, 7 - max(level(c, 0, p), floor[c])))
    F, Z, O = 'f', 0, 1
    def col(n, top, kind_top=F, kind=O): return [(n, u, kind_top if u == top else kind) for u in range(1, top + 1)]
    frames = [
        [(0, 1, F), (-1, 1, Z), (1, 1, Z)],
        col(-2, 2) + col(-1, 3, F, Z) + [(0, 1, Z)] + col(1, 3, F, Z) + col(2, 2),
        col(-3, 1) + col(-2, 3) + col(-1, 4, F, Z) + col(0, 2, F, Z) + col(1, 4, F, Z) + col(2, 3) + col(3, 1)
        + [(0, 6, F), (-2, 6, Z), (2, 7, Z), (-3, 5, F), (3, 5, F)],
        col(-4, 1, F) + col(-3, 1) + col(-2, 2) + col(-1, 3, F, Z) + col(1, 3, F, Z) + col(2, 2) + col(3, 1) + col(4, 1, F)
        + [(0, 7, F), (-2, 7, Z), (2, 8, Z), (-4, 5, F), (4, 6, F)],
        col(-5, 1, F) + col(-4, 1) + col(-3, 1) + col(-2, 1) + col(-1, 2, F, Z) + col(1, 2, F, Z) + col(2, 1) + col(3, 1) + col(4, 1) + col(5, 1, F)
        + [(0, 5, F), (-2, 5, Z), (2, 6, Z), (-5, 3, F), (5, 4, F)],
    ]
    STEP = 1.3
    color_of = {F: wt['foam'], Z: wt['w'][0], O: wt['w'][1]}
    k = 0
    for fi, fr in enumerate(frames):
        f0, f1 = a + fi * STEP, a + (fi + 1) * STEP
        for dc, up, kind in fr:
            c = c0 + dc
            r = sfc_at(c, f0) - up               # 各列の水面の上に積む
            x, y = X(c), Y(r)
            if r < -3 or not 0 <= c < COLS: continue      # 草の外の列には出さない（水がないので浮いて見える）
            css.append(kf(f'z{k}', [(0, 'opacity:0'), (f0 - .01, 'opacity:0'), (f0, 'opacity:1'), (f1 - .01, 'opacity:1'), (f1, 'opacity:0'), (100, 'opacity:0')]))
            body.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{color_of[kind]}" style="opacity:0;animation:z{k} {DUR}s linear infinite"/>')
            k += 1
    if PARTS: return css, labels(t) + ''.join(body)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<style>{LEG_CSS}{"".join(css)}@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>'
            f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>{labels(t)}{"".join(body)}</svg>')


def labels(t):
    """本物の草と同じ文字：上に月、左に Mon/Wed/Fri、下に「Learn how we count contributions」と「Less □□□□□ More」"""
    font = 'font-family="-apple-system,BlinkMacSystemFont,&quot;Segoe UI&quot;,&quot;Noto Sans&quot;,Helvetica,Arial,sans-serif" font-size="12"'
    s = [f'<g {font}>']
    firsts = [datetime.date.fromisoformat(w['contributionDays'][0]['date']) for w in cal['weeks']]
    starts = [c for c in range(COLS) if c == 0 or firsts[c].month != firsts[c - 1].month]
    for i, c in enumerate(starts):
        nxt = starts[i + 1] if i + 1 < len(starts) else COLS
        if nxt - c < 2: continue          # 1列しかない月は出さない（本物と同じ）
        s.append(f'<text x="{X(c)}" y="{Y(0) - 6}" fill="{t["fg"]}">{firsts[c].strftime("%b")}</text>')
    for r, name in ((1, 'Mon'), (3, 'Wed'), (5, 'Fri')):
        s.append(f'<text x="{LEFT - 31}" y="{Y(r) + 9}" fill="{t["fg"]}">{name}</text>')
    y0 = Y(0)
    s.append(f'<text x="{LEFT - 2}" y="{y0 + 108}" fill="{t["muted"]}">Learn how we count contributions</text>')
    s.append(f'<text x="{LEFT + 528}" y="{y0 + 108}" fill="{t["muted"]}">Less</text>')
    for k in range(5):
        s.append(f'<rect x="{LEFT + 560 + 14 * k}" y="{y0 + 99}" width="10" height="10" rx="2" fill="{t["cells"][k]}"/>')
    s.append(f'<text x="{LEFT + 631}" y="{y0 + 108}" fill="{t["muted"]}">More</text>')
    s.append('</g>')
    return ''.join(s)



# ════════════════════════════════════════════════════════════
# README のいちばん上の大きな絵：タイトル「AnIT」→ 自己紹介 → 草。たこは重力ありで、上から順に全部を渡っていく
# ════════════════════════════════════════════════════════════
HD = 44.5                    # 1周の秒数
W0 = 24.5                    # 草の動き（20 秒ぶん）が始まる秒
HS, HB = 10, 8               # タイトルの文字のマスの間隔・大きさ
HTOP = 76                    # タイトルの文字の上のあき（跳んだ時に頭が切れないように）
LETTERS = [
    ('A', 0, [".111.", "1...1", "1...1", "11111", "1...1", "1...1", "1...1"]),
    ('n', 6, [".....", ".....", "1111.", "1...1", "1...1", "1...1", "1...1"]),
    ('I', 12, ["111", ".1.", ".1.", ".1.", ".1.", ".1.", "111"]),
    ('T', 16, ["11111", "..1..", "..1..", "..1..", "..1..", "..1..", "..1.."]),
]
# 文と文のあいだを1行ぶん空けて、キャラはそこ（文のすぐ上の通り道）を歩く。下の通り道へは、文のない左右の端で落ちる
INTRO = [  # (文, ベースライン y, 1文字のおおよその幅)
    ('PdM・SA・TS・DX人材志望の大学3年生です。自分や周りの困りごとを見つけて、', 200, 14),
    ('要件と設計を自分で考え、実装はAIに手伝ってもらってプロダクトを作っています。', 250, 14),
    ('Aspiring PdM, solutions architect, technical support engineer, or DX specialist.', 300, 7.2),
    ('I find problems around me, design the requirements myself, and build products with AI.', 350, 7.2),
]
WY = 362                     # 草の絵を置く高さ
HW, HH = W, WY + H


def hx(c): return LEFT + c * HS
def hy(r): return HTOP + r * HS
def hp(sec): return sec / HD * 100


def hero_tako(t):
    return chara(t, feet=True, blink=True)


def hero_path():
    """(秒, x, y, 形の変化)。跳ぶ・落ちるは放物線（重力）"""
    path = []
    def at(sec, xy, ex=''): path.append((sec, xy[0], xy[1], ex))
    def walk(t0, t1, a, b):
        n = max(2, int((t1 - t0) * 6))
        for k in range(n + 1):
            u = k / n
            at(t0 + (t1 - t0) * u, (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u - 3.5 * abs(math.sin(u * math.pi * n / 2))))
    def jump(t0, t1, a, b, hgt):
        at(t0 - .12, a, ' scale(1.12,.85)')
        for k in range(1, 13):
            u = k / 12
            at(t0 + (t1 - t0) * u, (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u - hgt * 4 * u * (1 - u)), ' scale(.92,1.1)' if u < .5 else '')
        at(t1 + .1, b, ' scale(1.18,.8)')
        at(t1 + .25, b)
    def drop(t0, t1, a, b):
        """前に一歩出て、重力で落ちる"""
        for k in range(0, 11):
            u = k / 10
            at(t0 + (t1 - t0) * u, (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u * u))
        at(t1 + .1, b, ' scale(1.15,.82)')
        at(t1 + .25, b)
    fl = hy(6) + HB
    A_top, I_top, T_top = (hx(2) + 4, hy(0)), (hx(13) + 4, hy(0)), (hx(18) + 4, hy(0))
    n_l, n_r = (hx(6) + 8, hy(2)), (hx(9) + 2, hy(2))
    gap = (hx(11) + 4, fl)
    lane = lambda k: INTRO[k][1] - 14                  # 文 k のすぐ上の通り道（足の高さ）
    L, R = 22, HW - 40                                  # 文のない左右の端
    walk(0, 1.3, (-20, fl), (hx(-1) - 4, fl))
    jump(1.4, 2.2, (hx(-1) - 4, fl), A_top, 34)
    walk(2.4, 2.8, A_top, (A_top[0] + 6, A_top[1]))
    jump(2.95, 3.6, (A_top[0] + 6, A_top[1]), n_l, 22)
    walk(3.8, 4.5, n_l, n_r)
    jump(4.65, 5.3, n_r, gap, 14)                       # n と I のあいだに割り込む
    for k, sx in enumerate([1.25, .85, 1.15, .92, 1.08, 1.0]):
        at(5.6 + k * .22, gap, f' scale({sx},{2 - sx:.2f})')
    jump(7.0, 7.8, gap, I_top, 50)
    jump(8.1, 8.8, I_top, T_top, 20)
    for k in range(6):                                   # T の上でぴょこぴょこ
        at(9.1 + k * .22, (T_top[0], T_top[1] - (3 if k % 2 else 0)))
    jump(10.6, 11.4, T_top, (280, lane(0)), 14)
    walk(11.6, 13.4, (280, lane(0)), (R, lane(0)))
    drop(13.5, 13.9, (R, lane(0)), (R, lane(1)))
    walk(14.1, 16.9, (R, lane(1)), (L, lane(1)))
    drop(17.0, 17.4, (L, lane(1)), (L, lane(2)))
    walk(17.6, 20.4, (L, lane(2)), (R, lane(2)))
    drop(20.5, 20.9, (R, lane(2)), (R, lane(3)))
    walk(21.1, 23.8, (R, lane(3)), (L + 18, lane(3)))
    # 草の左の「Mon」の上で待つ（波紋が来たら、びくっと跳ねる）
    mon = (LEFT - 18, WY + Y(1) - 2)
    drop(23.9, 24.4, (L + 18, lane(3)), mon)
    rip = W0 + (R0 + abs(0 - CENTER[0]) * RV) * DUR_W / 100
    at(rip - .05, mon); at(rip + .25, (mon[0], mon[1] - 10), ' scale(.9,1.12)'); at(rip + .5, mon, ' scale(1.15,.85)'); at(rip + .7, mon)
    for k in range(10):
        at(rip + 1 + k * .45, (mon[0], mon[1] - (1.5 if k % 2 else 0)))
    # 波が来たら飛び乗る（ここから草の中の波乗りのたこに入れ替わる）
    pw = T0 + 1.5
    wx = X(0) + crest(pw) * P + 4
    wy = WY + Y(7 - crest_h(crest(pw))) - 17 - 4 + 9 * CPX / 2
    handoff = W0 + pw * DUR_W / 100
    jump(handoff - .55, handoff - .02, mon, (wx, wy), 10)
    path.append((handoff, wx, wy, ';opacity:0'))
    path.append((HD - .05, -20, fl, ';opacity:0'))
    path.append((HD, -20, fl, ''))
    path.sort(key=lambda q: q[0])
    # 入れ替わったあとは見えない
    out = []
    for sec, x, y, ex in path:
        op = 0 if handoff <= sec < HD - .01 else 1
        ex = ex.replace(';opacity:0', '')
        out.append((hp(sec), f'transform:translate({x:.1f}px,{y:.1f}px){ex};opacity:{op}'))
    return out


def hero(t, wt):
    global TOFF, TSC, PARTS, DUR
    TOFF, TSC, PARTS, DUR = W0 / HD * 100, DUR_W / HD, True, HD
    wcss, wbody = build(t, wt)
    TOFF, TSC, PARTS, DUR = 0.0, 1.0, False, DUR_W
    css = list(wcss)
    css.append('.bk{opacity:0;animation:bk 3.1s steps(1) infinite}@keyframes bk{0%,90%{opacity:0}91%,96%{opacity:1}97%,100%{opacity:0}}')
    body = []
    # タイトルの文字：割り込まれた時に左右へ開いて、ばねで戻る
    for name, c0, rows in LETTERS:
        side = -1 if name in 'An' else 1
        amt = 12 * (1 if name in 'nI' else .55)
        st = [(0, 0), (5.25, 0), (5.45, side * amt), (6.7, side * amt), (7.05, side * amt * 1.1), (7.3, -side * amt * .25), (7.5, side * amt * .1), (7.7, 0), (HD, 0)]
        css.append(f'@keyframes L{name}{{' + ''.join(f'{hp(sec):.3f}%{{transform:translateX({v:.1f}px)}}' for sec, v in st) + '}')
        rects_ = ''.join(f'<rect x="{hx(c0 + cc)}" y="{hy(r)}" width="{HB}" height="{HB}" rx="1.6" fill="{t["fg"]}"/>'
                         for r, row in enumerate(rows) for cc, ch in enumerate(row) if ch == '1')
        body.append(f'<g style="animation:L{name} {HD}s linear infinite">{rects_}</g>')
    # 自己紹介
    font = 'font-family="-apple-system,BlinkMacSystemFont,&quot;Segoe UI&quot;,&quot;Hiragino Sans&quot;,&quot;Noto Sans JP&quot;,&quot;Noto Sans&quot;,Meiryo,sans-serif" font-size="14"'
    body.append(f'<g {font} fill="{t["fg"]}">' + ''.join(f'<text x="{LEFT}" y="{y}">{txt}</text>' for txt, y, _ in INTRO) + '</g>')
    body.append(f'<g transform="translate(0,{WY})">{wbody}</g>')
    css.append(f'@keyframes hk{{' + ''.join(f'{p:.3f}%{{{v}}}' for p, v in hero_path()) + '}' + f'.hk{{animation:hk {HD}s linear infinite}}')
    body.append(f'<g class="hk">{hero_tako(t)}</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {HW} {HH}" width="{HW}" height="{HH}">'
            f'<title>AnIT</title><style>{LEG_CSS}{"".join(css)}@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.hk{{opacity:0}}}}</style>'
            f'<rect width="{HW}" height="{HH}" fill="{t["bg"]}"/>{"".join(body)}</svg>')


for th, t in THEMES.items():
    open(os.path.join(out, f'tako-wave-{th}.svg'), 'w').write(build(t, WATER[th]))
    open(os.path.join(out, f'tako-hero-{th}.svg'), 'w').write(hero(t, WATER[th]))
print('ok', COLS, 'weeks', len(GRASS), 'days with grass')
