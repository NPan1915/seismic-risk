"""Hazard model + rate-change model, with baselines and spatial-block validation.
Rolling setup: train on features before (today-10y) -> labels in last 10y; score present-day features for the next 10y."""
import json, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.inspection import permutation_importance
RATE = ["n_hist", "n_m6_hist", "n_recent10", "n_prior10", "rate_ratio"]
BND = ["dist_boundary_km"]
VOL = ["mag_mean", "mag_max", "mag_std", "depth_mean", "depth_std"]   # lat/lon deliberately excluded
BLOCK_DEG = 30
def rf(): return RandomForestClassifier(n_estimators=300, min_samples_leaf=3, class_weight="balanced_subsample", n_jobs=-1, random_state=42)
def blocks(df): return ((df.lon + 180) // BLOCK_DEG).astype(int) * 100 + ((df.lat + 90) // BLOCK_DEG).astype(int)

def cv(df, feats, y, spatial=True, importance=False):
    splitter = StratifiedGroupKFold(5, shuffle=True, random_state=42) if spatial else StratifiedKFold(5, shuffle=True, random_state=42)
    oof, folds, imp = np.zeros(len(df)), [], pd.Series(0.0, index=feats)
    for tr, te in splitter.split(df, y, blocks(df)):
        m = rf().fit(df.iloc[tr][feats], y.iloc[tr]); p = m.predict_proba(df.iloc[te][feats])[:, 1]; oof[te] = p
        if y.iloc[te].nunique() == 2: folds.append(roc_auc_score(y.iloc[te], p))
        if importance:
            pi = permutation_importance(m, df.iloc[te][feats], y.iloc[te], scoring="roc_auc", n_repeats=5, random_state=42, n_jobs=-1)
            imp += pd.Series(pi.importances_mean, index=feats) / 5
    return dict(auc=roc_auc_score(y, oof), pr_auc=average_precision_score(y, oof),
                fold_auc_mean=float(np.mean(folds)), fold_auc_std=float(np.std(folds))), imp

def evaluate(df, y, models, heuristic):
    rows, imp = [], None
    for name, feats in models.items():
        full = name.startswith("D") or name.startswith("full")
        r, i = cv(df, feats, y, importance=full); rows.append(dict(model=name, **r)); imp = i if full else imp
    for name, col in heuristic.items():
        rows.append(dict(model=name, auc=roc_auc_score(y, df[col]), pr_auc=average_precision_score(y, df[col]), fold_auc_mean=np.nan, fold_auc_std=np.nan))
    leaky, _ = cv(df, list(models.values())[-1], y, spatial=False)
    return pd.DataFrame(rows).round(3), imp.sort_values(ascending=False).round(4), round(leaky["auc"], 3)

def main():
    from common import connect
    from features import build
    conn, today = connect(), pd.Timestamp.now(tz="UTC").normalize()
    df = build(conn, today - pd.DateOffset(years=10), today); df["neg_dist"] = -df.dist_boundary_km   # closer = riskier
    out = dict(generated_at=str(today.date()), n_cells=len(df))

    # ---- Task 1: hazard (any M6+ in next 10y) ----
    y = (df.n_m6_future > 0).astype(int)
    models = {"A. rate only": RATE, "B. boundary only": BND, "C. rate + boundary": RATE + BND, "D. full (+ magnitude/depth volatility)": RATE + BND + VOL}
    tab, imp, leaky = evaluate(df, y, models, {"heuristic: historical M6+ count": "n_m6_hist", "heuristic: closeness to boundary": "neg_dist"})
    best_single = tab[tab.model.str.startswith(("A.", "B."))].auc.max(); full_auc = tab[tab.model.str.startswith("D.")].auc.iloc[0]
    print(f"\n=== HAZARD: P(M6+ in next 10y per 2deg cell) | base rate {y.mean():.2%} | spatial-block 5-fold CV ===\n{tab.to_string(index=False)}")
    print(f"\nFull model AUC with RANDOM (leaky) CV: {leaky}  vs spatial CV: {full_auc}  -> inflation {leaky-full_auc:+.3f}")
    print(f"Full model vs best single-family baseline: {full_auc-best_single:+.3f} AUC\n\nKey drivers (permutation importance, held-out regions):\n{imp}")
    out["hazard"] = dict(base_rate=float(y.mean()), table=tab.to_dict("records"), random_cv_auc=leaky, lift_vs_best_single=round(full_auc-best_single, 3), importance=imp.to_dict())

    # ---- Task 2: rate change (will M4.5+ rate rise >=1.5x in next 10y?) among active cells ----
    s = df[df.n_recent10 >= 10].reset_index(drop=True); y2 = (s.n_m45_future >= 1.5 * s.n_recent10).astype(int)
    if y2.nunique() == 2 and len(s) > 100:
        m2 = {"rate only": RATE, "rate + boundary": RATE + BND, "full": RATE + BND + VOL}
        t2, imp2, leaky2 = evaluate(s, y2, m2, {"heuristic: persistence (recent/prior ratio)": "rate_ratio"})
        print(f"\n=== RATE CHANGE: active cells (n={len(s)}), base rate {y2.mean():.2%} ===\n{t2.to_string(index=False)}\n{imp2}")
        out["rate_change"] = dict(base_rate=float(y2.mean()), table=t2.to_dict("records"), importance=imp2.to_dict())

    # ---- Final models, score the present ----
    now = build(conn, today, today)
    now["risk"] = rf().fit(df[models["D. full (+ magnitude/depth volatility)"]], y).predict_proba(now[models["D. full (+ magnitude/depth volatility)"]])[:, 1]
    now["accel"] = 0.0
    if "rate_change" in out:
        a = rf().fit(s[RATE + BND + VOL], y2); act = now.n_recent10 >= 10
        now.loc[act, "accel"] = a.predict_proba(now.loc[act, RATE + BND + VOL])[:, 1]
    now["vol"] = (now.mag_std / now.mag_std.max() + now.n_recent10 / max(now.n_recent10.max(), 1)) / 2
    now["expected_exposed"] = now.risk * now.pop100                    # people within 100km x P(M6+)
    now["impact"] = (now.risk * np.log10(1 + now.pop100)); now["impact"] /= now.impact.max()
    z = now[now.risk >= 0.5]
    json.dump([dict(lat=r.lat, lon=r.lon, risk=round(r.risk, 3), vol=round(r.vol, 3), maxmag=round(r.mag_max, 1),
                    pop_m=round(r.pop100/1e6, 2), impact=round(r.impact, 3), accel=round(r.accel, 3)) for r in z.itertuples()], open("zones.json", "w"))
    top = now.sort_values("expected_exposed", ascending=False).head(10)[["lat", "lon", "risk", "pop100", "expected_exposed"]].round(2)
    print(f"\n{len(z)} zones -> zones.json\n\nTop 10 by expected human exposure (risk x population within 100km):\n{top.to_string(index=False)}")
    out["top_exposure"] = top.to_dict("records"); json.dump(out, open("metrics.json", "w"), indent=1, default=float)
    import os, shutil                                   # also drop results into the website folder
    if os.path.isdir("vercel-site/public"):
        for f in ("zones.json", "metrics.json"): shutil.copy(f, f"vercel-site/public/{f}")
if __name__ == "__main__": main()
