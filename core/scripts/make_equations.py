"""Typeset the report's display equations (STIX math font ~ Times New Roman).

Each image is exactly one text-width wide (453 pt) with the formula centred and the
equation number at the right margin, so it can be inserted 1:1 into the Google Doc.
Writes outputs/equations/eqNN.png, outputs/equations/sizes.json and equations.md (LaTeX source).
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.transforms import Bbox  # noqa: E402

from mtl.config import OUTPUT_DIR  # noqa: E402

OUT = OUTPUT_DIR / "equations"
OUT.mkdir(parents=True, exist_ok=True)
WIDTH_PT = 453.0
W_IN = WIDTH_PT / 72.0
plt.rcParams.update({"mathtext.fontset": "stix", "font.family": "STIXGeneral"})

SUMK = r"\sum_{k=0}^{\infty}\gamma^{k}R_{t+k+1}"
BELL = r"\left[R(s,a,s')+\gamma V^{*}(s')\right]"
# (key, [lines], [numbers])  -- numbers are assigned sequentially, one per line
EQS = [
    ("m", [r"M=(S,\;A,\;P,\;R,\;\gamma)"]),
    ("markov*", [r"P(S_{t+1}=s'\mid S_t=s,A_t=a,S_{t-1},A_{t-1},\ldots,S_0,A_0)",
                r"=P(S_{t+1}=s'\mid S_t=s,A_t=a)"]),
    ("return", [r"G_t=\sum_{k=0}^{\infty}\gamma^{k}R_{t+k+1}=R_{t+1}+\gamma R_{t+2}+\gamma^{2}R_{t+3}+\cdots"]),
    ("vpi_def", [r"V^{\pi}(s)=\mathbb{E}_{\pi}\left[G_t\mid S_t=s\right]=\mathbb{E}_{\pi}\left[" + SUMK + r"\mid S_t=s\right]"]),
    ("qpi_def", [r"Q^{\pi}(s,a)=\mathbb{E}_{\pi}\left[G_t\mid S_t=s,A_t=a\right]=\mathbb{E}_{\pi}\left[" + SUMK + r"\mid S_t=s,A_t=a\right]"]),
    ("bellman_exp", [r"V^{\pi}(s)=\sum_{a\in A}\pi(a\mid s)\sum_{s'\in S}P(s'\mid s,a)\left[R(s,a,s')+\gamma V^{\pi}(s')\right]"]),
    ("vstar", [r"V^{*}(s)=\max_{a\in A}\sum_{s'\in S}P(s'\mid s,a)" + BELL]),
    ("qstar", [r"Q^{*}(s,a)=\sum_{s'\in S}P(s'\mid s,a)\left[R(s,a,s')+\gamma\max_{a'\in A}Q^{*}(s',a')\right]"]),
    ("pistar", [r"\pi^{*}(s)=\arg\max_{a\in A}Q^{*}(s,a)"]),
    ("qlearn", [r"Q(S_t,A_t)\leftarrow Q(S_t,A_t)+\alpha\left[R_{t+1}+\gamma\max_{a'}Q(S_{t+1},a')-Q(S_t,A_t)\right]"]),
    ("m2", [r"M=(S,\;A,\;P,\;R,\;\gamma)"]),
    ("state", [r"S_t=(q_{NS},\;q_{EW},\;p,\;e)"]),
    ("queue", [r"q'=\min\left(q_{\max},\;\max\left(0,\;q+\mathrm{arrivals}-\mathrm{departures}\right)\right)"]),
    ("reward", [r"R(s,a,s')=-\left(q'_{NS}+q'_{EW}\right)-c_{\mathrm{switch}}\cdot\mathbf{1}[a=\mathrm{SWITCH}]"]),
    ("optimal", [r"V^{*}(s)=\max_{a\in A}\sum_{s'\in S}P(s'\mid s,a)" + BELL,
                 r"\pi^{*}(s)=\arg\max_{a\in A}Q^{*}(s,a)"]),
]

sizes, md, n = {}, ["# Equations of the report (LaTeX source)\n"], 0
for key, lines in EQS:
    cont = key.endswith("*")           # lines are one equation: a single number
    key = key.rstrip("*")
    nl = len(lines)
    if cont:
        nums = [n + 1]
        n += 1
    else:
        nums = [n + i + 1 for i in range(nl)]
        n += nl
    LH = 0.5                              # line pitch in inches
    H = LH * nl + 0.2
    fig = plt.figure(figsize=(W_IN, H))
    fig.patch.set_alpha(0)
    ys = [1 - (0.1 + LH * (i + 0.5)) / H for i in range(nl)]
    texts = []
    for i, (tex, y) in enumerate(zip(lines, ys)):
        t = fig.text(0.5, y, f"${tex}$", ha="center", va="center", fontsize=12)
        texts.append(t)
    if cont:
        fig.text(0.998, sum(ys) / nl, f"({nums[0]})", ha="right", va="center", fontsize=12)
    else:
        for num, y in zip(nums, ys):
            fig.text(0.998, y, f"({num})", ha="right", va="center", fontsize=12)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    ext = [t.get_window_extent(r) for t in texts]
    width_in = max(e.width for e in ext) / fig.dpi
    assert width_in < W_IN * 0.86, f"{key} too wide: {width_in:.2f} in"
    y0 = min(e.y0 for e in ext) / fig.dpi - 0.05
    y1 = max(e.y1 for e in ext) / fig.dpi + 0.05
    fig.savefig(OUT / f"eq_{key}.png", dpi=300, transparent=True,
                bbox_inches=Bbox([[0, y0], [W_IN, y1]]))
    plt.close(fig)
    sizes[key] = {"w": WIDTH_PT, "h": round((y1 - y0) * 72, 1), "numbers": nums}
    md.append(f"## ({', '.join(map(str, nums))}) {key}\n\n```latex\n" + "\n".join(lines) + "\n```\n")
(OUT / "sizes.json").write_text(json.dumps(sizes, indent=1), encoding="utf-8")
(OUT / "equations.md").write_text("\n".join(md), encoding="utf-8")
print(json.dumps(sizes))
