"""Excel Utils - 图形化界面.

Usage:
    streamlit run src/excel_utils/webui.py
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Excel 数据匹配工具", layout="wide")
st.title("Excel 数据匹配工具")

# ── Initialize session state ──
if "datasets" not in st.session_state:
    st.session_state.datasets: dict[str, pd.DataFrame] = {}
if "matched_df" not in st.session_state:
    st.session_state.matched_df: Optional[pd.DataFrame] = None
if "unmatched_left_df" not in st.session_state:
    st.session_state.unmatched_left_df: Optional[pd.DataFrame] = None
if "unmatched_right_df" not in st.session_state:
    st.session_state.unmatched_right_df: Optional[pd.DataFrame] = None
if "unmatched_raw_df" not in st.session_state:
    st.session_state.unmatched_raw_df: Optional[pd.DataFrame] = None
if "join_cond_count" not in st.session_state:
    st.session_state.join_cond_count = 1


def _strip_suffix(name: str) -> str:
    """去除文件名末尾的数字，用于自动分组."""
    m = re.match(r"^(.+?)[-_]?\d+$", name)
    return m.group(1) if m else name


# ── Sidebar: upload ──
with st.sidebar:
    st.header("1. 上传文件")
    uploaded = st.file_uploader(
        "选择 Excel/CSV 文件（可多选）",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
    )

    if uploaded:
        if st.button("自动加载并合并", type="primary", use_container_width=True):
            groups: dict[str, list[pd.DataFrame]] = {}
            for f in uploaded:
                stem = Path(f.name).stem
                prefix = _strip_suffix(stem)
                try:
                    if f.name.endswith(".csv"):
                        df = pd.read_csv(f)
                    else:
                        df = pd.read_excel(f)
                except Exception as e:
                    st.error(f"读取 {f.name} 失败: {e}")
                    continue
                groups.setdefault(prefix, []).append(df)
                st.write(f"  ✓ {f.name} → 分组 **{prefix}**")

            for prefix, dfs in groups.items():
                merged = dfs[0] if len(dfs) == 1 else pd.concat(dfs, ignore_index=True)
                st.session_state.datasets[prefix] = merged
                suffix = f" (合并 {len(dfs)} 个文件)" if len(dfs) > 1 else ""
                st.success(f"**{prefix}**: {len(merged):,} 行{suffix}")

        st.divider()
        st.caption("或逐个加载：")
        for f in uploaded:
            name = Path(f.name).stem
            if st.button(f"加载 {f.name}", key=f"load_{f.name}"):
                try:
                    if f.name.endswith(".csv"):
                        df = pd.read_csv(f)
                    else:
                        df = pd.read_excel(f)
                    st.session_state.datasets[name] = df
                    st.success(f"{f.name}: {len(df):,} 行")
                except Exception as e:
                    st.error(f"读取失败: {e}")

        if len(st.session_state.datasets) >= 2:
            st.divider()
            st.caption("手动合并已加载的表：")
            merge_candidates = list(st.session_state.datasets.keys())
            merge_selected = st.multiselect(
                "选择要合并的表", merge_candidates, key="merge_sel"
            )
            merge_name = st.text_input("合并后的表名", value="merged", key="merge_name")
            if (
                st.button("合并选中表", key="do_merge")
                and len(merge_selected) >= 2
                and merge_name
            ):
                merged = pd.concat(
                    [st.session_state.datasets[n] for n in merge_selected],
                    ignore_index=True,
                )
                st.session_state.datasets[merge_name] = merged
                st.success(f"合并完成: **{merge_name}** ({len(merged):,} 行)")

    if st.session_state.datasets:
        st.header("已加载数据")
        for k, v in st.session_state.datasets.items():
            st.write(f"- **{k}**: {len(v):,} 行 × {len(v.columns)} 列")


# ── Main area ──
tab1, tab2, tab3 = st.tabs(
    ["模式1: 两表关联匹配", "模式2: 分组聚合比对", "结果下载"]
)

# ═══════════════════════════════════════
# TAB 1: JOIN matching
# ═══════════════════════════════════════
with tab1:
    st.subheader("多表关联匹配")
    st.caption("支持 2-N 张表链式 JOIN、多条件、多种运算符、列截取函数")

    ds_names = list(st.session_state.datasets.keys())
    n_ds = len(ds_names)
    if n_ds < 2:
        st.info("请先在左侧上传至少 2 个文件（可合并后得到多张表）")
    else:
        # ── 选择关联表链 ──
        tc = st.session_state.join_table_count
        # 确保 cond_counts 长度正确
        while len(st.session_state.join_cond_counts) < tc - 1:
            st.session_state.join_cond_counts.append(1)

        st.markdown("### 关联表链")
        chain_info = []
        cols = st.columns(tc)
        for i in range(tc):
            with cols[i]:
                prev = (
                    chain_info[i - 1][0] if i > 0
                    else [n for n in ds_names][0]
                )
                tbl = st.selectbox(
                    f"表{i + 1}",
                    ds_names,
                    key=f"chain_tbl_{i}",
                    index=(
                        min(i, n_ds - 1)
                        if i < n_ds
                        else 0
                    ),
                )
                chain_info.append((tbl, list(st.session_state.datasets[tbl].columns)))

        c_add, c_del, _ = st.columns([1, 1, 4])
        with c_add:
            if tc < n_ds and st.button("+ 添加表", use_container_width=True):
                st.session_state.join_table_count += 1
                st.rerun()
        with c_del:
            if tc > 2 and st.button("- 移除最后", use_container_width=True):
                st.session_state.join_table_count -= 1
                if st.session_state.join_cond_counts:
                    st.session_state.join_cond_counts.pop()
                st.rerun()

        st.markdown("---")

        # ── 每对表之间的匹配条件 ──
        OPERATORS = ["=", "!=", ">", "<", ">=", "<=", "LIKE", "IN"]
        TRANSFORMS = [
            "无",
            "split_part(delimiter, index)",
            "substring(start, length)",
            "upper()",
            "lower()",
        ]

        def _col_expr(col: str, t: str, arg: str) -> str:
            if t == "无" or not t:
                return f'"{col}"'
            if t.startswith("split_part"):
                return f"split_part(\"{col}\", {arg})"
            if t.startswith("substring"):
                return f"substring(\"{col}\", {arg})"
            if t.startswith("upper"):
                return f"upper(\"{col}\")"
            if t.startswith("lower"):
                return f"lower(\"{col}\")"
            return f'"{col}"'

        pair_conditions: list[list[dict]] = []

        for pair_idx in range(tc - 1):
            left_tbl, left_cols = chain_info[pair_idx]
            right_tbl, right_cols = chain_info[pair_idx + 1]

            st.markdown(f"**条件 {pair_idx + 1}**: `{left_tbl}` JOIN `{right_tbl}`")

            conds: list[dict] = []
            n_cond = st.session_state.join_cond_counts[pair_idx]
            for ci in range(n_cond):
                with st.container():
                    c1, c2, c3, c4, c5 = st.columns([2.5, 2, 1, 2.5, 2])
                    with c1:
                        lcol = st.selectbox(
                            f"列" if ci == 0 else f"列",
                            left_cols,
                            key=f"jc_p{pair_idx}_l_{ci}",
                            label_visibility="collapsed" if ci > 0 else "visible",
                        )
                        lt = st.selectbox(
                            "函数",
                            TRANSFORMS,
                            key=f"jc_p{pair_idx}_lt_{ci}",
                            label_visibility="collapsed",
                        )
                        lt_arg = ""
                        if lt and lt.startswith("split_part"):
                            lt_arg = st.text_input(
                                "split_part参数",
                                value="'-', 1",
                                key=f"jc_p{pair_idx}_lta_{ci}",
                            )
                        elif lt and lt.startswith("substring"):
                            lt_arg = st.text_input(
                                "substring参数",
                                value="1, 10",
                                key=f"jc_p{pair_idx}_lta_{ci}",
                            )
                    with c2:
                        op = st.selectbox(
                            "运算符",
                            OPERATORS,
                            key=f"jc_p{pair_idx}_op_{ci}",
                            label_visibility="collapsed" if ci > 0 else "visible",
                        )
                    with c3:
                        if ci > 0:
                            logic = st.selectbox(
                                "",
                                ["AND", "OR"],
                                key=f"jc_p{pair_idx}_log_{ci}",
                            )
                        else:
                            logic = None
                    with c4:
                        rcol = st.selectbox(
                            f"列",
                            right_cols,
                            key=f"jc_p{pair_idx}_r_{ci}",
                            label_visibility="collapsed" if ci > 0 else "visible",
                        )
                        rt = st.selectbox(
                            "函数",
                            TRANSFORMS,
                            key=f"jc_p{pair_idx}_rt_{ci}",
                            label_visibility="collapsed",
                        )
                        rt_arg = ""
                        if rt and rt.startswith("split_part"):
                            rt_arg = st.text_input(
                                "split_part参数",
                                value="'-', 1",
                                key=f"jc_p{pair_idx}_rta_{ci}",
                            )
                        elif rt and rt.startswith("substring"):
                            rt_arg = st.text_input(
                                "substring参数",
                                value="1, 10",
                                key=f"jc_p{pair_idx}_rta_{ci}",
                            )
                    with c5:
                        if (
                            n_cond > 1
                            and st.button("✕", key=f"jc_p{pair_idx}_del_{ci}")
                        ):
                            st.session_state.join_cond_counts[pair_idx] -= 1
                            st.rerun()

                conds.append(
                    {
                        "lcol": lcol,
                        "lt": lt,
                        "lt_arg": lt_arg,
                        "op": op,
                        "rcol": rcol,
                        "rt": rt,
                        "rt_arg": rt_arg,
                        "logic": logic,
                    }
                )

            pair_conditions.append(conds)

            col_btn1, _ = st.columns([1, 4])
            with col_btn1:
                if st.button(
                    f"+ 条件", key=f"add_cond_p{pair_idx}",
                    use_container_width=True,
                ):
                    st.session_state.join_cond_counts[pair_idx] += 1
                    st.rerun()
            st.divider()

        # ── 输出设置 ──
        st.markdown("### 输出设置")
        all_output_cols = []
        for tbl, cols in chain_info:
            for c in cols:
                label = f"{tbl}.{c}"
                if label not in all_output_cols:
                    all_output_cols.append(label)

        output_cols = st.multiselect(
            "选择输出列（不选则输出全部列）",
            all_output_cols,
            key="output_cols",
        )
        sum_cols = st.multiselect(
            "选择求和列（不求和则不选，选了会 GROUP BY 非求和列）",
            all_output_cols,
            key="sum_cols",
        )

        st.markdown("---")

        if st.button("运行匹配", type="primary", key="run_join"):
            try:
                conn = duckdb.connect(":memory:")

                # 注册所有表
                for tbl, _ in chain_info:
                    conn.execute(
                        f'CREATE TABLE "{tbl}" AS '
                        f"SELECT * FROM st.session_state.datasets['{tbl}']"
                    )
                # 用更可靠的方式
                conn.close()
                conn = duckdb.connect(":memory:")
                for tbl_name in [t for t, _ in chain_info]:
                    df = st.session_state.datasets[tbl_name]
                    conn.register(tbl_name, df)

                # ── 构建 JOIN 链 ──
                first_tbl, _ = chain_info[0]
                from_clause = f'"{first_tbl}"'
                join_clauses = ""

                for pi, conds in enumerate(pair_conditions):
                    left_tbl, _ = chain_info[pi]
                    right_tbl, _ = chain_info[pi + 1]

                    parts = []
                    for c in conds:
                        l_expr = _col_expr(c["lcol"], c["lt"], c["lt_arg"])
                        r_expr = _col_expr(c["rcol"], c["rt"], c["rt_arg"])
                        parts.append(
                            {
                                "expr": f'"{left_tbl}".{l_expr} {c["op"]} "{right_tbl}".{r_expr}',
                                "logic": c["logic"],
                            }
                        )

                    on = ""
                    for p in parts:
                        if p["logic"]:
                            on += f"\n    {p['logic']} {p['expr']}"
                        else:
                            on += p["expr"]

                    join_clauses += (
                        f'\nINNER JOIN "{right_tbl}"\n'
                        f"ON {on}"
                    )

                # ── SELECT ──
                if output_cols:
                    display_out = [c for c in output_cols if c not in sum_cols]
                    if sum_cols:
                        sum_parts = ", ".join(
                            f'SUM({c}) AS "{c}_sum"' for c in sum_cols
                        )
                        group_cols = (
                            ", ".join(display_out) if display_out else ""
                        )
                        sel = (
                            f"{group_cols}, {sum_parts}"
                            if group_cols
                            else sum_parts
                        )
                        group_clause = (
                            f"\nGROUP BY {group_cols}" if group_cols else ""
                        )
                    else:
                        sel = ", ".join(output_cols)
                        group_clause = ""
                else:
                    sel = "*"
                    group_clause = ""

                # ── 执行三种查询 ──
                # 1) INNER JOIN → matched
                sql = (
                    f"CREATE TABLE inner_result AS\n"
                    f"SELECT {sel}\n"
                    f"FROM {from_clause}"
                    f"{join_clauses}"
                    f"{group_clause}"
                )
                conn.execute(sql)
                st.session_state.matched_df = conn.execute(
                    "SELECT * FROM inner_result"
                ).fetchdf()

                # 2) anti: 第一张表未匹配
                if tc == 2:
                    # two-table: simple anti_left using pair 0
                    left_tbl, _ = chain_info[0]
                    right_tbl, _ = chain_info[1]
                    parts0 = []
                    for c in pair_conditions[0]:
                        l_expr = _col_expr(c["lcol"], c["lt"], c["lt_arg"])
                        r_expr = _col_expr(c["rcol"], c["rt"], c["rt_arg"])
                        logic = c["logic"] or "AND"
                        parts0.append(
                            f'{logic} "{left_tbl}".{l_expr} {c["op"]} "{right_tbl}".{r_expr}'
                        )
                    inner_where = " ".join(parts0)
                    if inner_where.startswith("AND "):
                        inner_where = inner_where[4:]

                    al_cols = [
                        c.split(".", 1)[1]
                        for c in output_cols
                        if c.startswith(f"{left_tbl}.")
                    ] if output_cols else []
                    sel_al = (
                        ", ".join(f'"{c}"' for c in al_cols)
                        if al_cols
                        else f'"{left_tbl}".*'
                    )
                    conn.execute(
                        f"CREATE TABLE anti_l AS\n"
                        f"SELECT {sel_al}\n"
                        f'FROM "{left_tbl}"\n'
                        f"WHERE NOT EXISTS (\n"
                        f'  SELECT 1 FROM "{right_tbl}"\n'
                        f"  WHERE {inner_where}\n"
                        f")"
                    )
                    st.session_state.unmatched_left_df = conn.execute(
                        "SELECT * FROM anti_l"
                    ).fetchdf()

                    ar_cols = [
                        c.split(".", 1)[1]
                        for c in output_cols
                        if c.startswith(f"{right_tbl}.")
                    ] if output_cols else []
                    sel_ar = (
                        ", ".join(f'"{c}"' for c in ar_cols)
                        if ar_cols
                        else f'"{right_tbl}".*'
                    )
                    conn.execute(
                        f"CREATE TABLE anti_r AS\n"
                        f"SELECT {sel_ar}\n"
                        f'FROM "{right_tbl}"\n'
                        f"WHERE NOT EXISTS (\n"
                        f'  SELECT 1 FROM "{left_tbl}"\n'
                        f"  WHERE {inner_where}\n"
                        f")"
                    )
                    st.session_state.unmatched_right_df = conn.execute(
                        "SELECT * FROM anti_r"
                    ).fetchdf()
                else:
                    # multi-table: anti is complex, skip
                    st.session_state.unmatched_left_df = None
                    st.session_state.unmatched_right_df = None

                st.session_state.unmatched_raw_df = None
                conn.close()

                n1 = len(st.session_state.matched_df)
                n2 = (
                    len(st.session_state.unmatched_left_df)
                    if st.session_state.unmatched_left_df is not None
                    else 0
                )
                n3 = (
                    len(st.session_state.unmatched_right_df)
                    if st.session_state.unmatched_right_df is not None
                    else 0
                )
                st.success(
                    f"完成！匹配成功: {n1:,} 行  |  "
                    f"左表未匹配: {n2:,} 行  |  "
                    f"右表未匹配: {n3:,} 行"
                )

            except Exception as e:
                st.error(f"执行失败: {e}")


# ═══════════════════════════════════════
# TAB 2: Group-aggregate matching
# ═══════════════════════════════════════
with tab2:
    st.subheader("分组聚合比对")
    st.caption("例如：按主编码分组，统计子数据数 vs 期望数 → 找出不一致的")

    ds_names = list(st.session_state.datasets.keys())
    if not ds_names:
        st.info("请先在左侧上传文件")
    else:
        src_name = st.selectbox("数据源", ds_names, key="grp_src")

        if src_name:
            df = st.session_state.datasets[src_name]
            columns = list(df.columns)

            st.markdown("**选择分组列**（包含 `主编码_子编码` 的列）")
            code_col = st.selectbox("编码列", columns, key="grp_code")

            st.markdown("**选择期望数列**（期望的子数据数量）")
            expected_col = st.selectbox(
                "期望数列",
                [c for c in columns if c != code_col],
                key="grp_expected",
            )

            st.markdown("---")
            st.markdown("**选择要展示的列**（取第一行的值）")
            display_cols = st.multiselect("展示列", columns, key="grp_display")

            st.markdown("**选择要求和的列**（数值列）")
            sum_cols = st.multiselect(
                "求和列",
                [c for c in columns if c not in display_cols],
                key="grp_sum",
            )

            separator = st.text_input("编码分隔符", value="-", key="grp_sep")

            if st.button("运行比对", type="primary", key="run_group"):
                try:
                    conn = duckdb.connect(":memory:")
                    conn.execute("CREATE TABLE src AS SELECT * FROM df")

                    main_code_sql = f'split_part("{code_col}", \'{separator}\', 1)'
                    select_parts = [
                        f"{main_code_sql} AS main_code",
                        f'string_agg("{code_col}", \', \') AS sub_codes',
                        "count(*) AS actual_count",
                        f'max(try_cast("{expected_col}" AS INTEGER)) AS expected_count',
                    ]

                    for c in display_cols:
                        select_parts.append(f'first("{c}") AS "{c}"')

                    for c in sum_cols:
                        select_parts.append(
                            f'sum(try_cast("{c}" AS DOUBLE)) AS "{c} all"'
                        )

                    select_clause = ",\n  ".join(select_parts)

                    conn.execute(
                        f"CREATE TABLE agg AS\n"
                        f"SELECT {select_clause}\n"
                        f"FROM src\n"
                        f"GROUP BY {main_code_sql}"
                    )

                    conn.execute(
                        "CREATE TABLE matched AS\n"
                        "SELECT * FROM agg\n"
                        "WHERE actual_count = expected_count"
                    )

                    conn.execute(
                        "CREATE TABLE unmatched_codes AS\n"
                        "SELECT main_code FROM agg\n"
                        "WHERE actual_count != expected_count"
                    )

                    conn.execute(
                        "CREATE TABLE unmatched_raw AS\n"
                        "SELECT src.*\n"
                        "FROM src\n"
                        f"WHERE {main_code_sql} IN (\n"
                        "  SELECT main_code FROM unmatched_codes\n"
                        ")"
                    )

                    matched_df = conn.execute(
                        "SELECT * FROM matched"
                    ).fetchdf()
                    unmatched_raw_df = conn.execute(
                        "SELECT * FROM unmatched_raw"
                    ).fetchdf()
                    conn.close()

                    st.session_state.matched_df = matched_df
                    st.session_state.unmatched_raw_df = unmatched_raw_df
                    st.session_state.unmatched_left_df = None
                    st.session_state.unmatched_right_df = None

                    st.success(
                        f"完成！匹配成功: {len(matched_df):,} 条"
                        f"，匹配失败: {len(unmatched_raw_df):,} 条源数据"
                    )

                except Exception as e:
                    st.error(f"执行失败: {e}")


# ═══════════════════════════════════════
# TAB 3: Download results
# ═══════════════════════════════════════
with tab3:
    st.subheader("下载结果")

    def _download_button(df: pd.DataFrame, label: str, filename: str):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False)
        st.download_button(
            label=f"{label} ({len(df):,} 行)",
            data=buf.getvalue(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    has_any = (
        st.session_state.matched_df is not None
        or st.session_state.unmatched_left_df is not None
        or st.session_state.unmatched_right_df is not None
        or st.session_state.unmatched_raw_df is not None
    )
    if not has_any:
        st.info("请先在模式1或模式2运行匹配")
    else:
        if st.session_state.matched_df is not None:
            _download_button(
                st.session_state.matched_df,
                "下载匹配成功",
                "匹配成功.xlsx",
            )
        if st.session_state.unmatched_left_df is not None:
            _download_button(
                st.session_state.unmatched_left_df,
                "下载左表未匹配",
                "左表未匹配.xlsx",
            )
        if st.session_state.unmatched_right_df is not None:
            _download_button(
                st.session_state.unmatched_right_df,
                "下载右表未匹配",
                "右表未匹配.xlsx",
            )
        if st.session_state.unmatched_raw_df is not None:
            _download_button(
                st.session_state.unmatched_raw_df,
                "下载匹配失败（源数据）",
                "匹配失败_源数据.xlsx",
            )
