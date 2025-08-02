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
    """基于技术指标计算贪婪与恐惧指数"""
    # 1. 计算所需技术指标
    # KDJ指标
    df['k'], df['d'] = talib.STOCH(df['high'], df['low'], df['close'], 
                                  fastk_period=9, slowk_period=3, slowd_period=3)
    df['j'] = 3 * df['k'] - 2 * df['d']
    
    # BOLL指标
    df['boll_mid'] = talib.MA(df['close'], timeperiod=20)
    df['boll_upper'], df['boll_mid'], df['boll_lower'] = talib.BBANDS(
        df['close'], timeperiod=20, nbdevup=2, nbdevdn=2)
    
    # 成交量指标
    df['vol_ma5'] = talib.MA(df['volume'], timeperiod=5)
    df['vol_ma10'] = talib.MA(df['volume'], timeperiod=10)
    df['vol_ratio'] = df['volume'] / df['vol_ma10']
    
    # 均线系统
    df['ma5'] = talib.MA(df['close'], timeperiod=5)
    df['ma10'] = talib.MA(df['close'], timeperiod=10)
    df['ma_cross'] = np.where(df['ma5'] > df['ma10'], 1, -1)
    
    # RSI指标
    df['rsi'] = talib.RSI(df['close'], timeperiod=14)
    
    # MACD指标
    df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
        df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
    
    # 2. 计算各指标分数
    # KDJ评分 (25%)
    df['kdj_score'] = np.select(
        [df['j'] < 20, df['j'] > 80, (df['j'] >= 20) & (df['j'] <= 80)],
        [1, 0, 0.5], default=0.5
    )
    
    # BOLL评分 (20%)
    df['boll_score'] = np.select(
        [df['close'] > df['boll_upper'], 
         df['close'] < df['boll_lower'],
         (df['close'] >= df['boll_lower']) & (df['close'] <= df['boll_upper'])],
        [1, 0, 0.5], default=0.5
    )
    
    # 成交量评分 (20%)
    df['vol_score'] = np.tanh(df['vol_ratio'] - 1) * 0.5 + 0.5
    
    # 均线系统评分 (15%)
    df['ma_score'] = np.where(
        (df['close'] > df['ma5']) & (df['close'] > df['ma10']), 
        1, 
        np.where((df['close'] < df['ma5']) & (df['close'] < df['ma10']), 0, 0.5)
    )
    
    # RSI评分 (10%)
    df['rsi_score'] = np.interp(df['rsi'], [30, 70], [0, 1]).clip(0, 1)
    
    # MACD评分 (10%)
    df['macd_score'] = np.where(
        df['macd_hist'] > 0, 
        np.interp(df['macd_hist'], [0, df['macd_hist'].quantile(0.9)], [0.5, 1]),
        np.interp(df['macd_hist'], [df['macd_hist'].quantile(0.1), 0], [0, 0.5])
    )
    
    # 3. 计算加权贪婪指数
    weights = {
        'kdj_score': 0.25,
        'boll_score': 0.20,
        'vol_score': 0.20,
        'ma_score': 0.15,
        'rsi_score': 0.10,
        'macd_score': 0.10
    }
    
    df['greed'] = sum(df[score] * weight for score, weight in weights.items()) * 100
    
    # 4. 计算恐惧指数（使用相同的指标但反向评分）
    fear_weights = weights.copy()
    # 对部分指标进行反向处理
    df['fear_kdj'] = 1 - df['kdj_score']
    df['fear_boll'] = 1 - df['boll_score']
    df['fear_vol'] = 1 - df['vol_score']
    df['fear_ma'] = 1 - df['ma_score']
    # RSI和MACD保持原权重方向
    
    df['fear'] = (
        df['fear_kdj'] * fear_weights['kdj_score'] +
        df['fear_boll'] * fear_weights['boll_score'] +
        df['fear_vol'] * fear_weights['vol_score'] +
        df['fear_ma'] * fear_weights['ma_score'] +
        df['rsi_score'] * fear_weights['rsi_score'] +
        df['macd_score'] * fear_weights['macd_score']
    ) * 100
    
    # 5. 平滑处理
    df['greed'] = df['greed'].ewm(span=5).mean()
    df['fear'] = df['fear'].ewm(span=5).mean()
    
    # 限制范围
    df['greed'] = df['greed'].clip(0, 100)
    df['fear'] = df['fear'].clip(0, 100)
    
    # 清理临时列
    cols_to_drop = [col for col in df.columns if 'score' in col or 'fear_' in col]
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

