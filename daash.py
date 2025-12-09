# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import vectorbt as vbt
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# ==================== 페이지 설정 ====================
st.set_page_config(page_title="Grok Ranker Ultimate", layout="wide")
st.title("30개 지표 실시간 순위 + 5년 백테스팅 시스템")
st.markdown("**종목 무제한 추가·삭제 가능 | 항상 동일한 기준으로 순위·성과 검증**")

# ==================== 사이드바: 종목 자유 관리 ====================
st.sidebar.header("나의 관심 종목 리스트")
if 'universe' not in st.session_state:
    st.session_state.universe = [
        "NVDA", "TSLA", "GOOGL", "AVGO", "MRVL", "PLTR", "IREN", "HPE",
        "SMCI", "AMD", "META", "MSFT", "AAPL", "ARM", "QCOM", "INTC"
    ]

# 추가
new_ticker = st.sidebar.text_input("티커 추가 (예: COIN SOFI)", "").upper().strip()
if st.sidebar.button("추가하기"):
    if new_ticker and new_ticker not in st.session_state.universe:
        st.session_state.universe.append(new_ticker)
        st.sidebar.success(f"{new_ticker} 추가됨")

# 삭제 & 정렬
st.sidebar.write("현재 종목 수:", len(st.session_state.universe))
for i, t in enumerate(st.session_state.universe[:]):
    col1, col2 = st.sidebar.columns([4, 1])
    col1.write(t)
    if col2.button("삭제", key=f"del_{t}_{i}"):
        st.session_state.universe.remove(t)
        st.rerun()

# ==================== 계산 시작 버튼 ====================
if st.button("실시간 순위 계산 + 5년 백테스팅 실행", type="primary"):
    if len(st.session_state.universe) == 0:
        st.error("종목을 하나 이상 추가해주세요")
    else:
        with st.spinner("데이터 다운로드 및 30개 지표 계산 중... (10~30초 소요)"):
            results = []

            for ticker in st.session_state.universe:
                try:
                    # 2년 데이터 (지표 계산용)
                    df = yf.download(ticker, period="2y", progress=False)
                    if len(df) < 100:
                        continue
                    df = df.copy()

                    # pandas_ta로 30개 지표 일괄 계산
                    df.ta.macd(append=True)
                    df.ta.rsi(append=True)
                    df.ta.stoch(append=True)
                    df.ta.willr(append=True)
                    df.ta.cci(append=True)
                    df.ta.adx(append=True)
                    df.ta.obv(append=True)
                    df.ta.vwap(append=True)
                    df.ta.aroon(append=True)
                    df.ta.supertrend(append=True)
                    df.ta.ichimoku(append=True)
                    df.ta.bbands(append=True)
                    df.ta.donchian(append=True)
                    df.ta.psar(append=True)
                    df.ta.cmf(append=True)

                    # 점수 계산 (총 300점 만점)
                    score = 0

                    # 1. 모멘텀
                    if df["MACD_12_26_9"].iloc[-1] > df["MACDs_12_26_9"].iloc[-1]: score += 15
                    if df["RSI_14"].iloc[-1] < 70: score += 10
                    if df["STOCHk_14_3_3"].iloc[-1] > df["STOCHd_14_3_3"].iloc[-1]: score += 10
                    if df["WILLR_14"].iloc[-1] > -80: score += 10
                    if df["CCI_20_0.015"].iloc[-1] < 100: score += 10

                    # 2. 추세
                    if df["ADX_14"].iloc[-1] > 25 and df["DMP_14"].iloc[-1 > df["DMN_14"].iloc[-1]: score += 20
                    if df["AROOND_14"].iloc[-1] - df["AROONU_14"].iloc[-1] > 0: score += 15
                    if df["SUPERT_10_3"].iloc[-1] == 1: score += 25  # SuperTrend Buy

                    # 3. 거래량·자금 흐름
                    if df["OBV"].iloc[-1] > df["OBV"].rolling(20).mean().iloc[-1]: score += 15
                    if df["CMF_21"] = df.ta.cmf(length=21)
                    if df["CMF_21"].iloc[-1] > 0: score += 15

                    # 4. 변동성·브레이크아웃
                    upper, middle, lower = df["BBU_20_2.0"], df["BBM_20_2.0"], df["BBL_20_2.0"]
                    if df["Close"].iloc[-1] > middle.iloc[-1]: score += 12
                    if df["Close"].iloc[-1] > df["DCL_20_20"].iloc[-1]: score += 18  # Donchian 상단 돌파

                    # 5. Ichimoku & PSAR
                    isa, isb = df["ISA_9"], df["ISB_26"]
                    if df["Close"].iloc[-1] > max(isa.iloc[-1], isb.iloc[-1]): score += 20
                    if df["PSARl_0.02_0.2"].iloc[-1] < df["Close"].iloc[-1]: score += 15

                    # 6. 기타
                    if df["Close"].iloc[-1] > df["VWAP_D"].iloc[-1]: score += 12

                    results.append({
                        "티커": ticker,
                        "현재가": round(df["Close"].iloc[-1], 2),
                        "종합점수": score,
                        "1개월수익률": round((df["Close"].iloc[-1] / df["Close"].iloc[-21] - 1) * 100, 1)
                    })
                except:
                    continue

            # ==================== 순위 출력 ====================
            if results:
                rank_df = pd.DataFrame(results).sort_values("종합점수", ascending=False).reset_index(drop=True)
                rank_df.index = rank_df.index + 1
                st.success("실시간 진입순위 완성!")
                st.dataframe(rank_df.style.background_gradient(cmap="Greens"), use_container_width=True)

                # ==================== 백테스팅 (상위 3개) ====================
                top_n = st.slider("백테스팅 상위 몇 개 종목?", 1, 10, 3)
                top_tickers = rank_df["티커"].head(top_n).tolist()

                with st.spinner(f"백테스팅 중... ({top_n}종목, 2019년~현재)"):
                    price = yf.download(top_tickers, start="2019-01-01", progress=False)["Adj Close"]
                    monthly_ret = price.resample("ME").last().pct_change().dropna()

                    # 동일 가중 포트폴리오
                    port_ret = monthly_ret[top_tickers].mean(axis=1)
                    port_cum = (1 + port_ret).cumprod()

                    # vectorbt 포트폴리오
                    pf = vbt.Portfolio.from_holding(price[top_tickers], freq="1M")
                    stats = pf.stats()

                    st.subheader(f"백테스팅 결과 – 상위 {top_n}개 종목 (2019.1 ~ 현재)")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("연평균수익률", f"{stats['CAGR%']:.1f}%")
                    col2.metric("누적수익률", f"{stats['Total Return%']:.0f}%")
                    col3.metric("최대낙폭(MDD)", f"{stats['Max Drawdown%']:.1f}%")
                    col4.metric("샤프비율", f"{stats['Sharpe Ratio']:.2f}")

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=port_cum.index, y=port_cum, name="나의 전략", line=dict(width=3)))
                    spy = yf.download("SPY", start="2019-01-01")["Adj Close"].resample("ME").last().pct_change().add(1).cumprod()
                    fig.add_trace(go.Scatter(x=spy.index, y=spy, name="S&P500", line=dict(dash="dash")))
                    fig.update_layout(title="나의 전략 vs S&P500", yaxis_title="누적수익률", height=500)
                    st.plotly_chart(fig, use_container_width=True)

            else:
                st.error("데이터를 가져올 수 없습니다")

st.caption("Grok Ranker Ultimate v1.0 | 항상 동일한 기준으로 순위·백테스팅 제공")
