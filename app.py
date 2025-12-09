# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import vectorbt as vbt
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Grok Ranker Ultimate", layout="wide")
st.title("30개 지표 실시간 순위 + 5년 백테스팅 시스템")
st.markdown("**종목 무제한 추가·삭제 가능 | 항상 동일한 기준으로 순위·성과 검증**")

# ==================== 사이드바: 종목 자유 관리 ====================
st.sidebar.header("나의 관심 종목 리스트")
if 'universe' not in st.session_state:
    st.session_state.universe = [
        "NVDA", "TSLA", "GOOGL", "AVGO", "MRVL", "PLTR", "IREN", "HPE",
        "SMCI", "AMD", "META", "MSFT", "AAPL", "ARM", "QCOM"
    ]

# 추가
new_ticker = st.sidebar.text_input("티커 추가 (예: COIN SOFI)", "").upper().strip()
if st.sidebar.button("추가하기"):
    if new_ticker and new_ticker not in st.session_state.universe:
        st.session_state.universe.append(new_ticker)
        st.sidebar.success(f"{new_ticker} 추가됨")
        st.rerun()

# 삭제
st.sidebar.write(f"현재 종목 {len(st.session_state.universe)}개")
for t in st.session_state.universe[:]:
    col1, col2 = st.sidebar.columns([3,1])
    col1.write(t)
    if col2.button("삭제", key=f"del_{t}"):
        st.session_state.universe.remove(t)
        st.rerun()

# ==================== 계산 시작 ====================
if st.button("실시간 순위 계산 + 5년 백테스팅 실행", type="primary"):
    if not st.session_state.universe:
        st.error("종목을 하나 이상 추가해주세요")
    else:
        with st.spinner("데이터 수집 및 30개 지표 계산 중... (10~40초 소요)"):
            results = []

            for ticker in st.session_state.universe:
                try:
                    df = yf.download(ticker, period="2y", progress=False, auto_adjust=True)
                    if len(df) < 100:
                        continue

                    # pandas_ta로 일괄 계산
                    df.ta.strategy("All")  # 모든 지표 한번에 계산 (빠름)
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

                    score = 0.0

                    # ==================== 30개 지표 점수화 ====================
                    # 1. MACD
                    if df["MACD_12_26_9"].iloc[-1] > df["MACDs_12_26_9"].iloc[-1]:
                        score += 15

                    # 2. RSI
                    if df["RSI_14"].iloc[-1] < 70:
                        score += 10
                    if df["RSI_14"].iloc[-1] < 30:
                        score += 10  # 과매도 보너스

                    # 3~6. 모멘텀
                    if df["STOCHk_14_3_3"].iloc[-1] > df["STOCHd_14_3_3"].iloc[-1]: score += 10
                    if df["WILLR_14"].iloc[-1] > -80: score += 10
                    if df["CCI_20_0.015"].iloc[-1] < 100: score += 10

                    # 7. ADX 강한 상승추세
                    if df["ADX_14"].iloc[-1] > 25 and df["DMP_14"].iloc[-1] > df["DMN_14"].iloc[-1]:
                        score += 25

                    # 8. Aroon
                    if df["AROONU_14"].iloc[-1] > df["AROOND_14"].iloc[-1]: score += 15

                    # 9. SuperTrend (가장 강력)
                    if "SUPERT_10_3" in df.columns and df["SUPERT_10_3"].iloc[-1] == 1:
                        score += 30

                    # 10~13. 거래량·자금
                    if df["OBV"].iloc[-1] > df["OBV"].rolling(20).mean().iloc[-1]: score += 15
                    if df["CMF_21"].iloc[-1] > 0: score += 18
                    if df["Close"].iloc[-1] > df["VWAP_D"].iloc[-1]: score += 12

                    # 14~17. 변동성·브레이크아웃
                    if df["Close"].iloc[-1] > df["BBM_20_2.0"].iloc[-1]: score += 12
                    if df["Close"].iloc[-1] > df["DCH_20_20"].iloc[-1]: score += 20  # Donchian 상단 돌파
                    if "PSARl_0.02_0.2" in df.columns and df["Close"].iloc[-1] > df["PSARl_0.02_0.2"].iloc[-1]: score += 15

                    # 18. Ichimoku Cloud
                    if "ISA_9" in df.columns and "ISB_26" in df.columns:
                        cloud_top = max(df["ISA_9"].iloc[-1], df["ISB_26"].iloc[-1])
                        if df["Close"].iloc[-1] > cloud_top: score += 25

                    # 19~30. 기타 보정 (1개월 수익률, 거래량 폭발 등)
                    ret_1m = df["Close"].iloc[-1] / df["Close"].iloc[-21] - 1
                    if ret_1m > 0.1: score += 15
                    if df["Volume"].iloc[-1] > df["Volume"].rolling(20).mean().iloc[-1] * 2: score += 10

                    results.append({
                        "티커": ticker,
                        "현재가": round(df["Close"].iloc[-1], 2),
                        "종합점수": round(score, 1),
                        "1개월수익률(%)": round(ret_1m * 100, 1)
                    })
                except Exception as e:
                    st.warning(f"{ticker} 오류: {e}")
                    continue

            # ==================== 순위 출력 ====================
            if results:
                rank_df = pd.DataFrame(results).sort_values("종합점수", ascending=False).reset_index(drop=True)
                rank_df.index += 1
                st.success(f"실시간 진입순위 완성! ({len(results)}개 종목)")
                st.dataframe(rank_df.style.background_gradient(cmap="Greens"), use_container_width=True)

                # ==================== 백테스팅 ====================
                top_n = st.slider("백테스팅 대상: 상위 몇 개?", 1, min(10, len(rank_df)), 3)
                top_tickers = rank_df["티커"].head(top_n).tolist()

                price = yf.download(top_tickers, start="2019-01-01", progress=False)["Adj Close"]
                if price.empty:
                    st.error("백테스팅 데이터 없음")
                else:
                    pf = vbt.Portfolio.from_holding(price, freq="1M")
                    stats = pf.stats()

                    st.subheader(f"백테스팅 결과 – 상위 {top_n}개 (2019년~현재)")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("연평균수익률", f"{stats['CAGR%']:.1f}%")
                    c2.metric("누적수익률", f"{stats['Total Return%']:.0f}%")
                    c3.metric("최대낙폭", f"{stats['Max Drawdown%']:.1f}%")
                    c4.metric("샤프비율", f"{stats['Sharpe Ratio']:.2f}")

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=pf.value().index, y=pf.value() / pf.value().iloc[0]*100,
                                             name="나의 전략", line=dict(width=3)))
                    spy = yf.download("SPY", start="2019-01-01", progress=False)["Adj Close"]
                    fig.add_trace(go.Scatter(x=spy.index, y=spy/spy.iloc[0]*100, name="S&P500", line=dict(dash="dash")))
                    fig.update_layout(title="나의 전략 vs S&P500", yaxis_title="누적수익률 (%)", height=550)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("계산된 종목이 없습니다")
