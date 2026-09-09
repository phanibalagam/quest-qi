"""
gen_figures.py -- all figures for the paper, from the saved result JSON only.

No number is typed by hand here; every value is read from results/.
Outputs PDF (vector) and PNG (300 dpi) into figures/.

Independent work. Carried out on personal time and equipment, not connected to the
author's employment, using only public data. No proprietary, confidential or internal
data of any organization was used. See the Disclaimer in paper.md.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
FIG = os.path.join(ROOT, "figures")

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["DejaVu Serif"],
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.labelsize": 9, "legend.fontsize": 8, "legend.frameon": False,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.15, "grid.linestyle": "-",
    "axes.axisbelow": True,
    # Round 11 (arXiv check, B2): matplotlib's default pdf.fonttype is 3, which
    # embeds Type 3 bitmap fonts in the figure PDFs. Text in a Type 3 font is not
    # selectable or searchable in the compiled paper and many venues reject it.
    # 42 is TrueType, embedded and searchable.
    "pdf.fonttype": 42, "ps.fonttype": 42,
})
COLORS = ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#0072B2", "#56B4E9"]
OURS = "#E76F51"
BASE = "#B0BEC5"
ORACLE = "#8C8C8C"


def load(name):
    return json.load(open(os.path.join(RES, name), encoding="utf-8"))


def fig3_main(base, prop):
    """Headline: nDCG@10 by system on the held-out test split."""
    order = [("minilm", "MiniLM (pretrained)", BASE),
             ("w2v", "word2vec", BASE), ("bm25", "BM25", BASE),
             ("tfidf", "TF-IDF", BASE), ("bge_base", "BGE-base (pretrained)", BASE),
             ("lsa", "LSA", BASE),
             ("hybrid_rrf", "Hybrid RRF", BASE),
             ("hybrid_rrf_dense", "Hybrid RRF + BGE", BASE),
             ("qir_clf", "+ classifier defect prior", OURS),
             ("qir_centroid", "+ centroid defect prior", OURS),
             ("slots_only", "soft metadata filter", ORACLE),
             ("prefilter_hybrid", "metadata prefilter + RRF", ORACLE),
             ("qir_centroid_slots", "centroid prior + metadata", ORACLE),
             ("gold_downweight_control", "gold, down-weight control", ORACLE),
             ("qir_oracle_slots", "oracle category + metadata", ORACLE),
             ("gold_additive_control", "gold, additive control", ORACLE),
             ("gold_lookup_ceiling", "gold lookup (ceiling)", ORACLE)]
    means, los, his, labels, cols = [], [], [], [], []
    for key, label, col in order:
        src = base["summary"] if key in base["summary"] else prop["summary"]
        m = src[key]["ndcg@10"]
        ci = m.get("ci95_cluster") or m["ci95"]
        means.append(m["mean"])
        los.append(m["mean"] - ci[0])
        his.append(ci[1] - m["mean"])
        labels.append(label)
        cols.append(col)

    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    y = np.arange(len(labels))
    ax.barh(y, means, xerr=[los, his], color=cols, height=0.6,
            edgecolor="white", linewidth=0.6,
            error_kw={"ecolor": "#444", "elinewidth": 0.9, "capsize": 2.5})
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("nDCG@10 (held-out test queries, 95% clustered bootstrap CI)")
    ax.set_xlim(0, max(means) * 1.20)
    for yi, m, h in zip(y, means, his):
        ax.text(m + h + max(means) * 0.03, yi, f"{m:.3f}", va="center",
                fontsize=8, color="#333")
    ax.axhline(7.5, color="#999", lw=0.7, ls=":")
    ax.axhline(9.5, color="#999", lw=0.7, ls=":")
    for y_pos, label in [(3.5, "text only"), (8.5, "query prior"),
                         (13.0, "re-executes\nthe predicate")]:
        ax.text(max(means) * 1.15, y_pos, label, rotation=90, va="center",
                ha="center", fontsize=7, color="#777", linespacing=0.9)
    fig.savefig(os.path.join(FIG, "fig3_main.pdf"))
    fig.savefig(os.path.join(FIG, "fig3_main.png"))
    plt.close(fig)


def fig2_family(base, prop):
    """Where text-only retrieval fails: nDCG@10 by question family."""
    fams = [("A_defect_form", "defect ×\nform"), ("B_defect_severity", "defect ×\nseverity"),
            ("D_defect_period", "defect ×\nperiod"), ("E_defect_geography", "defect ×\ngeography"),
            ("C_firm_history", "firm\nhistory"), ("F_site_country", "site\ncountry")]
    systems = [("hybrid_rrf", "Hybrid RRF (BM25+LSA)", BASE, base),
               ("hybrid_rrf_dense", "Hybrid RRF + BGE (pretrained)", "#7FB3AA", base),
               ("qir_centroid", "+ centroid defect prior", OURS, prop),
               ("qir_centroid_slots", "+ metadata filter (re-executes predicate)",
                ORACLE, prop)]
    fig, ax = plt.subplots(figsize=(6.8, 3.0))
    x = np.arange(len(fams))
    width = 0.7 / len(systems)
    for i, (key, label, col, src) in enumerate(systems):
        vals = [src["by_family"][key][f]["ndcg@10"] for f, _ in fams]
        off = (i - len(systems) / 2 + 0.5) * width
        ax.bar(x + off, vals, width * 0.9, label=label, color=col,
               edgecolor="white", linewidth=0.5)
        for xi, v in zip(x, vals):
            if v < 0.02:
                ax.text(xi + off, 0.012, "0", ha="center", va="bottom",
                        fontsize=6, color="#666")
    ax.set_xticks(x)
    ax.set_xticklabels([lbl for _, lbl in fams])
    ax.set_ylabel("nDCG@10")
    ax.set_ylim(0, 1.0)
    ax.axvline(3.5, color="#999", lw=0.8, ls="--")
    ax.text(1.5, 0.94, "defect-semantics questions", ha="center", fontsize=7.5, color="#666")
    ax.text(4.5, 0.94, "entity questions", ha="center", fontsize=7.5, color="#666")
    ax.legend(ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    fig.savefig(os.path.join(FIG, "fig2_family.pdf"))
    fig.savefig(os.path.join(FIG, "fig2_family.png"))
    plt.close(fig)


def fig1_taxonomy(tax):
    """Corpus defect taxonomy: size and cross-validated F1 per category."""
    dist = tax["final_distribution"]
    per = tax["per_category"]
    cats = [c for c in sorted(dist, key=lambda c: -dist[c])]
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 3.4), gridspec_kw={"width_ratios": [1, 1]})
    y = np.arange(len(cats))
    fixes = {"Gmp": "GMP", "Nonsterile": "Non-Sterile"}
    labels = [" ".join(fixes.get(w, w) for w in c.replace("_", " ").title().split())
              for c in cats]

    axes[0].barh(y, [dist[c] for c in cats], color=COLORS[0], height=0.62,
                 edgecolor="white", linewidth=0.5)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(labels, fontsize=7.5)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Events in corpus")
    for yi, c in zip(y, cats):
        axes[0].text(dist[c] + max(dist.values()) * 0.02, yi, str(dist[c]),
                     va="center", fontsize=7, color="#444")
    axes[0].set_xlim(0, max(dist.values()) * 1.16)

    f1 = [per[c]["f1"] if c in per else np.nan for c in cats]
    axes[1].barh(y, f1, color=COLORS[1], height=0.62, edgecolor="white", linewidth=0.5)
    axes[1].set_yticks(y)
    axes[1].set_yticklabels([])
    axes[1].invert_yaxis()
    axes[1].set_xlim(0, 1.0)
    axes[1].set_xlabel("5-fold CV $F_1$ (all prefix-tier remainders)")
    axes[1].axvline(tax["cv_macro_f1"], color=OURS, lw=1.1, ls="--")
    axes[1].axvline(tax["tail_estimate"]["cv_macro_f1_rule_free_subset"],
                    color="#264653", lw=1.1, ls=":")
    axes[1].text(tax["cv_macro_f1"] + 0.02, len(cats) - 0.2,
                 f"macro {tax['cv_macro_f1']:.3f}", fontsize=6.5, color=OURS)
    axes[1].text(0.02, len(cats) - 1.1,
                 f"macro on rule-free subset "
                 f"{tax['tail_estimate']['cv_macro_f1_rule_free_subset']:.3f}",
                 fontsize=6.5, color="#264653")
    for yi, v in zip(y, f1):
        if not np.isnan(v):
            axes[1].text(v + 0.02, yi, f"{v:.2f}", va="center", fontsize=7, color="#444")
    fig.savefig(os.path.join(FIG, "fig1_taxonomy.pdf"))
    fig.savefig(os.path.join(FIG, "fig1_taxonomy.png"))
    plt.close(fig)


def main():
    base = load("retrieval_results.json")
    prop = load("proposed_results.json")
    tax = load("taxonomy_eval.json")
    # Generated in order of first appearance in the manuscript, which is the
    # order they are numbered in: taxonomy (Sec 3.2), family (5.2), main (5.3).
    fig1_taxonomy(tax)
    fig2_family(base, prop)
    fig3_main(base, prop)
    print("wrote:", sorted(f for f in os.listdir(FIG) if f.endswith((".pdf", ".png"))))


if __name__ == "__main__":
    main()
