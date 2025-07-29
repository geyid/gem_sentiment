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
    
    # 计算贪婪指数 (基于上涨动能)
    df['greed'] = (
        0.4 * df['pct_change'].rolling(window=5).mean() +  # 短期趋势
        0.3 * np.log(df['volume'] / df['volume'].rolling(window=30).mean()) +  # 成交量热度
        0.3 * (df['high'] / df['close'].rolling(window=10).max())  # 突破高点
    ) * 20 + 50  # 调整到0-100范围
    
    # 计算恐惧指数 (基于下跌风险)
    df['fear'] = (
        0.5 * (df['low'] / df['close'].rolling(window=10).min()) +  # 接近低点
        0.3 * df['volatility'] +  # 波动加剧
        0.2 * (1 - (df['close'] / df['close'].rolling(window=20).mean()))  # 低于均线
    ) * 20 + 50  # 调整到0-100范围
    
    # 限制范围
    df['greed_raw'] = df['greed']
    df['greed'] = df['greed_raw'].clip(0, 100)

    df['fear_raw'] = df['fear']
    df['fear'] = df['fear_raw'].clip(0, 100)
    
    return df.dropna()

# 主函数
if __name__ == "__main__":
    cyb_data = get_cyb_data()
    sentiment_data = calculate_sentiment(cyb_data)
    sentiment_data.to_csv('cyb_sentiment.csv')


    import os         #查看保存路径
    print("保存路径：", os.path.abspath("cyb_sentiment.csv"))
