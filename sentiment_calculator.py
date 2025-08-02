import akshare as ak
import pandas as pd
import numpy as np
import talib



def get_cyb_data():
    """获取创业板指历史数据"""
    cyb_df = ak.stock_zh_index_daily(symbol="sz399006")
    cyb_df['date'] = pd.to_datetime(cyb_df['date'])
    cyb_df.set_index('date', inplace=True)
    return cyb_df

def zscore(series):
    return (series - series.mean()) / (series.std() + 1e-9)

def calculate_sentiment(df):
    # 计算技术指标
    df['k'], df['d'] = talib.STOCH(df['high'], df['low'], df['close'], 9, 3, 3)
    df['j'] = 3 * df['k'] - 2 * df['d']

    df['boll_upper'], df['boll_mid'], df['boll_lower'] = talib.BBANDS(df['close'], 20, 2, 2)

    df['vol_ma10'] = talib.MA(df['volume'], timeperiod=10)
    df['vol_ratio'] = df['volume'] / (df['vol_ma10'] + 1e-9)

    df['ma5'] = talib.MA(df['close'], 5)
    df['ma10'] = talib.MA(df['close'], 10)

    df['rsi'] = talib.RSI(df['close'], timeperiod=14)

    df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(df['close'], 12, 26, 9)

    # ======== 评分系统（低灵敏度） ========

    df['j_diff'] = df['j'].diff()
    df['kdj_score'] = 0.5 + 0.5 * np.tanh(df['j_diff'] * 1.2)

    df['macd_diff'] = df['macd_hist'].diff()
    df['macd_score'] = 0.5 + 0.5 * np.tanh(df['macd_diff'] * 1.5)

    df['rsi_diff'] = df['rsi'].diff()
    df['rsi_score'] = 0.5 + 0.5 * np.tanh(df['rsi_diff'] * 1.2)

    df['vol_score'] = np.clip(zscore(df['vol_ratio']) / 6 + 0.5, 0, 1)

    df['boll_score'] = np.select(
        [df['close'] > df['boll_upper'], df['close'] < df['boll_lower']],
        [1.0, 0.0],
        default=0.5
    )

    df['ma_score'] = np.where(
        (df['close'] > df['ma5']) & (df['close'] > df['ma10']),
        1.0,
        np.where((df['close'] < df['ma5']) & (df['close'] < df['ma10']), 0.0, 0.5)
    )

    # 可选波动修正，改为非常轻微
    df['volatility'] = (df['high'] - df['low']) / (df['close'] + 1e-9)
    volatility_boost = (1 + df['volatility'] * 0.3)

    # 贪婪指数
    df['greed'] = (
        df['kdj_score'] * 0.25 +
        df['macd_score'] * 0.2 +
        df['vol_score'] * 0.2 +
        df['rsi_score'] * 0.15 +
        df['boll_score'] * 0.1 +
        df['ma_score'] * 0.1
    ) * volatility_boost * 100

    # 恐惧指数（反向）
    df['fear'] = (
        (1 - df['kdj_score']) * 0.25 +
        (1 - df['macd_score']) * 0.2 +
        (1 - df['vol_score']) * 0.2 +
        (1 - df['rsi_score']) * 0.15 +
        (1 - df['boll_score']) * 0.1 +
        (1 - df['ma_score']) * 0.1
    ) * volatility_boost * 100

    # 平滑处理（可调）
    df['greed'] = df['greed'].ewm(span=3).mean()
    df['fear'] = df['fear'].ewm(span=3).mean()

    # 限制在0~100
    df['greed'] = df['greed'].clip(0, 100)
    df['fear'] = df['fear'].clip(0, 100)

    # 清理临时列
    cols_to_drop = [col for col in df.columns if 'score' in col or col.endswith('_diff') or col == 'volatility']
    return df.drop(columns=cols_to_drop).dropna()

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

