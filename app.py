import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 设置页面配置为宽屏模式
st.set_page_config(page_title="广告数据多维透视看板", layout="wide")

st.title("📊 广告数据多维透视与看板")
st.caption("🚀 UI全面优化：每个板块右侧内置【📋 复制表格数据】按钮，一键快速粘贴至 Excel/文档")

# 性能优化：缓存表格读取
@st.cache_data(show_spinner="正在加载解析表格数据...")
def load_data(file):
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    return df

# 高亮显示函数：D0 达标率 ≥ 80% 标红字体与浅红背景
def highlight_d0_rate(val):
    try:
        if isinstance(val, str) and '%' in val:
            num = float(val.replace('%', ''))
            if num >= 80.0:
                return 'color: #dc2626; font-weight: bold; background-color: #fee2e2;'
    except:
        pass
    return ''

# ---------------- ✨ 图二同款：标题 + 右侧【复制表格数据】按钮布局 ----------------
def render_section_header_and_table(df_to_render, title_text, target_col='DO 达标率', key_prefix="sec"):
    col_title, col_btn = st.columns([0.78, 0.22])
    
    with col_title:
        st.markdown(f"#### {title_text}")
        
    with col_btn:
        # TSV 格式最适合直接粘贴至 Excel
        tsv_data = df_to_render.to_csv(sep='\t', index=False)
        st.download_button(
            label="📋 复制表格数据",
            data=tsv_data,
            file_name=f"{title_text.strip('📌 ').replace(' ', '_')}.tsv",
            mime="text/tab-separated-values",
            key=f"btn_{key_prefix}",
            use_container_width=True
        )

    # 渲染高亮表格
    try:
        styled = df_to_render.style.map(highlight_d0_rate, subset=[target_col])
    except AttributeError:
        styled = df_to_render.style.applymap(highlight_d0_rate, subset=[target_col])
    st.dataframe(styled, use_container_width=True, hide_index=True)

# 1. 文件上传入口
uploaded_file = st.file_uploader("📂 拖入或选择你的 Excel / CSV 表格文件", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    try:
        df = load_data(uploaded_file)
        st.success(f"成功读取表格！共 {len(df):,} 行原始数据")
    except Exception as e:
        st.error(f"读取文件失败，请检查文件格式: {e}")
        st.stop()

    # 模糊匹配列名辅助函数
    def get_col(keywords, default=None):
        for k in keywords:
            for col in df.columns:
                if k.lower() in str(col).lower():
                    return col
        return default

    # 识别核心列
    col_date = get_col(['日期', '时间', '投放日期', 'date'])
    col_type = get_col(['书籍类型', '类型'])
    col_cn_name = get_col(['中文推广剧目', '中文剧名', '中文'])
    col_en_name = get_col(['英文推广剧目', '推广剧目', 'book'])
    col_drama_name = get_col(['推广剧目/书籍名称', '剧目名称', '书籍名称'])
    col_dub = get_col(['是否配音', '配音'])
    col_gender = get_col(['男女频', '频'])
    col_id = get_col(['推广剧目/书籍短ID', '推广剧目/书籍id', '短id', '剧目id', '书籍id', 'id'])
    
    col_pixel = get_col(['pixel名称', 'pixel', '像素名称', '像素'])
    col_material = get_col(['素材名称', '素材', 'material', '视频名称', '创意名称'])
    col_platform = get_col(['投放平台', '平台', 'channel'])
    col_optimizer = get_col(['优化师', '优化'])
    col_opt_mode = get_col(['优化方式', '优化模式', 'opt'])
    col_target = get_col(['推广目标', '目标'])
    col_bid = get_col(['手动出价的金额/系数', '手动出价', '出价', 'bid'])
    col_ad_type = get_col(['广告类型', '广告样式', 'type'])

    col_spend = get_col(['花费', 'cost', '消耗'])
    col_d0_rev = get_col(['d0_revenue', 'd0收入', '实际收入'])
    col_d0_target = get_col(['d0目标收入', '目标收入', 'd0目标'])
    col_active = get_col(['首日激活用户数', '首日激活', '激活用户'])
    col_pay_users = get_col(['首日付费用户数', '首日付费', '付费用户'])

    # 侧边栏多维切片筛选器
    st.sidebar.header("🎛️ 多维切片筛选")
    filtered_df = df.copy()

    # ---------------- 🔍 短 ID 筛选与搜索 ----------------
    selected_ids = []
    if col_id:
        all_ids = sorted(filtered_df[col_id].dropna().astype(str).unique().tolist())
        selected_ids = st.sidebar.multiselect(
            "🔍 搜索/筛选 推广剧目/书籍短ID",
            options=all_ids,
            default=[],
            placeholder="输入或选择短ID (留空代表全选)"
        )
        if selected_ids:
            filtered_df = filtered_df[filtered_df[col_id].astype(str).isin(selected_ids)]

    st.sidebar.markdown("---")

    # ---------------- 📅 首投日期/时间维度筛选 ----------------
    if col_date:
        filtered_df['_dt'] = pd.to_datetime(filtered_df[col_date], errors='coerce')
        valid_dates = filtered_df['_dt'].dropna()

        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()

            st.sidebar.subheader("📅 投放时间筛选")
            st.sidebar.caption(f"💡 首投起始日: **{min_date}**")

            date_range = st.sidebar.date_input(
                "选择时间范围（从首投日开始）",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )

            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_d, end_d = date_range
                filtered_df = filtered_df[
                    (filtered_df['_dt'].dt.date >= start_d) & 
                    (filtered_df['_dt'].dt.date <= end_d)
                ]
    else:
        st.sidebar.warning("未在表格中匹配到【日期】或【时间】列")

    st.sidebar.markdown("---")

    # 其它维度切片
    slicer_cols = [c for c in [col_optimizer, col_platform, col_target, col_pixel, col_type, col_gender, col_dub] if c is not None]
    for scol in slicer_cols:
        opts = filtered_df[scol].astype(str).unique().tolist()
        selected = st.sidebar.multiselect(f"筛选 {scol}", options=opts, default=opts)
        filtered_df = filtered_df[filtered_df[scol].astype(str).isin(selected)]

    # 预先进行数值向量化转换
    spend_val = pd.to_numeric(filtered_df[col_spend], errors='coerce').fillna(0) if col_spend else 0
    d0_rev_val = pd.to_numeric(filtered_df[col_d0_rev], errors='coerce').fillna(0) if col_d0_rev else 0
    d0_target_val = pd.to_numeric(filtered_df[col_d0_target], errors='coerce').fillna(0) if col_d0_target else 0
    active_val = pd.to_numeric(filtered_df[col_active], errors='coerce').fillna(0) if col_active else 0
    pay_users_val = pd.to_numeric(filtered_df[col_pay_users], errors='coerce').fillna(0) if col_pay_users else 0

    filtered_df['_spend'] = spend_val
    filtered_df['_d0_rev'] = d0_rev_val
    filtered_df['_d0_target'] = d0_target_val
    filtered_df['_active'] = active_val
    filtered_df['_paying'] = pay_users_val

    st.markdown("---")

    # 通用透视计算函数
    def build_summary_pivot(df_input, group_by_cols):
        pivot = df_input.groupby(group_by_cols, as_index=False).agg({
            '_spend': 'sum',
            '_d0_rev': 'sum',
            '_d0_target': 'sum',
            '_active': 'sum',
            '_paying': 'sum'
        })

        if len(group_by_cols) == 1:
            pivot = pivot.sort_values(by='_spend', ascending=False)
        else:
            pivot = pivot.sort_values(by=[group_by_cols[0], '_spend'], ascending=[True, False])

        sp = pivot['_spend'].values
        rev = pivot['_d0_rev'].values
        tar = pivot['_d0_target'].values
        act = pivot['_active'].values
        pay = pivot['_paying'].values

        pivot['DO 达标率'] = [f"{(r/t*100):.2f}%" if t > 0 else "0.00%" for r, t in zip(rev, tar)]
        pivot['ROAS'] = [f"{(r/s*100):.2f}%" if s > 0 else "0.00%" for r, s in zip(rev, sp)]
        pivot['CPI'] = [f"{(s/a):.2f}" if a > 0 else "#DIV/0!" for s, a in zip(sp, act)]
        pivot['CPP'] = [f"{(s/p):.2f}" if p > 0 else "#DIV/0!" for s, p in zip(sp, pay)]
        pivot['付费率'] = [f"{(p/a*100):.2f}%" if a > 0 else "0.00%" for p, a in zip(pay, act)]
        pivot['arppu'] = [f"{(r/p):.2f}" if p > 0 else "#DIV/0!" for r, p in zip(rev, pay)]

        tot_sp = sp.sum()
        tot_rev = rev.sum()
        tot_tar = tar.sum()
        tot_act = act.sum()
        tot_pay = pay.sum()

        tot_d0 = (tot_rev / tot_tar * 100) if tot_tar > 0 else 0
        tot_roas = (tot_rev / tot_sp * 100) if tot_sp > 0 else 0
        tot_cpi = (tot_sp / tot_act) if tot_act > 0 else 0
        tot_cpp = (tot_sp / tot_pay) if tot_pay > 0 else 0
        tot_pay_rate = (tot_pay / tot_act * 100) if tot_act > 0 else 0
        tot_arppu = (tot_rev / tot_pay) if tot_pay > 0 else 0

        display_df = pivot.copy()
        for col in group_by_cols:
            display_df[col] = display_df[col].astype(str).replace('nan', '-').replace('', '-')

        display_df['花费'] = [f"{s:,.2f}" for s in sp]

        summary_data = {
            group_by_cols[0]: '总计',
            '花费': f"{tot_sp:,.2f}",
            'DO 达标率': f"{tot_d0:.2f}%",
            'ROAS': f"{tot_roas:.2f}%",
            'CPI': f"{tot_cpi:.2f}" if tot_cpi > 0 else "#DIV/0!",
            'CPP': f"{tot_cpp:.2f}" if tot_cpp > 0 else "#DIV/0!",
            '付费率': f"{tot_pay_rate:.2f}%",
            'arppu': f"{tot_arppu:.2f}" if tot_arppu > 0 else "#DIV/0!"
        }
        for col in group_by_cols[1:]:
            summary_data[col] = ""

        summary_row = pd.DataFrame([summary_data])

        if len(group_by_cols) > 1:
            for col in group_by_cols[:-1]:
                mask = display_df[col] == display_df[col].shift(1)
                display_df.loc[mask, col] = ""

        show_cols = group_by_cols + ['花费', 'DO 达标率', 'ROAS', 'CPI', 'CPP', '付费率', 'arppu']
        final_df = pd.concat([display_df[show_cols], summary_row[show_cols]], ignore_index=True)
        return final_df, tot_sp, tot_d0, tot_roas, tot_cpi, tot_cpp, tot_pay_rate, tot_arppu

    # 提取 D0 >= 70% 优质资产的函数
    def extract_passed_assets(df_input, group_col, threshold=70.0):
        if not group_col or group_col not in df_input.columns:
            return pd.DataFrame()
        agg_df = df_input.groupby([group_col], as_index=False).agg({
            '_spend': 'sum',
            '_d0_rev': 'sum',
            '_d0_target': 'sum'
        })
        agg_df['D0达标数值'] = agg_df.apply(lambda r: (r['_d0_rev'] / r['_d0_target'] * 100) if r['_d0_target'] > 0 else 0, axis=1)
        passed = agg_df[agg_df['D0达标数值'] >= threshold].sort_values(by='_spend', ascending=False)
        passed['DO 达标率'] = passed['D0达标数值'].apply(lambda x: f"{x:.2f}%")
        passed['花费 ($)'] = passed['_spend'].apply(lambda x: f"${x:,.2f}")
        return passed[[group_col, '花费 ($)', 'DO 达标率']]

    # 辅助函数：处理近 3 天爆款素材过滤与计算
    def process_recent_good_materials(df_source, material_column, threshold=80.0):
        mat_pivot = df_source.groupby([material_column], as_index=False).agg({
            '_spend': 'sum',
            '_d0_rev': 'sum',
            '_d0_target': 'sum',
            '_active': 'sum',
            '_paying': 'sum'
        })
        sp_r = mat_pivot['_spend'].values
        rev_r = mat_pivot['_d0_rev'].values
        tar_r = mat_pivot['_d0_target'].values
        act_r = mat_pivot['_active'].values
        pay_r = mat_pivot['_paying'].values

        mat_pivot['DO达标数值'] = [ (r / t * 100) if t > 0 else 0 for r, t in zip(rev_r, tar_r) ]
        mat_pivot['DO 达标率'] = [ f"{(r/t*100):.2f}%" if t > 0 else "0.00%" for r, t in zip(rev_r, tar_r) ]
        mat_pivot['ROAS'] = [ f"{(r/s*100):.2f}%" if s > 0 else "0.00%" for r, s in zip(rev_r, sp_r) ]
        mat_pivot['CPI'] = [ f"{(s/a):.2f}" if a > 0 else "#DIV/0!" for s, a in zip(sp_r, act_r) ]
        mat_pivot['CPP'] = [ f"{(s/p):.2f}" if p > 0 else "#DIV/0!" for s, p in zip(sp_r, pay_r) ]
        mat_pivot['付费率'] = [ f"{(p/a*100):.2f}%" if a > 0 else "0.00%" for p, a in zip(pay_r, act_r) ]
        mat_pivot['arppu'] = [ f"{(r/p):.2f}" if p > 0 else "#DIV/0!" for r, p in zip(rev_r, pay_r) ]

        good_mats = mat_pivot[mat_pivot['DO达标数值'] >= threshold].sort_values(by='_spend', ascending=False)
        return good_mats

    # ==================== 🎯 【单剧集/短ID 深度透视板块】 ====================
    if selected_ids and len(selected_ids) == 1:
        cur_id = selected_ids[0]
        
        first_launch_str = ""
        if col_date and '_dt' in filtered_df.columns:
            id_dates = filtered_df['_dt'].dropna()
            if not id_dates.empty:
                first_launch_str = f"（首投时间：{id_dates.min().strftime('%Y-%m-%d')}）"

        st.subheader(f"🎯 推广剧目/书籍短ID: {cur_id} 深度透视 {first_launch_str}")
        
        # 1. 投放平台数据拆分对比
        if col_platform:
            pf_df, tot_sp, tot_d0, tot_roas, tot_cpi, tot_cpp, tot_pay_rate, tot_arppu = build_summary_pivot(filtered_df, [col_platform])
            render_section_header_and_table(pf_df, "📌 1. 投放平台数据拆分对比", key_prefix="s1")

        # 2. 优化师数据对比
        if col_optimizer:
            opt_df, *_ = build_summary_pivot(filtered_df, [col_optimizer])
            render_section_header_and_table(opt_df, "📌 2. 优化师数据对比", key_prefix="s2")

        # 3. 投放平台 x 优化师拆分对比
        if col_platform and col_optimizer:
            pf_opt_df, *_ = build_summary_pivot(filtered_df, [col_platform, col_optimizer])
            render_section_header_and_table(pf_opt_df, "📌 3. 投放平台 × 优化师拆分对比", key_prefix="s3")

        # 4. 投放平台 x Pixel名称 成效拆分对比
        if col_platform and col_pixel:
            pf_px_df, *_ = build_summary_pivot(filtered_df, [col_platform, col_pixel])
            render_section_header_and_table(pf_px_df, "📌 4. 投放平台 × Pixel名称 成效透视对比", key_prefix="s4")

        # 5. 投放平台 x 推广目标 x 广告类型 拆分对比
        plat_target_ad_cols = [c for c in [col_platform, col_target, col_ad_type] if c]
        if len(plat_target_ad_cols) >= 2:
            pta_df, *_ = build_summary_pivot(filtered_df, plat_target_ad_cols)
            render_section_header_and_table(pta_df, "📌 5. 投放平台 × 推广目标 × 广告类型 拆分对比", key_prefix="s5")

        # 6. 广告层级细分全量深度透视
        deep_pivot_cols = [c for c in [col_platform, col_opt_mode, col_target, col_bid, col_ad_type] if c]
        if deep_pivot_cols:
            deep_df, *_ = build_summary_pivot(filtered_df, deep_pivot_cols)
            render_section_header_and_table(deep_df, "📌 6. 广告层级细分全量深度透视", key_prefix="s6")

        # 7. 素材测试全量透视与素材测出率统计
        mat_total_count = 0
        mat_passed_count = 0
        mat_pass_rate_str = "0.00%"

        if col_material:
            st.markdown("---")
            mat_group_cols = [c for c in [col_cn_name, col_gender, col_dub, col_id, col_material] if c]
            
            if mat_group_cols:
                mat_df, *_ = build_summary_pivot(filtered_df, mat_group_cols)
                render_section_header_and_table(mat_df, "📌 7. 单剧素材测试全量透视（测试素材测出率统计）", key_prefix="s7")

            mat_stat_df = filtered_df.groupby([col_material], as_index=False).agg({
                '_spend': 'sum',
                '_d0_rev': 'sum',
                '_d0_target': 'sum'
            })
            mat_total_count = len(mat_stat_df)
            
            if mat_total_count > 0:
                mat_stat_df['D0达标数值'] = mat_stat_df.apply(lambda r: (r['_d0_rev'] / r['_d0_target'] * 100) if r['_d0_target'] > 0 else 0, axis=1)
                passed_mat_df = mat_stat_df[mat_stat_df['D0达标数值'] >= 70]
                mat_passed_count = len(passed_mat_df)
                mat_pass_rate = (mat_passed_count / mat_total_count * 100)
                mat_pass_rate_str = f"{mat_pass_rate:.2f}%"

            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("总测试素材数", f"{mat_total_count} 条")
            sc2.metric("测出素材数 (D0达标率≥70%)", f"{mat_passed_count} 条")
            sc3.metric("🎯 素材测出率", mat_pass_rate_str)

            # 8. 近 3 天优质爆款素材（三方向拆分）
            st.markdown("#### 🔥 8. 近 3 天优质爆款素材（DO 达标率 ≥ 80%，按方向分类方便直接复制上计划）")
            
            recent_3d_df = filtered_df.copy()
            if col_date and '_dt' in recent_3d_df.columns and not recent_3d_df['_dt'].dropna().empty:
                max_dt = recent_3d_df['_dt'].max()
                three_days_ago = max_dt - timedelta(days=2)
                recent_3d_df = recent_3d_df[recent_3d_df['_dt'] >= three_days_ago]

            fb_df = pd.DataFrame()
            tt_df = pd.DataFrame()
            if col_platform in recent_3d_df.columns:
                fb_df = recent_3d_df[recent_3d_df[col_platform].astype(str).str.lower().str.contains('fb|facebook')]
                tt_df = recent_3d_df[recent_3d_df[col_platform].astype(str).str.lower().str.contains('tt|tiktok')]

            good_all = process_recent_good_materials(recent_3d_df, col_material, 80.0)
            good_fb = process_recent_good_materials(fb_df, col_material, 80.0) if not fb_df.empty else pd.DataFrame()
            good_tt = process_recent_good_materials(tt_df, col_material, 80.0) if not tt_df.empty else pd.DataFrame()

            tab_all, tab_fb, tab_tt = st.tabs([
                f"🌐 全平台汇总爆款 ({len(good_all)}条)", 
                f"🔵 FB平台专属爆款 ({len(good_fb)}条)", 
                f"🎵 TT平台专属爆款 ({len(good_tt)}条)"
            ])

            with tab_all:
                if not good_all.empty:
                    st.success(f"🎉【全平台汇总】近 3 天达标率 ≥ 80% 爆款素材（全选下方框内复制）：")
                    st.code("\n".join(good_all[col_material].tolist()), language="text")
                    disp = good_all.copy()
                    disp['花费'] = [f"{s:,.2f}" for s in disp['_spend'].values]
                    render_section_header_and_table(disp[[col_material, '花费', 'DO 达标率', 'ROAS', 'CPI', 'CPP', '付费率', 'arppu']], "🌐 全平台爆款素材列表", key_prefix="m_all")
                else:
                    st.info("近 3 天全平台暂无汇总达标率 ≥ 80% 的素材。")

            with tab_fb:
                if not good_fb.empty:
                    st.success(f"🔵【FB 平台专属】近 3 天 FB 独立达标率 ≥ 80% 爆款素材（全选复制上 FB 计划）：")
                    st.code("\n".join(good_fb[col_material].tolist()), language="text")
                    disp_fb = good_fb.copy()
                    disp_fb['花费'] = [f"{s:,.2f}" for s in disp_fb['_spend'].values]
                    render_section_header_and_table(disp_fb[[col_material, '花费', 'DO 达标率', 'ROAS', 'CPI', 'CPP', '付费率', 'arppu']], "🔵 FB专属爆款素材列表", key_prefix="m_fb")
                else:
                    st.info("近 3 天 FB 平台暂无独立达标率 ≥ 80% 的素材。")

            with tab_tt:
                if not good_tt.empty:
                    st.success(f"🎵【TT 平台专属】近 3 天 TT 独立达标率 ≥ 80% 爆款素材（全选复制上 TT 计划）：")
                    st.code("\n".join(good_tt[col_material].tolist()), language="text")
                    disp_tt = good_tt.copy()
                    disp_tt['花费'] = [f"{s:,.2f}" for s in disp_tt['_spend'].values]
                    render_section_header_and_table(disp_tt[[col_material, '花费', 'DO 达标率', 'ROAS', 'CPI', 'CPP', '付费率', 'arppu']], "🎵 TT专属爆款素材列表", key_prefix="m_tt")
                else:
                    st.info("近 3 天 TT 平台暂无独立达标率 ≥ 80% 的素材。")

        # ==================== 🎯 9. D0 ≥ 70% 达标优质资产汇总与复测策略报告 ====================
        st.markdown("---")
        st.markdown("### 🎯 9. 达标（DO≥70%）优质资产汇总与后续复测策略分析")

        p_pf = extract_passed_assets(filtered_df, col_platform, 70.0)
        p_opt = extract_passed_assets(filtered_df, col_optimizer, 70.0)
        p_tgt = extract_passed_assets(filtered_df, col_target, 70.0)
        p_mode = extract_passed_assets(filtered_df, col_opt_mode, 70.0)
        p_mat = extract_passed_assets(filtered_df, col_material, 70.0)

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["达标平台", "达标优化师", "达标推广目标", "达标优化方式", "达标素材(前20)"])

        with tab1:
            if not p_pf.empty: st.dataframe(p_pf, use_container_width=True, hide_index=True)
            else: st.info("暂无达标平台")
        with tab2:
            if not p_opt.empty: st.dataframe(p_opt, use_container_width=True, hide_index=True)
            else: st.info("暂无达标优化师")
        with tab3:
            if not p_tgt.empty: st.dataframe(p_tgt, use_container_width=True, hide_index=True)
            else: st.info("暂无达标推广目标")
        with tab4:
            if not p_mode.empty: st.dataframe(p_mode, use_container_width=True, hide_index=True)
            else: st.info("暂无达标优化方式")
        with tab5:
            if not p_mat.empty: st.dataframe(p_mat.head(20), use_container_width=True, hide_index=True)
            else: st.info("暂无达标素材")

        str_pf = ", ".join(p_pf[col_platform].tolist()) if not p_pf.empty else "无"
        str_opt = ", ".join(p_opt[col_optimizer].tolist()) if not p_opt.empty else "无"
        str_tgt = ", ".join(p_tgt[col_target].tolist()) if not p_tgt.empty else "无"
        str_mode = ", ".join(p_mode[col_opt_mode].tolist()) if not p_mode.empty else "无"
        mats_top_list = p_mat[col_material].tolist() if not p_mat.empty else []
        str_mat_top = "\n  - ".join(mats_top_list[:5]) if mats_top_list else "无"

        retest_report = f"""【复测与扩量策略报告】短ID: {cur_id}
==================================================
【一、 70% 达标资产盘点】
• 达标投放平台: {str_pf}
• 达标优化师: {str_opt}
• 达标推广目标: {str_tgt}
• 达标优化方式: {str_mode}
• 测出素材数: {len(mats_top_list)} 条 (测出率: {mat_pass_rate_str})
  头部测出素材示例:
  - {str_mat_top}

【二、 后续复测与放量动作指南】
1. 🎯 组合搭建复测计划:
   - 将上一步盘点出的【达标平台 + 达标目标 + 达标优化方式】作为黄金组合基础设置。
   - 优先将【测出素材】重新组装到该黄金组合账户中上新计划，初始出价建议参考历史均值 CPP / CPI。

2. 🚀 素材衍生与二次扩量:
   - 对 D0≥70% 的 {len(mats_top_list)} 条测出素材，提取前 3 秒黄金 Hook 与高转化片段，制作 3-5 支微剪/调色/换音衍生视频做二次复测。

3. 💰 预算倾斜策略:
   - 建议将 70% 的新增预算集中分配给【{str_pf}】平台上的黄金组合，余下 30% 用于探路新素材。
==================================================
"""
        st.markdown("📢 **复测与扩量策略报告（一键复制发送至飞书/钉钉/微信/汇报文档）**")
        st.code(retest_report, language="text")

        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("总花费", f"${tot_sp:,.2f}")
        c2.metric("总DO达标率", f"{tot_d0:.2f}%")
        c3.metric("总ROAS", f"{tot_roas:.2f}%")
        c4.metric("总CPI", f"${tot_cpi:.2f}")
        c5.metric("总CPP", f"${tot_cpp:.2f}")
        c6.metric("总付费率", f"{tot_pay_rate:.2f}%")
        c7.metric("总ARPPU", f"${tot_arppu:.2f}")

        st.markdown("---")
    elif selected_ids and len(selected_ids) > 1:
        st.info("💡 提示：在左侧搜索并【仅选择 1 个短ID】时，将自动开启单剧集的深度层级与复测策略分析板块。")

    # ==================== 📌 模块一：本周剧目测出率透视分析 ====================
    if not (selected_ids and len(selected_ids) == 1):
        if col_type:
            drama_group_keys = [c for c in [col_type, col_id] if c]
            drama_agg = filtered_df.groupby(drama_group_keys, as_index=False).agg({
                '_spend': 'sum',
                '_d0_rev': 'sum',
                '_d0_target': 'sum'
            })

            drama_agg['D0达标率'] = drama_agg.apply(lambda r: (r['_d0_rev'] / r['_d0_target']) if r['_d0_target'] > 0 else 0, axis=1)

            tested_dramas = drama_agg[drama_agg['_spend'] > 100]
            passed_dramas = tested_dramas[drama_agg['D0达标率'] > 0.85]

            type_summary = filtered_df.groupby(col_type, as_index=False).agg({'_spend': 'sum'})
            total_spend = type_summary['_spend'].sum()
            type_summary['消耗占比'] = type_summary['_spend'].apply(lambda x: f"{(x/total_spend*100):.2f}%" if total_spend > 0 else "0.00%")
            type_summary['花费 ($)'] = type_summary['_spend'].apply(lambda x: f"${x:,.2f}")

            test_counts = tested_dramas.groupby(col_type).size().to_dict()
            pass_counts = passed_dramas.groupby(col_type).size().to_dict()

            type_summary['测试剧目数 (花费>$100)'] = type_summary[col_type].map(test_counts).fillna(0).astype(int)
            type_summary['测出剧目数'] = type_summary[col_type].map(pass_counts).fillna(0).astype(int)
            type_summary['剧目测出率'] = type_summary.apply(lambda r: f"{(r['测出剧目数']/r['测试剧目数 (花费>$100)']*100):.2f}%" if r['测试剧目数 (花费>$100)'] > 0 else "0.00%", axis=1)

            type_summary_display = type_summary.sort_values(by='_spend', ascending=False)[[col_type, '花费 ($)', '消耗占比', '测试剧目数 (花费>$100)', '测出剧目数', '剧目测出率']]
            type_summary_display.columns = ['书籍类型', '花费 ($)', '消耗占比', '测试剧目数 (花费>$100)', '测出剧目数', '剧目测出率']
            
            render_section_header_and_table(type_summary_display, "📌 本周剧目测出率透视分析 (限制条件: 仅计算花费 > $100 剧目, D0 达标率 > 85% 算测出)", target_col='剧目测出率', key_prefix="m1")
        else:
            st.warning("未包含【书籍类型】列，无法自动计算测出率透视。")

        st.markdown("---")

        # ==================== 📌 模块二：本周每部书籍/剧集数据明细透视 ====================
        group_cols = [c for c in [col_type, col_cn_name, col_en_name, col_drama_name, col_dub, col_id] if c]

        if group_cols:
            detail_pivot = filtered_df.groupby(group_cols, as_index=False).agg({
                '_spend': 'sum',
                '_d0_rev': 'sum',
                '_d0_target': 'sum',
                '_active': 'sum',
                '_paying': 'sum'
            })

            sp_d = detail_pivot['_spend'].values
            rev_d = detail_pivot['_d0_rev'].values
            tar_d = detail_pivot['_d0_target'].values
            act_d = detail_pivot['_active'].values
            pay_d = detail_pivot['_paying'].values

            detail_pivot['D0 达标率'] = [ f"{(r/t*100):.2f}%" if t > 0 else "0.00%" for r, t in zip(rev_d, tar_d) ]
            detail_pivot['CPI'] = [ f"{(s/a):.2f}" if a > 0 else "#DIV/0!" for s, a in zip(sp_d, act_d) ]
            detail_pivot['CPP'] = [ f"{(s/p):.2f}" if p > 0 else "#DIV/0!" for s, p in zip(sp_d, pay_d) ]

            detail_pivot = detail_pivot.sort_values(by='_spend', ascending=False)
            detail_pivot['花费'] = [f"{s:,.2f}" for s in detail_pivot['_spend'].values]

            show_cols = [c for c in group_cols] + ['花费', 'D0 达标率', 'CPI', 'CPP']
            render_section_header_and_table(detail_pivot[show_cols], "📌 本周每部书籍/剧集数据明细透视 (全量, 按花费降序)", key_prefix="m2")
        else:
            st.warning("未能匹配到足够的剧目明细字段。")

else:
    st.info("👋 请在上方上传 Excel / CSV 表格开始全自动透视分析。")