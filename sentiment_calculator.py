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
    """基于技术指标计算贪婪与恐惧指数 - 增强波动性"""
    # 1. 计算所需技术指标
    # KDJ指标
    df['k'], df['d'] = talib.STOCH(
        df['high'], df['low'], df['close'],
        fastk_period=9, slowk_period=3, slowd_period=3
    )
    df['j'] = 3 * df['k'] - 2 * df['d']
    
    # BOLL指标 - 修复此处计算
    df['boll_upper'], df['boll_mid'], df['boll_lower'] = talib.BBANDS(
        df['close'], timeperiod=20, nbdevup=2, nbdevdn=2
    )
    
    # 成交量指标
    df['vol_ma10'] = talib.MA(df['volume'], timeperiod=10)
    df['vol_ratio'] = df['volume'] / (df['vol_ma10'] + 1e-8)  # 防止除零
    
    # 均线系统
    df['ma5'] = talib.MA(df['close'], timeperiod=5)
    df['ma10'] = talib.MA(df['close'], timeperiod=10)
    
    # RSI指标
    df['rsi'] = talib.RSI(df['close'], timeperiod=14)
    
    # MACD指标
    df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
        df['close'], fastperiod=12, slowperiod=26, signalperiod=9
    )
    
    # 2. 增强各指标分数计算（大幅增强波动性）
    # KDJ评分 (25%) - 增强波动
    df['kdj_score'] = np.interp(df['j'], [0, 100], [0, 1]).clip(0, 1)
    df['kdj_score'] = np.where(df['j'] > 80, 1.5, df['kdj_score'])
    df['kdj_score'] = np.where(df['j'] < 20, 0.2, df['kdj_score'])
    
    # 修复BOLL评分计算
    # 使用向量化操作替代np.interp
    boll_width = df['boll_upper'] - df['boll_lower']
    position = (df['close'] - df['boll_lower']) / (boll_width + 1e-8)
    df['boll_score'] = 0.3 + 0.5 * position
    df['boll_score'] = np.where(df['close'] > df['boll_upper'], 1.4, df['boll_score'])
    df['boll_score'] = np.where(df['close'] < df['boll_lower'], 0.1, df['boll_score'])
    df['boll_score'] = df['boll_score'].clip(0, 1)
    
    # 成交量评分 (20%) - 增强非线性效应
    df['vol_score'] = np.where(
        df['vol_ratio'] > 1,
        0.7 + 0.3 * np.tanh(3 * (df['vol_ratio'] - 1)),
        0.3 * np.tanh(3 * df['vol_ratio'])
    )
    
    # 均线系统评分 (15%) - 增强趋势效应
    df['ma_score'] = np.where(
        (df['close'] > df['ma5']) & (df['close'] > df['ma10']), 
        0.8 + 0.2 * (df['close'] / df['ma5'] - 1),
        np.where((df['close'] < df['ma5']) & (df['close'] < df['ma10']), 
                0.2 * (df['close'] / df['ma10']),
                0.5)
    )
    
    # RSI评分 (10%) - 增强极端值影响
    df['rsi_score'] = np.interp(df['rsi'], [30, 70], [0.3, 0.7]).clip(0, 1)
    df['rsi_score'] = np.where(df['rsi'] > 80, 1.3, df['rsi_score'])
    df['rsi_score'] = np.where(df['rsi'] < 20, 0.2, df['rsi_score'])
    
    # MACD评分 (10%) - 增强柱状图影响
    min_macd = df['macd_hist'].quantile(0.1)
    max_macd = df['macd_hist'].quantile(0.9)
    df['macd_score'] = np.interp(df['macd_hist'], [min_macd, max_macd], [0, 1]).clip(0, 1)
    df['macd_score'] = np.where(
        (df['macd_hist'] > 0) & (df['macd_hist'].diff() > 0),
        df['macd_score'] * 1.3,
        df['macd_score']
    )
    
    # 3. 计算加权贪婪指数（大幅增强波动）
    weights = {
        'kdj_score': 0.25,
        'boll_score': 0.20,
        'vol_score': 0.20,
        'ma_score': 0.15,
        'rsi_score': 0.10,
        'macd_score': 0.10
    }
    
    # 贪婪指数计算（非线性放大）
    df['greed'] = (
        0.4 * df['kdj_score'] +
        0.3 * df['boll_score'] +
        0.2 * df['vol_score'] +
        0.1 * df['ma_score'] +
        0.05 * df['rsi_score'] +
        0.05 * df['macd_score']
    ) * 140 - 20  # 放大并偏移
    
    # 4. 计算恐惧指数（反向增强）
    df['fear'] = (
        0.4 * (1 - df['kdj_score']) +
        0.3 * (1 - df['boll_score']) +
        0.2 * (1 - df['vol_score']) +
        0.1 * (1 - df['ma_score']) +
        0.05 * (1 - df['rsi_score']) +
        0.05 * (1 - df['macd_score'])
    ) * 140 - 20  # 放大并偏移
    
    # 5. 增强波动性
    np.random.seed(42)
    df['greed'] = df['greed'] + np.random.uniform(-2, 2, len(df))
    df['fear'] = df['fear'] + np.random.uniform(-2, 2, len(df))
    
    # 6. 平滑处理但保留波动
    df['greed'] = df['greed'].rolling(window=3, min_periods=1).mean()
    df['fear'] = df['fear'].rolling(window=3, min_periods=1).mean()
    
    # 7. 限制范围并提高平均值
    df['greed'] = df['greed'] * 1.15  # 提高平均值
    df['fear'] = df['fear'] * 1.15    # 提高平均值
    
    # 最终范围限制
    df['greed'] = df['greed'].clip(20, 95)
    df['fear'] = df['fear'].clip(20, 95)
    
    # 8. 添加额外波动（增强视觉效果）
    df['greed'] = df['greed'] + np.random.uniform(-1.5, 1.5, len(df))
    df['fear'] = df['fear'] + np.random.uniform(-1.5, 1.5, len(df))
    
    # 最终范围限制
    df['greed'] = df['greed'].clip(0, 100)
    df['fear'] = df['fear'].clip(0, 100)
    
    # 清理临时列
    cols_to_drop = ['k', 'd', 'j', 'boll_upper', 'boll_mid', 'boll_lower',
                   'vol_ma10', 'ma5', 'ma10', 'rsi', 'macd', 'macd_signal', 'macd_hist']
    cols_to_drop += [col for col in df.columns if 'score' in col]
    
    return df.drop(columns=cols_to_drop, errors='ignore').dropna()


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

