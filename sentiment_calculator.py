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

def calculate_sentiment(df):
    # 技术指标计算
    df['k'], df['d'] = talib.STOCH(df['high'], df['low'], df['close'], 9, 3, 3)
    df['j'] = 3 * df['k'] - 2 * df['d']

    df['boll_upper'], df['boll_mid'], df['boll_lower'] = talib.BBANDS(df['close'], 20, 2, 2)

    df['vol_ma10'] = talib.MA(df['volume'], timeperiod=10)
    df['vol_ratio'] = df['volume'] / df['vol_ma10']

    df['ma5'] = talib.MA(df['close'], 5)
    df['ma10'] = talib.MA(df['close'], 10)

    df['rsi'] = talib.RSI(df['close'], timeperiod=14)

    df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(df['close'], 12, 26, 9)

    # KDJ评分 - 更敏感
    df['kdj_score'] = np.clip((80 - abs(df['j'] - 50)) / 60, 0, 1)

    # BOLL评分
    df['boll_score'] = np.select(
        [df['close'] > df['boll_upper'], df['close'] < df['boll_lower']],
        [1.0, 0.0],
        default=0.5
    )

    # 成交量评分 - 更敏感
    df['vol_score'] = np.tanh((df['vol_ratio'] - 1) * 2) * 0.5 + 0.5

    # 均线评分
    df['ma_score'] = np.where(
        (df['close'] > df['ma5']) & (df['close'] > df['ma10']),
        1.0,
        np.where((df['close'] < df['ma5']) & (df['close'] < df['ma10']), 0.0, 0.5)
    )

    # RSI评分
    df['rsi_score'] = np.interp(df['rsi'], [30, 70], [0, 1]).clip(0, 1)

    # MACD评分 - 更敏感
    macd_strength = df['macd_hist'].abs()
    macd_norm = (macd_strength - macd_strength.min()) / (macd_strength.max() - macd_strength.min())
    df['macd_score'] = np.where(df['macd_hist'] > 0, 0.5 + 0.5 * macd_norm, 0.5 - 0.5 * macd_norm)

    # 权重设置
    weights = {
        'kdj_score': 0.25,
        'boll_score': 0.20,
        'vol_score': 0.20,
        'ma_score': 0.15,
        'rsi_score': 0.10,
        'macd_score': 0.10
    }

    # 贪婪指数
    df['greed'] = sum(df[score] * weight for score, weight in weights.items()) * 100

    # 恐惧指数（反向评分）
    df['fear'] = (
        (1 - df['kdj_score']) * weights['kdj_score'] +
        (1 - df['boll_score']) * weights['boll_score'] +
        (1 - df['vol_score']) * weights['vol_score'] +
        (1 - df['ma_score']) * weights['ma_score'] +
        df['rsi_score'] * weights['rsi_score'] +
        df['macd_score'] * weights['macd_score']
    ) * 100

    # 可选轻微平滑
    df['greed'] = df['greed'].ewm(span=2).mean()
    df['fear'] = df['fear'].ewm(span=2).mean()
    #增加平均值
    df['greed'] = df['greed'] + 7
    df['fear'] = df['fear'] + 12
    # 限制范围
    df['greed'] = df['greed'].clip(0, 100)
    df['fear'] = df['fear'].clip(0, 100)

    # 清理
    cols_to_drop = [col for col in df.columns if 'score' in col or col.startswith('fear_')]
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

