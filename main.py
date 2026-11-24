# tiny-chess-01 entry: mailbox engine, incremental tapered eval (dev version)
import json, os, sys
from urllib.request import Request, urlopen

E = os.environ.get("MAKEFUN_ENV_URL", "")

VALUES = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0}

# piece-square tables, white's view, rows from rank 8 (top) to rank 1 (bottom)
PST = {
    "P": (0, 0, 0, 0, 0, 0, 0, 0,
          98, 134, 61, 95, 68, 126, 34, -11,
          -6, 7, 26, 31, 65, 56, 25, -20,
          -14, 13, 6, 21, 23, 12, 17, -23,
          -27, -2, -5, 12, 17, 6, 10, -25,
          -26, -4, -4, -10, 3, 3, 33, -12,
          -35, -1, -20, -23, -15, 24, 38, -22,
          0, 0, 0, 0, 0, 0, 0, 0),
    "PE": (0, 0, 0, 0, 0, 0, 0, 0,
           178, 173, 158, 134, 147, 132, 165, 187,
           94, 100, 85, 67, 56, 53, 82, 84,
           32, 24, 13, 5, -2, 4, 17, 17,
           13, 9, -3, -7, -7, -10, 3, -1,
           4, 7, -13, -9, -25, -20, -9, -3,
           -18, -9, -10, -3, -4, 7, -12, -15,
           0, 0, 0, 0, 0, 0, 0, 0),
    "N": (-50, -40, -30, -30, -30, -30, -40, -50,
          -40, -20, 0, 0, 0, 0, -20, -40,
          -30, 0, 10, 15, 15, 10, 0, -30,
          -30, 5, 15, 20, 20, 15, 5, -30,
          -30, 0, 15, 20, 20, 15, 0, -30,
          -30, 5, 10, 15, 15, 10, 5, -30,
          -40, -20, 0, 5, 5, 0, -20, -40,
          -50, -40, -30, -30, -30, -30, -40, -50),
    "B": (-20, -10, -10, -10, -10, -10, -10, -20,
          -10, 0, 0, 0, 0, 0, 0, -10,
          -10, 0, 5, 10, 10, 5, 0, -10,
          -10, 5, 5, 10, 10, 5, 5, -10,
          -10, 0, 10, 10, 10, 10, 0, -10,
          -10, 10, 10, 10, 10, 10, 10, -10,
          -10, 5, 0, 0, 0, 0, 5, -10,
          -20, -10, -10, -10, -10, -10, -10, -20),
    "R": (0, 0, 0, 0, 0, 0, 0, 0,
          5, 10, 10, 10, 10, 10, 10, 5,
          -5, 0, 0, 0, 0, 0, 0, -5,
          -5, 0, 0, 0, 0, 0, 0, -5,
          -5, 0, 0, 0, 0, 0, 0, -5,
          -5, 0, 0, 0, 0, 0, 0, -5,
          -5, 0, 0, 0, 0, 0, 0, -5,
          0, 0, 0, 5, 5, 0, 0, 0),
    "Q": (-20, -10, -10, -5, -5, -10, -10, -20,
          -10, 0, 0, 0, 0, 0, 0, -10,
          -10, 0, 5, 5, 5, 5, 0, -10,
          -5, 0, 5, 5, 5, 5, 0, -5,
          0, 0, 5, 5, 5, 5, 0, -5,
          -10, 5, 5, 5, 5, 5, 0, -10,
          -10, 0, 5, 0, 0, 0, 0, -10,
          -20, -10, -10, -5, -5, -10, -10, -20),
    "K": (-30, -40, -40, -50, -50, -40, -40, -30,
          -30, -40, -40, -50, -50, -40, -40, -30,
          -30, -40, -40, -50, -50, -40, -40, -30,
          -30, -40, -40, -50, -50, -40, -40, -30,
          -20, -30, -30, -40, -40, -30, -30, -20,
          -10, -20, -20, -20, -20, -20, -20, -10,
          20, 20, 0, 0, 0, 0, 20, 20,
          20, 30, 10, 0, 0, 10, 30, 20),
    "KE": (-50, -40, -30, -20, -20, -30, -40, -50,
           -30, -20, -10, 0, 0, -10, -20, -30,
           -30, -10, 20, 30, 30, 20, -10, -30,
           -30, -10, 30, 40, 40, 30, -10, -30,
           -30, -10, 30, 40, 40, 30, -10, -30,
           -30, -10, 20, 30, 30, 20, -10, -30,
           -30, -30, 0, 0, 0, 0, -30, -30,
           -50, -30, -30, -30, -30, -30, -30, -50),
}

KN = (21, 19, 12, 8, -8, -12, -19, -21)
KK = (11, 10, 9, 1, -1, -9, -10, -11)
KB = (11, 9, -9, -11)
KR = (10, 1, -1, -10)

SQS = tuple(s for s in range(21, 99) if s % 10 not in (0, 9))

# 120-entry tables per piece char, white positive, black negative (mirrored)
MG = {}
EG = {}
for _p in "PNBRQK":
    _mg = [0] * 120
    _eg = [0] * 120
    _bmg = [0] * 120
    _beg = [0] * 120
    _mtab = PST["P"] if _p == "P" else PST[_p]
    _etab = PST["PE"] if _p == "P" else (PST["KE"] if _p == "K" else PST[_p])
    for _s in SQS:
        _t = (_s // 10 - 2) * 8 + _s % 10 - 1
        _mt = (7 - (_t // 8)) * 8 + _t % 8
        _mg[_s] = VALUES[_p] + _mtab[_t]
        _eg[_s] = VALUES[_p] + _etab[_t]
        _bmg[_s] = -(VALUES[_p] + _mtab[_mt])
        _beg[_s] = -(VALUES[_p] + _etab[_mt])
    MG[_p] = tuple(_mg)
    EG[_p] = tuple(_eg)
    MG[_p.lower()] = tuple(_bmg)
    EG[_p.lower()] = tuple(_beg)

PW = {"N": 1, "B": 1, "R": 2, "Q": 4}
PW.update({k.lower(): v for k, v in PW.items()})

MATE = 30000
BUDGET = 60000

nodes = 0
TT = {}
KILLERS = {}
HISTORY = {}


class Abort(Exception):
    pass


def parse(fen):
    b = [" "] * 120
    rows = fen.split()[0].split("/")
    for r, row in enumerate(rows):
        c = 0
        for ch in row:
            if ch.isdigit():
                for _ in range(int(ch)):
                    b[21 + r * 10 + c] = "."
                    c += 1
            else:
                b[21 + r * 10 + c] = ch
                c += 1
    side = 1 if fen.split()[1] == "w" else -1
    cr = 0
    cst = fen.split()[2]
    if "K" in cst: cr |= 1
    if "Q" in cst: cr |= 2
    if "k" in cst: cr |= 4
    if "q" in cst: cr |= 8
    ep = 0
    eps = fen.split()[3]
    if eps != "-":
        ep = 21 + (8 - int(eps[1])) * 10 + ord(eps[0]) - 97
    return "".join(b), side, cr, ep


def init_state(bd):
    mg = eg = 0
    ph = 0
    wb = bb = 0
    for sq in SQS:
        p = bd[sq]
        if p == ".":
            continue
        mg += MG[p][sq]
        eg += EG[p][sq]
        ph += PW.get(p, 0)
        if p == "B":
            wb += 1
        elif p == "b":
            bb += 1
    return [mg, eg, ph, wb, bb]


def evaluate(S, side):
    mg, eg, ph, wb, bb = S
    if ph > 24:
        ph = 24
    ev = (mg * ph + eg * (24 - ph)) // 24
    ev += (30 * ph + 45 * (24 - ph)) // 24 if wb > 1 else 0
    ev -= (30 * ph + 45 * (24 - ph)) // 24 if bb > 1 else 0
    return ev * side


def attacked(bd, sq, by_white):
    # a white pawn at s attacks s-9 and s-11; a black pawn at s attacks s+9 and s+11
    if by_white:
        if bd[sq + 9] == "P" or bd[sq + 11] == "P":
            return True
        pk, pn, pb, pr, pq = "K", "N", "B", "R", "Q"
    else:
        if bd[sq - 9] == "p" or bd[sq - 11] == "p":
            return True
        pk, pn, pb, pr, pq = "k", "n", "b", "r", "q"
    for d in KN:
        if bd[sq + d] == pn:
            return True
    for d in KK:
        if bd[sq + d] == pk:
            return True
    for d in KB:
        s = sq + d
        while bd[s] == ".":
            s += d
        if bd[s] == pb or bd[s] == pq:
            return True
    for d in KR:
        s = sq + d
        while bd[s] == ".":
            s += d
        if bd[s] == pr or bd[s] == pq:
            return True
    return False


def gen_moves(bd, side, cr, ep):
    out = []
    white = side > 0
    own = str.isupper if white else str.islower
    for f in range(21, 99):
        if f % 10 in (0, 9):
            continue
        p = bd[f]
        if p == "." or p == " " or not own(p):
            continue
        u = p.upper()
        if u == "P":
            d = -10 if white else 10
            last = 2 if white else 9
            t = f + d
            if bd[t] == ".":
                if t // 10 == last:
                    for pr in "qnrb":
                        out.append((f, t, pr))
                else:
                    out.append((f, t, ""))
                    if f // 10 == (8 if white else 3) and bd[t + d] == ".":
                        out.append((f, t + d, ""))
            for dc in (-1, 1):
                t = f + d + dc
                q = bd[t]
                if q != " " and q != "." and not own(q):
                    if t // 10 == last:
                        for pr in "qnrb":
                            out.append((f, t, pr))
                    else:
                        out.append((f, t, ""))
                elif t == ep and ep:
                    out.append((f, t, ""))
        elif u == "N":
            for d in KN:
                t = f + d
                q = bd[t]
                if q == "." or (q != " " and not own(q)):
                    out.append((f, t, ""))
        elif u == "K":
            for d in KK:
                t = f + d
                q = bd[t]
                if q == "." or (q != " " and not own(q)):
                    out.append((f, t, ""))
            if white and f == 95:
                if (cr & 1) and bd[96] == "." and bd[97] == "." and bd[98] == "R" \
                        and not attacked(bd, 95, False) and not attacked(bd, 96, False) and not attacked(bd, 97, False):
                    out.append((95, 97, ""))
                if (cr & 2) and bd[94] == "." and bd[93] == "." and bd[92] == "." and bd[91] == "R" \
                        and not attacked(bd, 95, False) and not attacked(bd, 94, False) and not attacked(bd, 93, False):
                    out.append((95, 93, ""))
            if (not white) and f == 25:
                if (cr & 4) and bd[26] == "." and bd[27] == "." and bd[28] == "r" \
                        and not attacked(bd, 25, True) and not attacked(bd, 26, True) and not attacked(bd, 27, True):
                    out.append((25, 27, ""))
                if (cr & 8) and bd[24] == "." and bd[23] == "." and bd[22] == "." and bd[21] == "r" \
                        and not attacked(bd, 25, True) and not attacked(bd, 24, True) and not attacked(bd, 23, True):
                    out.append((25, 23, ""))
        else:
            dirs = KB if u == "B" else KR if u == "R" else KK
            for d in dirs:
                t = f + d
                while True:
                    q = bd[t]
                    if q == " " or own(q):
                        break
                    out.append((f, t, ""))
                    if q != ".":
                        break
                    t += d
    return out


def make(bd, m, side, cr, ep, S):
    # returns (new board, new castling, new ep, new state)
    f, t, pr = m
    b = list(bd)
    p = b[f]
    u = p.upper()
    v = b[t]
    mg, eg, ph, wb, bb = S
    # remove victim
    if v != ".":
        mg -= MG[v][t]
        eg -= EG[v][t]
        ph -= PW.get(v, 0)
        if v == "B":
            wb -= 1
        elif v == "b":
            bb -= 1
    # move the piece (promotion changes its table)
    npc = (pr.upper() if side > 0 else pr) if pr else p
    mg += MG[npc][t] - MG[p][f]
    eg += EG[npc][t] - EG[p][f]
    if pr:
        ph += PW.get(npc, 0)
        if npc == "B":
            wb += 1
        elif npc == "b":
            bb += 1
    b[f] = "."
    b[t] = npc
    ncr = cr
    if u == "K":
        if side > 0:
            ncr &= ~3
        else:
            ncr &= ~12
        if t - f == 2:
            b[t + 1], b[t - 1] = ".", ("R" if side > 0 else "r")
            mg += MG[b[t - 1]][t - 1] - MG[b[t - 1]][t + 1]
            eg += EG[b[t - 1]][t - 1] - EG[b[t - 1]][t + 1]
        elif f - t == 2:
            b[t - 2], b[t + 1] = ".", ("R" if side > 0 else "r")
            mg += MG[b[t + 1]][t + 1] - MG[b[t + 1]][t - 2]
            eg += EG[b[t + 1]][t + 1] - EG[b[t + 1]][t - 2]
    if f == 98 or t == 98:
        ncr &= ~1
    if f == 91 or t == 91:
        ncr &= ~2
    if f == 28 or t == 28:
        ncr &= ~4
    if f == 21 or t == 21:
        ncr &= ~8
    nep = 0
    if u == "P":
        if abs(t - f) == 20:
            nep = (f + t) // 2
        elif t == ep and ep and v == ".":
            vic = t + (10 if side > 0 else -10)
            b[vic] = "."
            mg -= MG["p" if side > 0 else "P"][vic]
            eg -= EG["p" if side > 0 else "P"][vic]
    return "".join(b), ncr, nep, [mg, eg, ph, wb, bb]


def in_check(bd, side):
    k = bd.index("K" if side > 0 else "k")
    return attacked(bd, k, side < 0)


def uci(m):
    f, t, pr = m
    return "abcdefgh"[f % 10 - 1] + str(10 - f // 10) + "abcdefgh"[t % 10 - 1] + str(10 - t // 10) + pr


def pick(fen, legal, hist):
    global nodes, TT, KILLERS, HISTORY
    bd, side, cr, ep = parse(fen)
    S = init_state(bd)
    TT = {}
    KILLERS = {}
    HISTORY = {}
    nodes = 0
    best = None
    H = hist

    def order(m):
        f, t, pr = m
        s = 0
        v = bd[t]
        if v != "." and v != " ":
            s = 10 * VALUES.get(v.upper(), 0) - VALUES.get(bd[f].upper(), 0)
        if pr:
            s += 8000
        return -s

    moves = sorted(gen_moves(bd, side, cr, ep), key=order)
    if not moves:
        return legal[0] if legal else None

    for depth in range(1, 20):
        try:
            alpha = -2 * MATE
            bmove = None
            for m in moves:
                nb, nc, ne, ns = make(bd, m, side, cr, ep, S)
                if in_check(nb, side):
                    continue
                sc = -_ab(nb, -side, nc, ne, ns, depth - 1, -2 * MATE, -alpha, 1, H)
                if sc > alpha:
                    alpha = sc
                    bmove = m
            if bmove:
                best = bmove
                moves.remove(bmove)
                moves.insert(0, bmove)
        except Abort:
            break
    return uci(best)


def _ab(bd, side, cr, ep, S, depth, alpha, beta, ply, H=()):
    global nodes
    nodes += 1
    if nodes > BUDGET:
        raise Abort
    key = (bd, side, cr, ep)
    if key in H:
        return 0
    e = TT.get(key)
    tmove = None
    if e is not None:
        ed, esc, em, ef = e
        tmove = em
        if ed >= depth:
            if ef == 0:
                return esc
            if ef == 1 and esc >= beta:
                return esc
            if ef == 2 and esc <= alpha:
                return esc
    if depth <= 0:
        return _qs(bd, side, ep, S, alpha, beta, ply)
    chk = in_check(bd, side)
    if chk:
        depth += 1
    if not chk and depth >= 3 and (set(bd) & set("NBRQ" if side > 0 else "nbrq")):
        sc = -_ab(bd, -side, cr, 0, S, depth - 3, -beta, 1 - beta, ply + 1, H)
        if sc >= beta:
            return sc

    km = KILLERS.get(ply, (None, None))

    def order(m):
        if m == tmove:
            return -10 ** 9
        if m == km[0]:
            return -8 * 10 ** 8
        if m == km[1]:
            return -7 * 10 ** 8
        f, t, pr = m
        s = 0
        v = bd[t]
        if v != "." and v != " ":
            s = 10 * VALUES.get(v.upper(), 0) - VALUES.get(bd[f].upper(), 0)
        if pr:
            s += 8000
        s += HISTORY.get((f, t), 0)
        return -s

    moves = sorted(gen_moves(bd, side, cr, ep), key=order)
    legal = 0
    bestsc = -2 * MATE
    bmove = None
    a0 = alpha
    for m in moves:
        nb, nc, ne, ns = make(bd, m, side, cr, ep, S)
        if in_check(nb, side):
            continue
        legal += 1
        if legal == 1:
            sc = -_ab(nb, -side, nc, ne, ns, depth - 1, -beta, -alpha, ply + 1, H)
        else:
            sc = -_ab(nb, -side, nc, ne, ns, depth - 1, -alpha - 1, -alpha, ply + 1, H)
            if alpha < sc < beta:
                sc = -_ab(nb, -side, nc, ne, ns, depth - 1, -beta, -alpha, ply + 1, H)
        if sc > bestsc:
            bestsc = sc
            bmove = m
        if sc > alpha:
            alpha = sc
        if alpha >= beta:
            f, t, pr = m
            HISTORY[(f, t)] = HISTORY.get((f, t), 0) + depth * depth
            if m != km[0]:
                KILLERS[ply] = (m, km[0])
            break
    if legal == 0:
        return -MATE + ply if chk else 0
    flag = 0
    if bestsc <= a0:
        flag = 2
    elif bestsc >= beta:
        flag = 1
    TT[key] = (depth, bestsc, bmove, flag)
    return bestsc


def _qs(bd, side, ep, S, alpha, beta, ply):
    global nodes
    nodes += 1
    if nodes > BUDGET:
        raise Abort
    stand = evaluate(S, side)
    chk = in_check(bd, side)
    if not chk:
        if stand >= beta:
            return stand
        if stand > alpha:
            alpha = stand
        moves = [m for m in gen_moves(bd, side, 0, ep) if bd[m[1]] not in (".", " ") or m[2]]
        best = stand
    else:
        moves = gen_moves(bd, side, 0, ep)
        best = -2 * MATE

    def order(m):
        f, t, pr = m
        v = bd[t]
        s = 10 * VALUES.get(v.upper(), 0) - VALUES.get(bd[f].upper(), 0) if v not in (".", " ") else 0
        if pr:
            s += 8000
        return -s

    moves.sort(key=order)
    for m in moves:
        v = bd[m[1]]
        if not chk and v != "." and v != " ":
            if stand + VALUES.get(v.upper(), 0) + 200 < alpha:
                continue
        nb, nc, ne, ns = make(bd, m, side, 0, ep, S)
        if in_check(nb, side):
            continue
        sc = -_qs(nb, -side, ne, ns, -beta, -alpha, ply + 1)
        if sc > best:
            best = sc
        if sc > alpha:
            alpha = sc
        if alpha >= beta:
            break
    return best


def game_keys(start_fen, moves):
    bd, side, cr, ep = parse(start_fen)
    S = init_state(bd)
    keys = []
    for u in moves:
        keys.append((bd, side, cr, ep))
        m = (21 + (8 - int(u[1])) * 10 + ord(u[0]) - 97,
             21 + (8 - int(u[3])) * 10 + ord(u[2]) - 97,
             u[4] if len(u) > 4 else "")
        bd, cr, ep, S = make(bd, m, side, cr, ep, S)
        side = -side
    return set(keys)


def post(path, body):
    req = Request(E + path, data=json.dumps(body).encode(),
                  headers={"content-type": "application/json"})
    with urlopen(req) as res:
        return json.load(res)


def main():
    while True:
        g = post("/game", {})
        if g["status"] == "done":
            print("done: %sW %sD %sL" % (g.get("wins"), g.get("draws"), g.get("losses")), file=sys.stderr)
            break
        while g["status"] == "your_move":
            H = game_keys(g["start_fen"], g["moves"])
            mv = pick(g["fen"], g["legal_moves"], H)
            if mv not in g["legal_moves"]:
                print("internal move %s refused, falling back" % mv, file=sys.stderr)
                mv = g["legal_moves"][0]
            g = post("/move", {"game": g["game"], "move": mv})
        print("game %s: %s by %s" % (g["game"], g["outcome"], g["reason"]), file=sys.stderr)
        print("  moves: %s" % " ".join(g["moves"]), file=sys.stderr)


if __name__ == "__main__":
    main()
