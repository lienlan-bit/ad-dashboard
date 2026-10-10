import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 设置页面配置为宽屏模式，并优化页面拉伸
st.set_page_config(page_title="广告数据多维透视看板", layout="wide", initial_sidebar_state="expanded")

st.title("📊 广告数据多维透视与看板")
st.caption("🚀 极致性能缓存版：内存级数据预加载，秒级切片，表格列全量自适应展示")

# 1. 内存级数据加载缓存
@st.cache_data(show_spinner="正在极速解析表格数据...", ttl=3600)
def load_data(file):
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        # 使用 openpyxl 引擎加速 excel 读取
        df = pd.read_excel(file, engine='openpyxl')
    return df

# 高亮显示函数：D0 达标率 ≥ 80% 标红字体与浅红背景
def highlight_d0_rate(val):
    try:
        if isinstance(val, str) and '%' in val:
            num = float(val.replace('%', ''))
            if num >= 80.0:
                return 'color: #dc2626; font-weight: bold; background-color: #fee2e2;'
    except Exception:
        pass
    return ''

# 标题 + 右侧【复制表格数据】按钮布局渲染
def render_section_header_and_table(df_to_render, title_text, target_col='DO 达标率', key_prefix="sec"):
    if df_to_render.empty:
        st.info(f"💡 {title_text} - 暂无匹配数据")
        return

    col_title, col_btn = st.columns([0.8, 0.2])
    
    with col_title:
        st.markdown(f"#### {title_text}")
        
    with col_btn:
        tsv_data = df_to_render.to_csv(sep='\t', index=False)
        st.download_button(
            label="📋 一键复制表格",
            data=tsv_data,
            file_name=f"{title_text.strip('📌 ').replace(' ', '_')}.tsv",
            mime="text/tab-separated-values",
            key=f"btn_{key_prefix}",
            use_container_width=True
        )

    # 自动定位达标率列名
    actual_target_col = None
    for candidate in [target_col, 'DO 达标率', 'D0 达标率', 'DO达标率', 'D0达标率', '剧目测出率']:
        if candidate in df_to_render.columns:
            actual_target_col = candidate
            break

    try:
        if actual_target_col:
            styled = df_to_render.style.map(highlight_d0_rate, subset=[actual_target_col])
            st.dataframe(styled, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_to_render, use_container_width=True, hide_index=True)
    except Exception:
        st.dataframe(df_to_render, use_container_width=True, hide_index=True)

# 核心计算函数加缓存：避免重复切片触发全量重算
@st.cache_data(show_spinner=False)
def build_summary_pivot(df_input, group_by_cols):
    if df_input.empty:
        return pd.DataFrame(), 0, 0, 0, 0, 0, 0, 0

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
        for idx in range(len(group_by_cols)):
            sub_cols = group_by_cols[:idx+1]
            grp_sum = df_input.groupby(sub_cols)['_spend'].sum().reset_index()
            grp_sum.rename(columns={'_spend': f'_sp_rank_{idx}'}, inplace=True)
            pivot = pivot.merge(grp_sum, on=sub_cols, how='left')

        rank_cols = [f'_sp_rank_{i}' for i in range(len(group_by_cols))]
        pivot = pivot.sort_values(by=rank_cols + ['_spend'], ascending=[False] * (len(rank_cols) + 1))
        pivot.drop(columns=rank_cols, inplace=True)

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
        for idx in range(len(group_by_cols) - 1):
            col_curr = group_by_cols[idx]
            parent_cols = group_by_cols[:idx+1]
            curr_key = display_df[parent_cols].apply(lambda r: "||".join(r), axis=1)
            mask = curr_key == curr_key.shift(1)
            display_df.loc[mask, col_curr] = ""

    show_cols = group_by_cols + ['花费', 'DO 达标率', 'ROAS', 'CPI', 'CPP', '付费率', 'arppu']
    final_df = pd.concat([display_df[show_cols], summary_row[show_cols]], ignore_index=True)
    return final_df, tot_sp, tot_d0, tot_roas, tot_cpi, tot_cpp, tot_pay_rate, tot_arppu

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
    
    col_account = get_col(['投放账户名称', '账户名称', '账户', '账号名称', '账号', 'account'])
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

    # 🔍 短 ID 筛选与搜索
    selected_ids = []
    if col_id:
        all_ids = sorted(filtered_df[col_id].dropna().astype(str).unique().tolist())
        selected_ids = st.sidebar.multiselect(
            "🔍 搜索/筛选 推广剧目/书籍短ID",
            options=all_ids,
            default=[],
            placeholder="输入或选择短ID (留空全选，单选开启深度视角)"
        )
        if selected_ids:
            filtered_df = filtered_df[filtered_df[col_id].astype(str).isin(selected_ids)]

    st.sidebar.markdown("---")

    # 📅 投放时间筛选
    if col_date:
        filtered_df['_dt'] = pd.to_datetime(filtered_df[col_date], errors='coerce')
        valid_dates = filtered_df['_dt'].dropna()

        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()

            st.sidebar.subheader("📅 投放时间筛选")
            date_range = st.sidebar.date_input(
                "选择时间范围",
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

    st.sidebar.markdown("---")

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

    # ==================== 📌 板块 1：投放平台 x 账户 成效明细 ====================
    if col_platform and col_account:
        plat_acc_df, *_ = build_summary_pivot(filtered_df, [col_platform, col_account])
        render_section_header_and_table(plat_acc_df, "📌 1. 投放平台 × 账户 成效透视明细", key_prefix="s_acc")
        st.markdown("---")

    # ==================== 🎯 板块 2：优化师挑剧全量透视表 ====================
    if col_optimizer and col_id:
        st.markdown("### 🎯 2. 优化师高达标/高于个人大盘剧目全量透视（平台×男女频×剧集）")
        
        opt_list = sorted(filtered_df[col_optimizer].dropna().astype(str).unique().tolist())
        if opt_list:
            selected_opt_for_drama = st.selectbox("👤 请选择要分析的优化师：", options=opt_list, index=0)
            
            opt_df_single = filtered_df[filtered_df[col_optimizer].astype(str) == selected_opt_for_drama]
            
            opt_tot_rev = opt_df_single['_d0_rev'].sum()
            opt_tot_tar = opt_df_single['_d0_target'].sum()
            opt_benchmark_d0 = (opt_tot_rev / opt_tot_tar * 100) if opt_tot_tar > 0 else 0.0
            
            st.info(f"💡 **{selected_opt_for_drama}** 在当前时间段内的个人大盘总体 D0 达标率为：**{opt_benchmark_d0:.2f}%** (筛选条件：剧目达标率 ≥ {opt_benchmark_d0:.2f}% 或 ≥ 80%)")
            
            id_pivot = opt_df_single.groupby([col_id], as_index=False).agg({
                '_spend': 'sum',
                '_d0_rev': 'sum',
                '_d0_target': 'sum'
            })
            id_pivot['D0达标数值'] = id_pivot.apply(lambda r: (r['_d0_rev'] / r['_d0_target'] * 100) if r['_d0_target'] > 0 else 0, axis=1)
            
            valid_passed_ids = id_pivot[
                (id_pivot['D0达标数值'] >= opt_benchmark_d0) | 
                (id_pivot['D0达标数值'] >= 80.0)
            ][col_id].astype(str).tolist()
            
            if valid_passed_ids:
                opt_passed_raw = opt_df_single[opt_df_single[col_id].astype(str).isin(valid_passed_ids)]
                opt_full_cols = [c for c in [col_platform, col_gender, col_cn_name, col_drama_name, col_type, col_dub, col_id] if c]
                
                if opt_full_cols:
                    opt_single_table_df, *_ = build_summary_pivot(opt_passed_raw, opt_full_cols)
                    render_section_header_and_table(
                        opt_single_table_df, 
                        f"📌 {selected_opt_for_drama} - 高达标/超大盘剧目全量明细表 (含FB/TT/男女频/配音/短ID)", 
                        key_prefix="opt_dr_single_table"
                    )
            else:
                st.info(f"优化师 {selected_opt_for_drama} 暂无超越个人大盘或 ≥ 80% 达标率的剧目。")
        st.markdown("---")

    # ==================== ⚠️ 板块 3：连续多日低达标预警止损板块 ====================
    if col_id and col_date and '_dt' in filtered_df.columns:
        st.markdown("### ⚠️ 3. 持续低效/衰退剧目预警止损明细 (满足连续2天<60% 或 连续3天<73% 或 连续4天<78%)")
        
        valid_date_df = filtered_df.dropna(subset=['_dt']).copy()
        
        if not valid_date_df.empty:
            daily_drama_df = valid_date_df.groupby([col_id, '_dt'], as_index=False).agg({
                '_spend': 'sum',
                '_d0_rev': 'sum',
                '_d0_target': 'sum'
            })
            daily_drama_df['daily_d0_rate'] = daily_drama_df.apply(lambda r: (r['_d0_rev'] / r['_d0_target'] * 100) if r['_d0_target'] > 0 else 0.0, axis=1)
            daily_drama_df = daily_drama_df.sort_values(by=[col_id, '_dt'], ascending=[True, True])
            
            warning_ids = set()
            
            for dram_id, grp in daily_drama_df.groupby(col_id):
                rates = grp['daily_d0_rate'].tolist()
                n = len(rates)
                is_warning = False
                
                if n >= 2:
                    for i in range(n - 1):
                        if rates[i] < 60.0 and rates[i+1] < 60.0:
                            is_warning = True
                            break
                if not is_warning and n >= 3:
                    for i in range(n - 2):
                        if rates[i] < 73.0 and rates[i+1] < 73.0 and rates[i+2] < 73.0:
                            is_warning = True
                            break
                if not is_warning and n >= 4:
                    for i in range(n - 3):
                        if rates[i] < 78.0 and rates[i+1] < 78.0 and rates[i+2] < 78.0 and rates[i+3] < 78.0:
                            is_warning = True
                            break
                
                if is_warning:
                    warning_ids.add(str(dram_id))

            if warning_ids:
                warning_raw = filtered_df[filtered_df[col_id].astype(str).isin(warning_ids)]
                warning_cols = [c for c in [col_platform, col_optimizer, col_gender, col_cn_name, col_drama_name, col_type, col_dub, col_id] if c]
                
                if warning_cols:
                    warning_table_df, *_ = build_summary_pivot(warning_raw, warning_cols)
                    st.warning(f"🚨 共发现 {len(warning_ids)} 部符合低效止损条件的预警剧目，请及时调整关停或止损！")
                    render_section_header_and_table(
                        warning_table_df, 
                        "🚨 连续低效/衰退预警剧目全量透视表 (满足连续2天<60% / 3天<73% / 4天<78%)", 
                        key_prefix="warn_dr_single_table"
                    )
            else:
                st.success("🎉 当前筛选范围内暂无符合连续低效（2天<60% / 3天<73% / 4天<78%）的预警剧目，整体大盘健康度良好！")
        st.markdown("---")

    # ==================== 📌 板块 4：广告层级全量多维细分透视 ====================
    full_deep_cols = [c for c in [col_platform, col_account, col_target, col_opt_mode, col_bid, col_ad_type] if c]
    if len(full_deep_cols) >= 3:
        full_deep_df, *_ = build_summary_pivot(filtered_df, full_deep_cols)
        render_section_header_and_table(
            full_deep_df, 
            "📌 4. 广告层级全量多维细分透视 (平台×账户×目标×方式×出价×类型)", 
            key_prefix="s6_2"
        )
        st.markdown("---")

    # ==================== 📌 板块 5：全量剧目明细透视 (全大盘视角) ====================
    detail_cols = [c for c in [col_type, col_cn_name, col_en_name, col_drama_name, col_dub, col_id] if c]
    if detail_cols:
        detail_pivot, *_ = build_summary_pivot(filtered_df, detail_cols)
        render_section_header_and_table(detail_pivot, "📌 5. 全量每部书籍/剧集数据明细透视 (按花费降序)", key_prefix="m2_all")

else:
    st.info("👋 请在上方上传 Excel / CSV 表格开始全自动透视分析。")