import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import collections # 分析関数で使用

# --- ここから分析ロジック関数 ---
def calculate_sma_for_analysis(data_series, window):
    """分析用のSMA計算（Pandas Seriesを入力とする）"""
    if len(data_series) < window:
        return pd.Series([None] * len(data_series)) # データ不足の場合はNoneのSeriesを返す
    return data_series.rolling(window=window).mean()

def get_slope_direction(sma_values_series):
    """SMAの傾きを取得（Pandas Seriesを入力とする）"""
    sma_values = sma_values_series.dropna().tolist() # NaNを除外してリスト化
    if len(sma_values) < 2:
        return "→"
    if sma_values[-1] > sma_values[-2]:
        return "↑"
    elif sma_values[-1] < sma_values[-2]:
        return "↓"
    else:
        return "→"

def check_trend_and_cross(ohlc_df, short_window=5, long_window=25):
    """
    Pandas DataFrameを受け取り、トレンドとクロスを分析する関数。
    ohlc_dfのindexはDatetimeIndex、'Close'カラムが必要。
    """
    if not isinstance(ohlc_df, pd.DataFrame) or 'Close' not in ohlc_df.columns:
        return {"error": "入力データがDataFrame形式でないか、Close価格が含まれていません。",
                "trend": "データ形式エラー", "signal": "N/A",
                "latest_short_sma": "N/A", "short_sma_slope": "",
                "latest_long_sma": "N/A", "long_sma_slope": ""}

    if len(ohlc_df) < long_window: # 最長の移動平均期間よりデータが少ない場合は分析不可
        return {"error": "データが不足しています。", "trend": "データ不足", "signal": "N/A",
                "latest_short_sma": "N/A", "short_sma_slope": "",
                "latest_long_sma": "N/A", "long_sma_slope": "",
                "latest_data_date": ohlc_df.index[-1].strftime('%Y/%m/%d') if not ohlc_df.empty else "N/A"}

    close_prices = ohlc_df['Close']
    short_sma_series = calculate_sma_for_analysis(close_prices, short_window)
    long_sma_series = calculate_sma_for_analysis(close_prices, long_window)

    # 最新のSMA値を取得 (NaNでない最後の値)
    latest_short_sma = short_sma_series.dropna().iloc[-1] if not short_sma_series.dropna().empty else None
    previous_short_sma = short_sma_series.dropna().iloc[-2] if len(short_sma_series.dropna()) >= 2 else None
    latest_long_sma = long_sma_series.dropna().iloc[-1] if not long_sma_series.dropna().empty else None
    previous_long_sma = long_sma_series.dropna().iloc[-2] if len(long_sma_series.dropna()) >= 2 else None

    if latest_short_sma is None or latest_long_sma is None:
        return {"error": "SMA計算に必要なデータが不足しています。", "trend": "SMA計算データ不足", "signal": "N/A",
                "latest_short_sma": "N/A", "short_sma_slope": "",
                "latest_long_sma": "N/A", "long_sma_slope": "",
                "latest_data_date": ohlc_df.index[-1].strftime('%Y/%m/%d')}

    short_sma_slope = get_slope_direction(short_sma_series)
    long_sma_slope = get_slope_direction(long_sma_series)

    trend = "レンジ相場"
    if latest_short_sma > latest_long_sma:
        if short_sma_slope == "↑":
            trend = "上昇トレンドの可能性あり 📈"
        elif long_sma_slope == "↑": # 短期が横ばいでも長期が上なら緩やかな上昇と判断
            trend = "緩やかな上昇傾向の可能性あり"
        else: # 短期が下向きだが長期より上にある場合など
            trend = "短期的に調整局面か、方向性注意"
    elif latest_short_sma < latest_long_sma:
        if short_sma_slope == "↓":
            trend = "下降トレンドの可能性あり 📉"
        elif long_sma_slope == "↓": # 短期が横ばいでも長期が下なら緩やかな下降と判断
            trend = "緩やかな下降傾向の可能性あり"
        else: # 短期が上向きだが長期より下にある場合など
            trend = "短期的に反発局面か、方向性注意"


    signal = "シグナルなし"
    cross_date = ohlc_df.index[-1].strftime('%Y/%m/%d') # 最新の日付

    # クロス判定 (previous_short_sma と previous_long_sma が None でないことを確認)
    if previous_short_sma is not None and previous_long_sma is not None:
        if previous_short_sma <= previous_long_sma and latest_short_sma > latest_long_sma:
            signal = f"【注目！】ゴールデンクロス発生の可能性あり！ ({cross_date})"
        elif previous_short_sma >= previous_long_sma and latest_short_sma < latest_long_sma:
            signal = f"【注意】デッドクロス発生の可能性あり！ ({cross_date})"

    return {
        "latest_short_sma": round(latest_short_sma, 2),
        "short_sma_slope": short_sma_slope,
        "latest_long_sma": round(latest_long_sma, 2),
        "long_sma_slope": long_sma_slope,
        "trend": trend,
        "signal": signal,
        "latest_data_date": cross_date
    }
# --- 分析ロジック関数ここまで ---


# Streamlitアプリのタイトル設定
st.title('株価・仮想通貨データ可視化＆分析アプリ') # タイトル変更

# サイドバーに銘柄入力欄を設置
st.sidebar.header('入力')
ticker_symbol = st.sidebar.text_input('銘柄シンボルを入力 (例: AAPL, BTC-USD)', 'AAPL')

# サイドバーに期間選択のオプションを設置
end_date = datetime.today()
start_date_default = end_date - timedelta(days=365)

start_date = st.sidebar.date_input('開始日', start_date_default)
end_date_selected = st.sidebar.date_input('終了日', end_date)

# 移動平均線の期間設定
st.sidebar.header('移動平均線')
short_window = st.sidebar.slider('短期移動平均 (日数)', 1, 50, 5)
long_window = st.sidebar.slider('長期移動平均 (日数)', 1, 200, 25)


# 「株価・仮想通貨データを取得・表示」ボタン
if st.sidebar.button('データを取得・分析・表示'): # ボタンのテキスト変更
    if ticker_symbol:
        with st.spinner(f'{ticker_symbol}のデータを取得・分析中...'): # ローディングスピナー
            try:
                ticker_data = yf.Ticker(ticker_symbol)
                # yfinanceではend_dateの日は含まれないため、翌日を指定する
                history = ticker_data.history(start=start_date, end=end_date_selected + timedelta(days=1))

                if history.empty:
                    st.error(f'{ticker_symbol}のデータが見つかりませんでした。銘柄シンボルや期間を確認してください。')
                else:
                    st.success(f'{ticker_symbol}のデータを取得しました。')

                    # 移動平均線の計算 (グラフ表示用)
                    history[f'SMA_{short_window}'] = history['Close'].rolling(window=short_window).mean()
                    history[f'SMA_{long_window}'] = history['Close'].rolling(window=long_window).mean()

                    # --- ここからテクニカル分析の実行と表示 ---
                    st.subheader(f"{ticker_symbol} のテクニカル分析結果")

                    # 分析関数に渡すために、history DataFrame をそのまま使用
                    # (check_trend_and_cross 関数内で必要な処理を行うように変更)
                    analysis_result = check_trend_and_cross(history, short_window, long_window)

                    if "error" in analysis_result:
                        st.warning(f"分析エラー: {analysis_result['error']}")
                    else:
                        st.markdown(f"**📊 トレンド状況 ({analysis_result['latest_data_date']})**")
                        st.info(f"{analysis_result['trend']}")

                        st.markdown(f"**🔔 シグナル**")
                        if analysis_result['signal'] == "シグナルなし":
                            st.info(analysis_result['signal'])
                        elif "ゴールデンクロス" in analysis_result['signal']:
                            st.success(analysis_result['signal'])
                        elif "デッドクロス" in analysis_result['signal']:
                            st.warning(analysis_result['signal'])
                        else:
                            st.info(analysis_result['signal'])


                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                label=f"短期SMA ({short_window}日)",
                                value=f"{analysis_result['latest_short_sma']}",
                                delta=f"傾き: {analysis_result['short_sma_slope']}" if analysis_result['short_sma_slope'] else None
                            )
                        with col2:
                            st.metric(
                                label=f"長期SMA ({long_window}日)",
                                value=f"{analysis_result['latest_long_sma']}",
                                delta=f"傾き: {analysis_result['long_sma_slope']}" if analysis_result['long_sma_slope'] else None
                            )
                        st.markdown("---") # 区切り線
                    # --- テクニカル分析の表示ここまで ---


                    # グラフの作成
                    st.subheader(f"{ticker_symbol} 株価・仮想通貨チャート") # チャートの前にサブヘッダー追加
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(x=history.index,
                                               open=history['Open'],
                                               high=history['High'],
                                               low=history['Low'],
                                               close=history['Close'],
                                               name='ローソク足'))
                    fig.add_trace(go.Scatter(x=history.index,
                                             y=history[f'SMA_{short_window}'],
                                             mode='lines',
                                             name=f'{short_window}日移動平均',
                                             line=dict(color='orange')))
                    fig.add_trace(go.Scatter(x=history.index,
                                             y=history[f'SMA_{long_window}'],
                                             mode='lines',
                                             name=f'{long_window}日移動平均',
                                             line=dict(color='purple')))
                    fig.update_layout(
                        title=f'{ticker_symbol} チャート (分析期間: {start_date.strftime("%Y-%m-%d")} - {end_date_selected.strftime("%Y-%m-%d")})',
                        xaxis_title='日付',
                        yaxis_title='価格',
                        xaxis_rangeslider_visible=False
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    if st.checkbox('取得データを表示する'):
                        st.subheader('取得データ')
                        st.write(history)

            except Exception as e:
                st.error(f'エラーが発生しました: {e}')
                st.error("詳細なエラーメッセージを確認し、必要であればコードを修正してください。") # エラー詳細の確認を促す
    else:
        st.warning('銘柄シンボルを入力してください。')

else:
    st.info('サイドバーで銘柄シンボルと期間を選択し、「データを取得・分析・表示」ボタンを押してください。')

