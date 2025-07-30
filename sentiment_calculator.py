import akshare as ak
import pandas as pd
import numpy as np

def get_cyb_data():
    """获取创业板指历史数据"""
    cyb_df = ak.stock_zh_index_daily(symbol="sz399006")
    cyb_df['date'] = pd.to_datetime(cyb_df['date'])
    cyb_df.set_index('date', inplace=True)
    return cyb_df

def calculate_sentiment(df):
    """计算贪婪与恐惧指数"""
    # 计算价格变动
    df['pct_change'] = df['close'].pct_change() * 100
    
    # 计算波动率 (10日标准差)
    df['volatility'] = df['pct_change'].rolling(window=10).std()
    
    # 计算成交量波动率
    df["vol_ratio"] = df['volume'] / df['volume'].rolling(window=10).mean()
    
    # 贪婪指数（保持不变）
    df['greed'] = (
        0.4 * np.tanh(3 * df['pct_change'].rolling(window=5).mean()) +
        0.3 * np.sign(df['vol_ratio']) * (np.abs(df['vol_ratio']))**1.5 +
        0.3 * (df['high'] / df['close'].rolling(window=10).max())**2
    ) * 40 + 45
    
    # ============ 恐惧指数计算 - 修复了KeyError问题 ============
    
    # 1. 增强低点检测灵敏度（使用对数放大）
    low_ratio = np.log1p(1 - (df['low'] / df['close'].rolling(window=10).min()))**2
    
    # 2. 强化波动率影响（指数放大）
    vol_factor = (df['volatility'] / df['volatility'].mean())**2.5
    
    # 3. 放量下跌增强因子（非线性放大）- 修复括号问题
    down_factor = np.where(
        (df['pct_change'] < 0) & (df['vol_ratio'] > 1),
        (df['vol_ratio']**1.3) * (abs(df['pct_change'])**1.5),
        0
    )
    
    # 4. 新增恐慌扩散因子（市场恐慌情绪扩散效应）
    panic_spread = np.where(
        (df['pct_change'] < -1.5) & (df['pct_change'].shift(1) < -1.5),
        0.5 * (abs(df['pct_change'].rolling(window=3).sum())**0.7),
        0
    )
    
    # 5. 计算初始恐惧指数（不使用动量因子）
    df['fear_initial'] = (
        0.35 * low_ratio +      # 低点效应
        0.30 * vol_factor +     # 波动率因子
        0.25 * down_factor +    # 放量下跌因子
        0.10 * panic_spread     # 恐慌扩散因子
    ) * 55 + 49
    
    # 6. 添加市场情绪惯性因子（使用初始恐惧指数）
    momentum_factor = df['fear_initial'].shift(1) * 0.3 * np.sign(df['pct_change'])
    
    # 7. 组合所有因子创建最终恐惧指数
    df['fear'] = df['fear_initial'] + momentum_factor
    
    # 删除临时列
    df = df.drop(columns=['fear_initial'])
    
    # ============ 结束恐惧指数计算 ============
    
    # 限制范围
    df['greed'] = df['greed'].clip(0, 100)
    df['fear'] = df['fear'].clip(0, 100)
    
    return df.dropna()


# 新增的 update_data 函数
def update_data():
    if pd.Timestamp.now().hour > 15:
        try:
            new_data = ak.stock_zh_index_daily(symbol="sz399006")
            historical = pd.read_csv('cyb_sentiment.csv')
            updated = pd.concat([historical, new_data]).drop_duplicates()
            updated.to_csv('cyb_sentiment.csv', index=False)
            print("自动更新成功。")
        except Exception as e:
            print("自动更新失败：", e)



# 主函数
if __name__ == "__main__":
    cyb_data = get_cyb_data()
    sentiment_data = calculate_sentiment(cyb_data)
    sentiment_data.to_csv('cyb_sentiment.csv')
print("数据已更新保存至: cyb_sentiment.csv")

