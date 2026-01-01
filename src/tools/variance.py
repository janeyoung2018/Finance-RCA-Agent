import pandas as pd


def filter_by_scope(
    df: pd.DataFrame,
    month: str,
    region=None,
    bu=None,
    product_line=None,
    segment=None,
    metric=None,
) -> pd.DataFrame:
    scoped = df[df["month"] == month]
    if region and "region" in scoped.columns:
        scoped = scoped[scoped["region"] == region]
    if bu and "bu" in scoped.columns:
        scoped = scoped[scoped["bu"] == bu]
    if product_line and "product_line" in scoped.columns:
        scoped = scoped[scoped["product_line"] == product_line]
    if segment and "segment" in scoped.columns:
        scoped = scoped[scoped["segment"] == segment]
    if metric and "metric" in scoped.columns:
        scoped = scoped[scoped["metric"] == metric]
    return scoped


def finance_variance(df: pd.DataFrame, comparison: str = "plan") -> pd.DataFrame:
    base_col = "plan" if comparison == "plan" else "prior"
    base_df = df.dropna(subset=[base_col])
    base_df = base_df.copy()
    base_df["variance"] = base_df["actual"] - base_df[base_col]
    return base_df


def summarize_top_contributors(df: pd.DataFrame, group_cols, metric="variance", top_n=5):
    grouped = df.groupby(group_cols)[metric].sum().reset_index()
    grouped["abs_variance"] = grouped[metric].abs()
    top = grouped.sort_values("abs_variance", ascending=False).head(top_n)
    return top[group_cols + [metric]].to_dict(orient="records")
