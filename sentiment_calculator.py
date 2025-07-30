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
    ) * 40 + 40
    
    # 恐惧指数优化（大幅提高灵敏度）
    # 1. 增加波动率的权重和非线性放大
    # 2. 引入放量下跌因子
    # 3. 添加相对强度指标
    df['fear'] = (
        0.4 * (1 - (df['low'] / df['close'].rolling(window=10).min()))**3 +  # 立方放大低点效应
        0.4 * (df['volatility'] / df['volatility'].mean())**1.5 +  # 波动率非线性放大
        0.2 * np.where(
            (df['pct_change'] < 0) & (df['vol_ratio'] > 1),
            df['vol_ratio'] * abs(df['pct_change']),  # 放量下跌增强
            0
        )
    ) * 40 + 48   # 调整系数增强变化幅度
    
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