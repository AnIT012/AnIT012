"""代表作3つ（就活Hub・TeaMy・mamebot）の動くカード。ブロックの子が、その作品の一場面をやって見せる。
場面はポートフォリオのタイルの見本と同じ（会社名・依頼文は見本の例のまま）。
  python3 tools/works_cards.py <出力フォルダ>
→ works-<id>-light.svg / works-<id>-dark.svg
"""
import os
import sys

W, H, D = 400, 236, 8.0          # カードの大きさと、1回の長さ（秒）
FONT = 'font-family="-apple-system,BlinkMacSystemFont,&quot;Segoe UI&quot;,&quot;Hiragino Sans&quot;,&quot;Noto Sans JP&quot;,&quot;Noto Sans&quot;,Meiryo,sans-serif"'

THEMES = {
    'light': dict(bg='#ffffff', fg='#1f2328', muted='#59636e', panel='#ffffff', line='#d1d9e0', tako='#e2606e', cheek='#ffb0bb', eye='#1f2328', sprout='#2da44e', feet='#b4404d'),
    'dark': dict(bg='#0d1117', fg='#f0f6fc', muted='#9198a1', panel='#161b22', line='#3d444d', tako='#e2606e', cheek='#ffb0bb', eye='#1f2328', sprout='#56d364', feet='#b4404d'),
}
# 作品の色と、ポートフォリオと同じブロックの形（1マス＝1）
WORKS = {
    'shukatsu': dict(name='就活Hub', metric='10名以上が利用', color='#6c5ce0', cells=[(0, 0), (0, 1), (1, 1), (2, 1)]),
    'teamy': dict(name='TeaMy', metric='コスト約1/3（1タスク20円前後）', color='#12857d', cells=[(0, 0), (1, 0), (2, 0), (1, 1)]),
    'mamebot': dict(name='mamebot', metric='家族4人が毎日利用', color='#9a5b2a', cells=[(0, 0), (1, 0), (0, 1), (1, 1)]),
}

# ── ブロックの子（プロフィールの上の絵と同じ）──
CHARA = [".....gg.....", "....g.......", "..11111111..", "..11111111..", "..11111111..", "..11111111..", "..c111111c..", "..11111111..", "...d....d..."]
FACES = {'f': [(3, 4), (3, 5), (8, 4), (8, 5)], 'r': [(4, 4), (4, 5), (9, 4), (9, 5)], 'l': [(2, 4), (2, 5), (7, 4), (7, 5)],
         'j': [(3, 3), (4, 4), (3, 5), (8, 3), (7, 4), (8, 5)]}
PX = 3.0


def mix(a, b, k):
    """a の色を k、b の色を 1-k で混ぜる"""
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x * k + y * (1 - k)):02x}' for x, y in zip(pa, pb))


def pct(sec): return sec / D * 100


def kf(name, stops, prop_fn, timing='linear'):
    """stops: [(秒, 値)]。0秒と最後を必ず置く"""
    st = sorted(stops)
    if st[0][0] > 0: st.insert(0, (0, st[0][1]))
    if st[-1][0] < D: st.append((D, st[-1][1]))
    body = ''.join(f'{pct(s):.2f}%{{{prop_fn(v)}}}' for s, v in st)
    return f'@keyframes {name}{{{body}}}.{name}{{animation:{name} {D}s {timing} infinite}}'


def steps_kf(name, stops, prop_fn):
    """値を次の区切りまで保つ（コマ送り）"""
    return kf(name, stops, prop_fn, 'step-end')


def chara(t, faces, prefix):
    w, h = 12 * PX, 9 * PX
    ox, oy = -w / 2, -h
    col = {'1': t['tako'], 'c': t['cheek'], 'g': t['sprout'], 'd': t['feet']}
    r = [f'<rect x="{x * PX + ox:.1f}" y="{y * PX + oy:.1f}" width="{PX + .05:.2f}" height="{PX + .05:.2f}" fill="{col[ch]}"/>'
         for y, row in enumerate(CHARA) for x, ch in enumerate(row) if ch != '.']
    for f in faces:
        r.append(f'<g class="{prefix}{f}" fill="{t["eye"]}">' + ''.join(
            f'<rect x="{x * PX + ox:.1f}" y="{y * PX + oy:.1f}" width="{PX + .05:.2f}" height="{PX + .05:.2f}"/>' for x, y in FACES[f]) + '</g>')
    return ''.join(r)


def face_css(prefix, windows):
    """windows: [(始め, 終わり, 表情)]。当たらない時は正面"""
    names = sorted({w[2] for w in windows} | {'f'})
    out = []
    for n in names:
        base = 1 if n == 'f' else 0
        st = {0.0: base}
        for a, b, f in windows:
            st[a] = 1 if f == n else 0
            st[b] = base
        out.append(steps_kf(f'{prefix}{n}', list(st.items()), lambda v: f'opacity:{v}'))
    return out, names


def hop_path(points):
    """points: [(秒, x, y)]。移る区間は2コマで跳ねる（上へ6px）"""
    st = []
    for i, (s, x, y) in enumerate(points):
        st.append((s, (x, y)))
        if i + 1 < len(points):
            s2, x2, y2 = points[i + 1]
            if (x2, y2) != (x, y):
                st.append((s2 - .3, (x, y)))
                st.append((s2 - .15, ((x + x2) / 2, min(y, y2) - 14)))
    return st


def frame(t, w, body, css, title):
    c = w['color']
    card = mix(c, t['bg'], .07 if t['bg'] == '#ffffff' else .16)
    name_col = mix(c, t['fg'], .85) if t['bg'] == '#ffffff' else mix(c, t['fg'], .5)
    icon = ''.join(f'<rect x="{W - 24 - 3 * 15 + x * 15}" y="{20 + y * 15}" width="14" height="14" fill="{c}"/>' for x, y in w['cells'])
    head = (f'<text x="24" y="50" font-size="24" font-weight="700" fill="{name_col}">{w["name"]}</text>'
            f'<text x="24" y="74" font-size="13" font-weight="700" fill="{t["muted"]}">{w["metric"]}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" {FONT}>'
            f'<title>{title}</title>'
            f'<style>{"".join(css)}@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>'
            f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>'
            f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" fill="{card}" stroke="{c}" stroke-width="3"/>'
            f'{icon}{head}{body}</svg>')


def kid(t, path, faces_win, prefix):
    css, names = face_css(prefix, faces_win)
    css.append(kf(f'{prefix}m', hop_path(path), lambda v: f'transform:translate({v[0]:.1f}px,{v[1]:.1f}px)'))
    return f'<g class="{prefix}m">{chara(t, names, prefix)}</g>', css


# ── 就活Hub：「次の一手」の〇を押す → 未→提出済→完了 → 進み具合のバーが1つ緑に → 花畑に花が咲く → 次の一手が入れ替わる ──
def shukatsu(t):
    w = WORKS['shukatsu']; c = w['color']
    due = mix(c, t['fg'], .8)
    green, amber, gray = '#2da44e', '#d4a72c', t['line']
    x0, y0, cw, ch = 24, 92, 250, 80
    body, css = [], []

    def card(cls, name, kind, what, date, segs):
        bar = ''.join(f'<rect class="{cls}s{k}" x="{x0 + 12 + k * 44}" y="{y0 + 28}" width="40" height="6" fill="{col}"/>' for k, col in enumerate(segs))
        return (f'<g class="{cls}">'
                f'<text x="{x0 + 12}" y="{y0 + 20}" font-size="13" font-weight="700" fill="{t["fg"]}">{name}</text>{bar}'
                f'<text x="{x0 + 12}" y="{y0 + 54}" font-size="9.5" fill="{t["muted"]}">次の一手</text>'
                f'<text x="{x0 + 62}" y="{y0 + 54}" font-size="12.5" font-weight="700" fill="{t["fg"]}">{what}</text>'
                f'<text x="{x0 + 12}" y="{y0 + 72}" font-size="10.5" font-weight="700" fill="{due if kind == "締切" else t["fg"]}">{kind} {date}</text></g>')

    body.append(f'<rect x="{x0}" y="{y0}" width="{cw}" height="{ch}" fill="{t["panel"]}" stroke="{t["line"]}"/>')
    body.append(card('ca', 'さくらネット', '締切', 'ES提出', '10/13', [green, gray, gray, gray]))
    body.append(card('cb', 'みどり電鉄', '実施', '面接', '10/16', [green, green, gray, gray]))
    css.append(steps_kf('ca', [(0, 1), (4.8, 0), (7.95, 1)], lambda v: f'opacity:{v}'))
    css.append(steps_kf('cb', [(0, 0), (4.8, 1), (7.95, 0)], lambda v: f'opacity:{v}'))
    # さくらネットの2つ目の段：提出済（黄）→ 通過（緑）
    body.append(f'<rect class="sA" x="{x0 + 12 + 44}" y="{y0 + 28}" width="40" height="6" fill="{amber}"/><rect class="sG" x="{x0 + 12 + 44}" y="{y0 + 28}" width="40" height="6" fill="{green}"/>')
    css.append(steps_kf('sA', [(0, 0), (2.4, 1), (3.2, 0), (4.8, 0)], lambda v: f'opacity:{v}'))
    css.append(steps_kf('sG', [(0, 0), (3.2, 1), (4.8, 0)], lambda v: f'opacity:{v}'))
    # 〇：未 → 提出済（半分）→ 完了（塗り＋チェック）
    ox, oy = x0 + cw - 26, y0 + 58
    body.append(f'<circle cx="{ox}" cy="{oy}" r="9" fill="{t["panel"]}" stroke="{t["muted"]}" stroke-width="2"/>'
                f'<path class="oH" d="M{ox} {oy - 9}a9 9 0 0 1 0 18z" fill="{amber}"/>'
                f'<g class="oF"><circle cx="{ox}" cy="{oy}" r="10" fill="{green}"/><path d="M{ox - 4.5} {oy}l3 3l6-6" stroke="#fff" stroke-width="2.2" fill="none"/></g>')
    css.append(steps_kf('oH', [(0, 0), (2.3, 1), (3.1, 0)], lambda v: f'opacity:{v}'))
    css.append(steps_kf('oF', [(0, 0), (3.1, 1), (4.8, 0)], lambda v: f'opacity:{v}'))
    # 花畑：動いた歩数で育つ（合格の数ではない）
    fy = 222
    body.append(f'<rect x="{x0}" y="{fy}" width="{cw}" height="5" fill="{mix("#8a6a3a", t["bg"], .7)}"/>')

    u = 3  # 花のドット1つ

    def px(x, y, col, w_=1, h_=1): return f'<rect x="{x}" y="{y}" width="{w_ * u}" height="{h_ * u}" fill="{col}"/>'

    def flower(fx, cls=''):
        stem = px(fx, fy - 5 * u, green, 1, 5) + px(fx + u, fy - 3 * u, green) + px(fx - u, fy - 2 * u, green)
        head = (px(fx - u, fy - 7 * u, c) + px(fx + u, fy - 7 * u, c) + px(fx, fy - 8 * u, c) + px(fx, fy - 6 * u, c) + px(fx, fy - 7 * u, '#f2c94c'))
        if not cls:
            return stem + head
        sprout = px(fx, fy - 2 * u, green, 1, 2) + px(fx + u, fy - 3 * u, green) + px(fx - u, fy - 3 * u, green)
        return f'<g class="{cls}1">{sprout}</g><g class="{cls}2">{stem}{head}</g>'
    for k in range(5):
        body.append(flower(x0 + 16 + k * 36))
    body.append(flower(x0 + 16 + 5 * 36, 'nf'))
    css.append(steps_kf('nf1', [(0, 0), (3.4, 1), (3.9, 0)], lambda v: f'opacity:{v}'))
    css.append(steps_kf('nf2', [(0, 0), (3.9, 1), (7.95, 0)], lambda v: f'opacity:{v}'))
    # 歩数
    body.append(f'<text x="{x0 + cw}" y="{fy - 2}" font-size="11" font-weight="700" text-anchor="end" fill="{due}"><tspan class="n12">12歩</tspan></text>'
                f'<text x="{x0 + cw}" y="{fy - 2}" font-size="11" font-weight="700" text-anchor="end" fill="{due}"><tspan class="n13">13歩</tspan></text>')
    css.append(steps_kf('n12', [(0, 1), (3.4, 0), (7.95, 1)], lambda v: f'opacity:{v}'))
    css.append(steps_kf('n13', [(0, 0), (3.4, 1), (7.95, 0)], lambda v: f'opacity:{v}'))
    g, kc = kid(t, [(0, 340, 226), (1.4, 340, 226), (1.9, ox, oy - 11), (3.5, ox, oy - 11), (4.1, 340, 226), (D, 340, 226)],
                [(0, 1.3, 'l'), (3.1, 4.0, 'j'), (4.8, 5.8, 'l')], 'k')
    body.append(g); css += kc
    return frame(t, w, ''.join(body), css, '就活Hub：次の一手が前に出て、動いた歩数で花畑が育つ')


# ── TeaMy：工程が進み、担当が話す。フウの所で「！」→ 最後にあの子が「結論」を掲げる ──
def teamy(t):
    w = WORKS['teamy']; c = w['color']
    cast = ['シ', 'ナ', 'タ', 'ハ', 'リ', 'ケ', 'フ', 'ユ']
    phases = [('下調べ', 'ユ'), ('会議', 'タハリケユ'), ('フウの爆弾', 'フ'), ('整理', 'ユケ'), ('結論まとめ', 'シナ'), ('清書', 'シ')]
    x0, y0 = 24, 100
    body, css = [], []
    seg_w = 270 / 6
    for i, (ph, who) in enumerate(phases):
        a, b = .3 + i * .9, .3 + (i + 1) * .9
        body.append(f'<rect class="sg{i}" x="{x0 + i * seg_w:.1f}" y="{y0}" width="{seg_w - 4:.1f}" height="5" fill="{c}"/>'
                    f'<rect x="{x0 + i * seg_w:.1f}" y="{y0}" width="{seg_w - 4:.1f}" height="5" fill="{t["line"]}" opacity=".5"/>')
        css.append(steps_kf(f'sg{i}', [(0, 0), (a, 1), (7.8, 0)], lambda v: f'opacity:{v}'))
        body.append(f'<text class="ph{i}" x="{x0}" y="{y0 + 26}" font-size="13" font-weight="700" fill="{t["fg"]}">{ph}</text>')
        css.append(steps_kf(f'ph{i}', [(0, 0), (a, 1), (b if i < 5 else 7.8, 0)], lambda v: f'opacity:{v}'))
    for j, ch in enumerate(cast):
        cx, cy = x0 + 14 + j * 32, y0 + 62
        on = [(0, 0)]
        for i, (_, who) in enumerate(phases):
            a, b = .3 + i * .9, .3 + (i + 1) * .9
            on += [(a, 1 if ch in who else 0)]
        on += [(5.7, 0), (7.8, 0)]
        body.append(f'<g><rect x="{cx - 12}" y="{cy - 12}" width="24" height="24" fill="{t["panel"]}" stroke="{t["line"]}"/>'
                    f'<rect class="cs{j}" x="{cx - 12}" y="{cy - 12}" width="24" height="24" fill="{mix(c, t["panel"], .35)}" stroke="{c}"/>'
                    f'<text x="{cx}" y="{cy + 4.5}" font-size="12" font-weight="700" text-anchor="middle" fill="{t["fg"]}">{ch}</text></g>')
        css.append(steps_kf(f'cs{j}', on, lambda v: f'opacity:{v}'))
    # フウの「！」
    fx = x0 + 14 + 6 * 32
    body.append(f'<g class="bang"><rect x="{fx - 8}" y="{y0 + 30}" width="16" height="16" fill="#e2606e"/><text x="{fx}" y="{y0 + 43}" font-size="13" font-weight="700" text-anchor="middle" fill="#fff">!</text></g>')
    css.append(steps_kf('bang', [(0, 0), (2.1, 1), (2.4, 0), (2.5, 1), (3.0, 0)], lambda v: f'opacity:{v}'))
    # 結論の札：あの子が掲げる
    kx = 345
    body.append(f'<g class="cc"><rect x="{kx - 26}" y="{y0 + 30}" width="52" height="22" fill="{c}"/><text x="{kx}" y="{y0 + 45}" font-size="12" font-weight="700" text-anchor="middle" fill="#fff">結論</text></g>')
    css.append(kf('cc', [(0, (0, 0)), (5.7, (0, 0)), (6.0, (1, -10)), (6.2, (1, 0)), (7.6, (1, 0)), (7.8, (0, 0))],
                  lambda v: f'opacity:{v[0]};transform:translateY({v[1]}px)'))
    g, kc = kid(t, [(0, kx, 214), (D, kx, 214)], [(0, 1.8, 'l'), (2.1, 3.0, 'r' if False else 'l'), (5.8, 7.6, 'j')], 'k')
    css.append(kf('hop', [(0, 0), (5.7, 0), (5.85, -10), (6.0, 0), (D, 0)], lambda v: f'transform:translateY({v}px)'))
    body.append(f'<g class="hop">{g}</g>'); css += kc
    return frame(t, w, ''.join(body), css, 'TeaMy：8人格のAIが工程ごとに議論し、結論を出す')


# ── mamebot：あの子が「お風呂」のボタンを踏む → 家族グループにお知らせが届く ──
def mamebot(t):
    w = WORKS['mamebot']; c = w['color']
    btn = mix(c, t['panel'], .22)
    x0, y0, bw, bh, g = 24, 120, 84, 30, 6
    menu = ['ごはん', '出発・帰宅', 'お風呂', 'ゴミの日']
    body, css = [], []
    for i, m in enumerate(menu):
        bx, by = x0 + (i % 2) * (bw + g), y0 + (i // 2) * (bh + g)
        cls = ' class="bp"' if i == 2 else ''
        body.append(f'<g{cls}><rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{btn}" stroke="{c}"/>'
                    f'<text x="{bx + bw / 2}" y="{by + 19.5}" font-size="11.5" font-weight="700" text-anchor="middle" fill="{t["fg"]}">{m}</text></g>')
    css.append(kf('bp', [(0, 0), (1.9, 0), (2.0, -4), (2.15, 0), (D, 0)], lambda v: f'transform:translateY({v}px)'))
    # 家族グループに届く
    gx, gy = 210, 104
    body.append(f'<g class="gm"><rect x="{gx}" y="{gy}" width="166" height="54" fill="{t["panel"]}" stroke="{c}" stroke-dasharray="4 3"/>'
                f'<text x="{gx + 10}" y="{gy + 18}" font-size="10" fill="{t["muted"]}">家族グループ</text>'
                f'<text x="{gx + 10}" y="{gy + 40}" font-size="12.5" font-weight="700" fill="{t["fg"]}">お風呂を洗いました</text></g>')
    css.append(kf('gm', [(0, (0, 8)), (2.7, (0, 8)), (3.0, (1, 0)), (7.5, (1, 0)), (7.8, (0, 8))],
                  lambda v: f'opacity:{v[0]};transform:translateY({v[1]}px)'))
    # あの子は「お風呂」のボタンの真下へ歩いて、ジャンプして頭で突く（ブロックを下から叩く）
    bx = x0 + bw / 2
    g_, kc = kid(t, [(0, 300, 226), (1.2, 300, 226), (1.6, bx, 226), (7.2, bx, 226), (7.7, 300, 226), (D, 300, 226)], [(0, 1.3, 'l'), (2.9, 3.8, 'j'), (4.2, 5.2, 'r')], 'k')
    css.append(kf('hop', [(0, 0), (1.75, 0), (1.95, -14), (2.15, 0), (D, 0)], lambda v: f'transform:translateY({v}px)'))
    body.append(f'<g class="hop">{g_}</g>'); css += kc
    return frame(t, w, ''.join(body), css, 'mamebot：LINEのボタンだけで、家族に連絡が届く')


def main(out):
    os.makedirs(out, exist_ok=True)
    for th, t in THEMES.items():
        for wid, fn in (('shukatsu', shukatsu), ('teamy', teamy), ('mamebot', mamebot)):
            open(os.path.join(out, f'works-{wid}-{th}.svg'), 'w').write(fn(t))
    print('ok works cards')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'dist')
