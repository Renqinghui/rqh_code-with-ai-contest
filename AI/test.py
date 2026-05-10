"""
5g_signal_dashboard.py
5G 路测数据可视化看板应用
针对您提供的 CSV 数据格式定制开发
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime
# 2. 在这里设置中文字体 - 必须紧接在导入 matplotlib 之后
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示为方块的问题
# ================= 第一步：基础设置 =================
st.set_page_config(
    page_title="5G 路测数据可视化看板",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid")


# ================= 第二步：数据加载与预处理 =================
@st.cache_data(ttl=3600)
def load_and_preprocess_data() -> pd.DataFrame:
    """
    加载 CSV 数据并进行预处理
    专门针对您提供的 signal_samples.csv 格式
    """
    # 查找数据文件
    data_files = []
    possible_paths = [
        "./data/signal_samples.csv",
        "./signal_samples.csv",
        "signal_samples.csv"
    ]

    for filepath in possible_paths:
        if os.path.exists(filepath):
            data_files.append(filepath)

    if not data_files:
        st.error("❌ 未找到数据文件 signal_samples.csv")
        st.info(
            "请将文件放在以下任一位置：\n1. ./data/signal_samples.csv\n2. ./signal_samples.csv\n3. signal_samples.csv")
        return create_sample_data()

    # 使用第一个找到的文件
    filepath = data_files[0]
    st.sidebar.success(f"✅ 找到数据文件: {filepath}")

    try:
        # 读取 CSV 文件
        df = pd.read_csv(filepath)
        st.sidebar.info(f"📊 成功加载 {len(df)} 行数据")

        # 显示原始列名
        st.sidebar.text(f"列名: {', '.join(df.columns)}")

        # 列名标准化
        column_mapping = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()

            if 'latitude' in col_lower or 'lat' in col_lower:
                column_mapping[col] = 'Latitude'
            elif 'longitude' in col_lower or 'lon' in col_lower or 'lng' in col_lower:
                column_mapping[col] = 'Longitude'
            elif 'cell' in col_lower and 'id' in col_lower:
                column_mapping[col] = 'Cell_ID'
            elif 'band' in col_lower:
                column_mapping[col] = 'Band'
            elif 'rsrp' in col_lower:
                column_mapping[col] = 'RSRP_dBm'
            elif 'sinr' in col_lower:
                column_mapping[col] = 'SINR_dB'
            elif 'terminal' in col_lower and 'type' in col_lower:
                column_mapping[col] = 'TerminalType'
            elif 'download' in col_lower:
                column_mapping[col] = 'Download_Mbps'

        if column_mapping:
            df = df.rename(columns=column_mapping)
            st.sidebar.success("✅ 已标准化列名")

        # 检查必要列
        required_cols = ['Latitude', 'Longitude', 'Band', 'RSRP_dBm']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            st.error(f"❌ 缺少必要列: {missing_cols}")
            st.info("文档中的现有列: " + ", ".join(df.columns))
            return create_sample_data()

        # 数据类型转换
        numeric_cols = ['RSRP_dBm', 'SINR_dB', 'Download_Mbps'] if 'Download_Mbps' in df.columns else ['RSRP_dBm',
                                                                                                       'SINR_dB']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 删除空值
        df_clean = df.dropna(subset=['Latitude', 'Longitude', 'Band', 'RSRP_dBm'])

        if len(df_clean) < len(df):
            st.sidebar.warning(f"⚠️ 删除 {len(df) - len(df_clean)} 行包含空值的数据")

        st.sidebar.success(f"✅ 数据清洗完成，有效记录: {len(df_clean)} 行")
        return df_clean

    except Exception as e:
        st.error(f"❌ 数据读取失败: {str(e)}")
        return create_sample_data()


def create_sample_data() -> pd.DataFrame:
    """生成示例数据（仅用于演示）"""
    np.random.seed(42)
    n_samples = 500

    data = {
        'Latitude': 31.2 + np.random.uniform(-0.1, 0.1, n_samples),
        'Longitude': 121.4 + np.random.uniform(-0.1, 0.1, n_samples),
        'Cell_ID': np.random.choice(range(1000, 2000), n_samples),
        'Band': np.random.choice(['n28', 'n41', 'n78'], n_samples, p=[0.4, 0.3, 0.3]),
        'RSRP_dBm': np.random.normal(-100, 15, n_samples),
        'SINR_dB': np.random.uniform(0, 30, n_samples),
        'TerminalType': np.random.choice(['Smartphone', 'CPE', 'IoT'], n_samples, p=[0.5, 0.3, 0.2]),
        'Download_Mbps': np.random.uniform(10, 1000, n_samples)
    }

    df = pd.DataFrame(data)
    st.sidebar.warning("⚠️ 正在使用演示数据")
    return df


# ================= 第三步：交互式地图 =================
def assign_signal_color(rsrp: float) -> str:
    """根据 RSRP 值分配颜色"""
    if rsrp > -90:
        return "#00FF00"  # 绿色
    elif rsrp < -110:
        return "#FF0000"  # 红色
    else:
        return "#FFFF00"  # 黄色


def display_map(df: pd.DataFrame) -> None:
    """显示交互式信号热力图"""
    st.header("🗺️ 5G 信号覆盖热力图")
    st.write("地图显示每个测量点的信号强度，颜色根据 RSRP 值变化")

    # 准备地图数据
    map_df = df[["Latitude", "Longitude", "RSRP_dBm"]].copy()
    map_df["color"] = map_df["RSRP_dBm"].apply(assign_signal_color)

    # 显示地图
    st.map(
        map_df,
        latitude="Latitude",
        longitude="Longitude",
        size=15,
        color="color"
    )

    # 颜色图例
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🟢 **信号优秀** (RSRP > -90dBm)")
    with col2:
        st.markdown("🟡 **信号良好** (-110dBm ≤ RSRP ≤ -90dBm)")
    with col3:
        st.markdown("🔴 **信号较差** (RSRP < -110dBm)")


# ================= 第四步：侧边栏筛选器 =================
def setup_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """设置侧边栏筛选器"""
    st.sidebar.header("🔧 数据筛选")

    # 频段筛选
    bands = sorted(df['Band'].unique())
    selected_bands = st.sidebar.multiselect(
        "选择频段:",
        options=bands,
        default=bands,
        help="选择要显示的频段"
    )

    # RSRP 范围筛选
    rsrp_min = float(df['RSRP_dBm'].min())
    rsrp_max = float(df['RSRP_dBm'].max())
    rsrp_range = st.sidebar.slider(
        "RSRP 范围 (dBm):",
        min_value=int(rsrp_min) - 5,
        max_value=int(rsrp_max) + 5,
        value=(int(rsrp_min), int(rsrp_max)),
        help="选择信号强度范围"
    )

    # SINR 筛选
    sinr_threshold = 0
    if 'SINR_dB' in df.columns:
        sinr_min = float(df['SINR_dB'].min())
        sinr_max = float(df['SINR_dB'].max())
        sinr_threshold = st.sidebar.slider(
            "最小 SINR (dB):",
            min_value=int(sinr_min),
            max_value=int(sinr_max),
            value=int(sinr_min),
            help="设置最小信噪比阈值"
        )

    # 终端类型筛选
    selected_terminals = []
    if 'TerminalType' in df.columns:
        terminal_types = sorted(df['TerminalType'].unique())
        selected_terminals = st.sidebar.multiselect(
            "选择终端类型:",
            options=terminal_types,
            default=terminal_types,
            help="选择要显示的终端类型"
        )

    # 应用筛选
    filtered_df = df.copy()

    if selected_bands:
        filtered_df = filtered_df[filtered_df['Band'].isin(selected_bands)]

    filtered_df = filtered_df[
        (filtered_df['RSRP_dBm'] >= rsrp_range[0]) &
        (filtered_df['RSRP_dBm'] <= rsrp_range[1])
        ]

    if 'SINR_dB' in df.columns:
        filtered_df = filtered_df[filtered_df['SINR_dB'] >= sinr_threshold]

    if 'TerminalType' in df.columns and selected_terminals:
        filtered_df = filtered_df[filtered_df['TerminalType'].isin(selected_terminals)]

    st.sidebar.info(f"📈 筛选后记录数: {len(filtered_df)} 条")

    return filtered_df


# ================= 第五步：数据统计图表 =================
def display_charts(df: pd.DataFrame) -> None:
    """显示数据统计图表"""
    st.header("📊 数据统计概览")

    # 创建两列布局
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("各频段基站数量统计")

        # 计算各频段基站数量
        band_counts = df['Band'].value_counts().reset_index()
        band_counts.columns = ['Band', '基站数量']

        fig1, ax1 = plt.subplots(figsize=(8, 5))
        colors = ['#4C72B0', '#55A868', '#C44E52', '#8172B2', '#CCB974']

        bars = ax1.bar(band_counts['Band'], band_counts['基站数量'],
                       color=colors[:len(band_counts)], edgecolor='black')

        ax1.set_title("各频段基站分布", fontsize=16, fontweight='bold', pad=15)
        ax1.set_xlabel("频段", fontsize=12)
        ax1.set_ylabel("基站数量", fontsize=12)

        # 在柱状图上显示数值
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2., height + 0.5,
                     f'{int(height)}', ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        st.pyplot(fig1)
        plt.close(fig1)

    with col2:
        st.subheader("信号强度分布")

        fig2, ax2 = plt.subplots(figsize=(8, 5))

        # 绘制直方图
        n, bins, patches = ax2.hist(df['RSRP_dBm'], bins=20,
                                    edgecolor='black', alpha=0.7,
                                    color='#4C72B0')

        # 添加均值和分界线
        mean_rsrp = df['RSRP_dBm'].mean()
        ax2.axvline(mean_rsrp, color='red', linestyle='--', linewidth=2,
                    label=f'平均值: {mean_rsrp:.1f} dBm')
        ax2.axvline(-90, color='green', linestyle=':', linewidth=1.5, alpha=0.7)
        ax2.axvline(-110, color='orange', linestyle=':', linewidth=1.5, alpha=0.7)

        ax2.set_title("信号强度分布", fontsize=16, fontweight='bold', pad=15)
        ax2.set_xlabel("RSRP (dBm)", fontsize=12)
        ax2.set_ylabel("测量点数量", fontsize=12)
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)

    # 终端类型分布
    if 'TerminalType' in df.columns:
        st.subheader("终端类型分布")

        terminal_counts = df['TerminalType'].value_counts()

        col3, col4 = st.columns(2)

        with col3:
            fig3, ax3 = plt.subplots(figsize=(6, 6))
            colors = ['#FF6B6B', '#4ECDC4', '#FFD166']

            ax3.pie(terminal_counts.values, labels=terminal_counts.index,
                    autopct='%1.1f%%', colors=colors, startangle=90)
            ax3.set_title("终端类型占比", fontsize=14)

            st.pyplot(fig3)
            plt.close(fig3)

        with col4:
            # 显示终端类型统计表
            if 'SINR_dB' in df.columns:
                terminal_stats = df.groupby('TerminalType').agg({
                    'RSRP_dBm': ['mean', 'min', 'max'],
                    'SINR_dB': 'mean'
                }).round(2)
            else:
                terminal_stats = df.groupby('TerminalType').agg({
                    'RSRP_dBm': ['mean', 'min', 'max']
                }).round(2)

            st.dataframe(terminal_stats, use_container_width=True)


# ================= 第六步：关键指标卡片 =================
def display_kpis(df: pd.DataFrame) -> None:
    """显示关键性能指标卡片"""
    st.header("📈 关键性能指标")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        avg_rsrp = df['RSRP_dBm'].mean()
        st.metric(
            label="平均信号强度",
            value=f"{avg_rsrp:.1f} dBm",
            delta=None
        )

    with col2:
        if 'SINR_dB' in df.columns:
            avg_sinr = df['SINR_dB'].mean()
            st.metric(
                label="平均信噪比",
                value=f"{avg_sinr:.1f} dB",
                delta=None
            )
        else:
            st.metric(
                label="测量点数",
                value=f"{len(df)}",
                delta=None
            )

    with col3:
        cell_count = df['Cell_ID'].nunique()
        st.metric(
            label="基站总数",
            value=f"{cell_count} 个",
            delta=None
        )

    with col4:
        band_count = df['Band'].nunique()
        st.metric(
            label="覆盖频段数",
            value=f"{band_count} 类",
            delta=None
        )

    # 信号质量统计
    st.subheader("📶 信号质量统计")

    total = len(df)
    excellent = (df['RSRP_dBm'] > -90).sum()
    good = ((df['RSRP_dBm'] >= -110) & (df['RSRP_dBm'] <= -90)).sum()
    poor = (df['RSRP_dBm'] < -110).sum()

    col5, col6, col7 = st.columns(3)

    with col5:
        st.progress(excellent / total if total > 0 else 0)
        st.metric("信号优秀", f"{excellent} 个", f"{excellent / total * 100:.1f}%")

    with col6:
        st.progress(good / total if total > 0 else 0)
        st.metric("信号良好", f"{good} 个", f"{good / total * 100:.1f}%")

    with col7:
        st.progress(poor / total if total > 0 else 0)
        st.metric("信号较差", f"{poor} 个", f"{poor / total * 100:.1f}%")


# ================= 第七步：侧边栏信息 =================
def setup_sidebar_info(df: pd.DataFrame) -> None:
    """设置侧边栏信息面板"""
    st.sidebar.header("ℹ️ 数据信息")

    # 基础信息
    st.sidebar.info(f"""
    **数据概览:**
    📊 总记录数: {len(df):,} 条
    📐 数据列数: {df.shape[1]} 列
    """)

    # 地理范围
    st.sidebar.markdown("---")
    st.sidebar.subheader("🌍 地理范围")
    st.sidebar.text(f"纬度: {df['Latitude'].min():.4f}° ~ {df['Latitude'].max():.4f}°")
    st.sidebar.text(f"经度: {df['Longitude'].min():.4f}° ~ {df['Longitude'].max():.4f}°")

    # 数据预览
    with st.sidebar.expander("📋 数据预览"):
        st.dataframe(df.head(10), use_container_width=True)

    # 数据导出
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 数据导出")

    if st.sidebar.button("导出当前数据 (CSV)", use_container_width=True):
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.sidebar.download_button(
            label="点击下载",
            data=csv,
            file_name=f"5g_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )


# ================= 第八步：主函数 =================
def main() -> None:
    """主函数"""
    # 应用标题
    st.title("📡 5G 路测信号质量实时监控看板")
    st.caption("基于现网路测数据，实时分析 5G 网络覆盖质量与性能指标")

    # 加载数据
    df = load_and_preprocess_data()

    if df is None or len(df) == 0:
        st.error("❌ 未加载到有效数据，请检查数据文件")
        return

    # 设置侧边栏
    setup_sidebar_info(df)

    # 数据筛选
    filtered_df = setup_sidebar_filters(df)

    # 显示关键指标
    display_kpis(filtered_df)

    # 显示地图
    display_map(filtered_df)

    # 显示图表
    display_charts(filtered_df)

    # 页脚
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    5G 网络优化可视化平台 | 数据时间: 2024年 | 版本: 1.0.0
    </div>
    """, unsafe_allow_html=True)


# ================= 启动应用 =================
if __name__ == "__main__":
    main()