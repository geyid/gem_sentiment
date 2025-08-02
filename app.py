import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime





# 标题
st.title("📈 创业板指情绪指数分析")
st.markdown("基于市场行为量化贪婪与恐惧情绪")


with st.expander("📖 用户操作指导", expanded=True):
    st.markdown("""
    <style>
    .instruction-img {
        max-width: 100%;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 5px;
        margin: 10px 0;
    }
    .instruction-step {
        margin-bottom: 15px;
    }
    </style>
    
    <div class="instruction-step">
        <h4>选择时间范围</h4>
        <p>拖动页面上方的滑块选择日期范围</p>
   
                
     </div>
        <div class="instruction-step">
        <h4>↔️ 图表中缩小时间范围</h4>
        <p>按住鼠标左键或手指滑动，水平左右拖动可快捷缩小时间范围</p>
    </div>
                

    <div class="instruction-step">
        <h4> 缩放图表</h4>
        <p>在图表上拖动鼠标或手指滑动，选择矩形区域进行放大</p>
    </div>
    
    
    <div class="instruction-step">
        <h4> 查看数据点</h4>
        <p>鼠标悬停在曲线上或点击曲线可查看详细数据</p>
    </div>
    
    <div class="instruction-step">
        <h4> 重置视图</h4>
        <p>双击图表可重置为原始视图</p>
    </div>
    """, unsafe_allow_html=True)

def load_data():
    return pd.read_csv(
        "https://raw.githubusercontent.com/geyid/gem_sentiment/main/cyb_sentiment.csv",
        parse_dates=['date']
    )


df = load_data()





# 确保日期格式正确
df['date'] = pd.to_datetime(df['date'])

# 侧边栏控制 - 只保留"显示原始数据"选项
st.sidebar.header("控制面板")
show_table = st.sidebar.checkbox("显示原始数据", value=True)

# 获取日期范围
min_date = max(df['date'].min().date(), datetime.date(2020, 1, 1))  # 限制最早日期为2020-01-01
max_date = df['date'].max().date()


 #添加日期范围滑块
st.subheader("选择日期范围")
  # 确保在顶部引入

selected_range = st.slider(
    "拖动滑块调整时间范围：",
    min_value=min_date,
    max_value=max_date,
    value=(
        max_date - datetime.timedelta(days=120),  # 默认起始：60天前
        max_date                                 # 默认结束：今天（或数据最大日期）
    ),
    format="YYYY-MM-DD"
)

 #过滤数据
start_date, end_date = selected_range
filtered_df = df[(df['date'] >= pd.Timestamp(start_date)) & 
                (df['date'] <= pd.Timestamp(end_date))]



# 情绪指数折线图 - 分成两个独立图表
col1, col2 = st.columns(2)

with col1:
    st.subheader("贪婪指数趋势")
    fig_greed = go.Figure()
    fig_greed.add_trace(go.Scatter(
        x=filtered_df['date'], y=filtered_df['greed'],
        mode='lines', name='贪婪指数', line=dict(color='red', width=2)
    ))
    # 添加贪婪区域标注（正确区间：70-100）
    fig_greed.add_hrect(y0=70, y1=100, fillcolor="lightcoral", opacity=0.2,
                      annotation_text="贪婪区域", annotation_position="top left")
    fig_greed.update_layout(
        height=400,
        xaxis_title="日期",
        yaxis_title="贪婪指数",
        yaxis_range=[20, 100],
        hovermode="x"
    )
    st.plotly_chart(fig_greed, use_container_width=True, config={"displayModeBar": False})

with col2:
    st.subheader("恐惧指数趋势")
    fig_fear = go.Figure()                                                                          
    fig_fear.add_trace(go.Scatter(
        x=filtered_df['date'], y=filtered_df['fear'],
        mode='lines', name='恐惧指数', line=dict(color='green', width=2)
    ))
    # 添加恐惧区域标注（正确区间：70-100）
    fig_fear.add_hrect(y0=70, y1=100, fillcolor="lightgreen", opacity=0.2,
                     annotation_text="恐惧区域", annotation_position="top left")
    fig_fear.update_layout(
        height=400,
        xaxis_title="日期",
        yaxis_title="恐惧指数",
        yaxis_range=[20, 100],
        hovermode="x"
    )
    st.plotly_chart(fig_fear, use_container_width=True, config={"displayModeBar": False})







# 数据表格
if show_table:
    st.subheader("历史情绪数据")
    st.dataframe(
        filtered_df[['date', 'close', 'greed', 'fear', ]].rename(columns={
            'date': '日期',
            'close': '收盘价',
            'greed': '贪婪指数',
            'fear': '恐惧指数',
            
        }),
        height=400,
        use_container_width=True
    )


# 最新情绪状态
if not filtered_df.empty:
    latest = filtered_df.iloc[-1]
    st.subheader("当前市场情绪状态")
    col1, col2, col3 = st.columns(3)

# 贪婪指数状态（保持不变）
    col1.metric("贪婪指数", f"{latest['greed']:.1f}",
           "极度贪婪" if latest['greed'] > 85 else
           "贪婪" if latest['greed'] > 70 else
           "中性" if latest['greed'] > 55 else "谨慎")

# 恐惧指数状态（修正逻辑）
    col2.metric("恐惧指数", f"{latest['fear']:.1f}",
           "极度恐惧" if latest['fear'] > 85 else
           "恐惧" if latest['fear'] > 70 else
           "中性" if latest['fear'] > 55 else "镇定")

# 安全计算涨跌幅
    pct_change = latest['pct_change'] if 'pct_change' in latest and not pd.isna(latest['pct_change']) else 0
    col3.metric("创业板指", f"{latest['close']:.2f}", f"{pct_change:.2f}%")

# 解释说明（修正恐惧指数区域定义）
st.markdown("""
### 情绪指数说明

- **贪婪指数**：量化市场乐观情绪，数值越高表示市场越贪婪
- **恐惧指数**：量化市场悲观情绪，数值越高表示市场越恐惧
- **情绪区间**：
  - **贪婪区域（贪婪指数 > 70）**：市场过热，警惕回调风险
  - **中性区域（贪婪指数55-70）**：市场情绪平稳
  - **谨慎区域（贪婪指数 < 55）**：市场热情不足
  - **恐惧区域（恐惧指数 > 70）**：市场恐慌，可能存在超跌机会
  - **中性区域（恐惧指数55-70）**：市场情绪平稳
  - **淡定区域（恐惧指数 < 55）**：市场恐慌情绪缓解
""")




