import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 页面设置
st.set_page_config(
    page_title="创业板指情绪指数",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 标题
st.title("📈 创业板指情绪指数分析")
st.markdown("基于市场行为量化贪婪与恐惧情绪")

# 加载数据
@st.cache_data
def load_data():
    return pd.read_csv('cyb_sentiment.csv', parse_dates=['date'])

df = load_data()

# 侧边栏控制
st.sidebar.header("控制面板")
start_date = st.sidebar.date_input("开始日期", value=df['date'].min())
end_date = st.sidebar.date_input("结束日期", value=df['date'].max())
show_table = st.sidebar.checkbox("显示原始数据", value=True)

# 过滤数据
filtered_df = df[(df['date'] >= pd.Timestamp(start_date)) & 
                (df['date'] <= pd.Timestamp(end_date))]

# 情绪指数折线图
st.subheader("情绪指数趋势")
fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=filtered_df['date'], y=filtered_df['greed'],
    mode='lines', name='贪婪指数', line=dict(color='green', width=2)
))
fig1.add_trace(go.Scatter(
    x=filtered_df['date'], y=filtered_df['fear'],
    mode='lines', name='恐惧指数', line=dict(color='red', width=2)
))

# 添加情绪区间
fig1.add_hrect(y0=70, y1=100, fillcolor="lightgreen", opacity=0.2, 
              annotation_text="贪婪区域", annotation_position="top left")
fig1.add_hrect(y0=0, y1=30, fillcolor="lightcoral", opacity=0.2, 
              annotation_text="恐惧区域", annotation_position="bottom left")

fig1.update_layout(
    height=500,
    xaxis_title="日期",
    yaxis_title="情绪指数",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig1, use_container_width=True)

# 指数与价格对比
st.subheader("情绪指数与创业板指价格对比")
col1, col2 = st.columns(2)

with col1:
    # 贪婪指数与价格
    fig2 = px.scatter(
        filtered_df, x='greed', y='close', 
        trendline="ols", color='volatility',
        labels={'greed': '贪婪指数', 'close': '收盘价'},
        title="贪婪指数 vs 价格"
    )
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    # 恐惧指数与价格
    fig3 = px.scatter(
        filtered_df, x='fear', y='close', 
        trendline="ols", color='volatility',
        labels={'fear': '恐惧指数', 'close': '收盘价'},
        title="恐惧指数 vs 价格"
    )
    st.plotly_chart(fig3, use_container_width=True)

# 数据表格
if show_table:
    st.subheader("历史情绪数据")
    st.dataframe(
        filtered_df[['date', 'close', 'greed', 'fear', 'volatility']].rename(columns={
            'date': '日期',
            'close': '收盘价',
            'greed': '贪婪指数',
            'fear': '恐惧指数',
            'volatility': '波动率'
        }),
        height=400,
        use_container_width=True
    )

# 最新情绪状态
latest = filtered_df.iloc[-1]
st.subheader("当前市场情绪状态")

col1, col2, col3 = st.columns(3)
col1.metric("贪婪指数", f"{latest['greed']:.1f}", 
           "极度贪婪" if latest['greed'] > 85 else 
           "贪婪" if latest['greed'] > 70 else 
           "中性" if latest['greed'] > 40 else "谨慎")
col2.metric("恐惧指数", f"{latest['fear']:.1f}", 
           "极度恐惧" if latest['fear'] < 15 else 
           "恐惧" if latest['fear'] < 30 else 
           "中性" if latest['fear'] < 60 else "贪婪")
col3.metric("创业板指", f"{latest['close']:.2f}", 
           f"{latest['pct_change']:.2f}%")

# 解释说明
st.markdown("""
### 情绪指数说明
- **贪婪指数**：量化市场乐观情绪，数值越高表示市场越贪婪
- **恐惧指数**：量化市场悲观情绪，数值越高表示市场越恐惧
- **情绪区间**：
  - >85：极度贪婪（风险区域）
  - 70-85：贪婪
  - 40-70：中性
  - 30-40：谨慎
  - <30：恐惧（可能机会区域）
""")