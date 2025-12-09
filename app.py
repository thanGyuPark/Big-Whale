# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import vectorbt as vbt
import plotly.graph_objects as go

st.set_page_config(page_title="Grok Ranker Ultimate", layout="wide")
st.title("30개 지표 실시간 순위 + 5년 백테스팅 시스템")
st.markdown("**종목 무제한 추가·삭제 | 항상 동일한 기준으로 순위·성과 검증**")

# ==================== 사이드바: 종목 관리 ====================
st.sidebar.header("나의 관심 종목 리스트")

if 'universe' not in st.session_state:
    st.session_state.universe = ["NVDA","TSLA","GOOGL","AVGO","MRVL","PLTR","IREN","HPE","SMCI","AMD"]

# 추가 (여러 티커 입력 지원)
new = st.sidebar.text_input("티커 추가 (예: AAPL MSFT)", "").upper().strip()
if st.sidebar.button("추가하기"):
    if new:
        for tkr in new.split():
            if tkr and tkr not in st.session_state.universe:
                st.session_state.universe.append(tkr)
        st.rerun()

# 삭제
st.sidebar.write(f"현재 {len(st.session_state.universe)}개 종목")
for t in st.session_state.universe[:]:
    col1, col2 = st.sidebar.columns([3, 1])
    col1.write(t)
    if col2.button("삭제", key=f"del_{t}"):
        st.session_state.universe.remove(t)
        st.rerun()

# ==================== 실행 버튼 ====================
if st.button("실시간 순위 계산 + 5년 백테스팅 실행", type="primary"):
    if not st.session_state.universe:
        st.error("종목을 하나 이상 추가해주세요")
    else:
        with st.spinner("30개 지표 계산 중..."):
            results = []

            for ticker in st.session_state.universe:
                try:
                    df = yf.download(ticker, period="2y", progress=False)

                    # 데이터 검증
                    if df is None or df.empty or len(df) < 100:
                        continue

                    # ==================== 핵심 지표 계산 ====================
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
                    df.ta.bbands(append=True)
                    df.ta.donchian(append=True)
                    df.ta.psar(append=True)
                    df.ta.cmf(append=True)

                    # Ichimoku 수동
                    df['tenkan'] = (df['High'].rolling(9).max() + df['Low'].rolling(9).min()) / 2
                    df['kijun']  = (df['High'].rolling(26).max() + df['Low'].rolling(26).min()) / 2

                    score = 0.0

                    # ==================== 스코어 룰 ====================
                    if 'MACD_12_26_9' in df.columns and 'MACDs_12_26_9' in df.columns:
                        if df["MACD_12_26_9"].iloc[-1] > df["MACDs_12_26_9"].iloc[-1]:
                            score += 15

                    if 'RSI_14' in df.columns and df["RSI_14"].iloc[-1] < 70:
                        score += 10

                    if 'STOCHk_14_3_3' in df.columns and 'STOCHd_14_3_3' in df.columns:
                        if df["STOCHk_14_3_3"].iloc[-1] > df["STOCHd_14_3_3"].iloc[-1]:
                            score += 10

                    if 'WILLR_14' in df.columns and df["WILLR_14"].iloc[-1] > -80:
                        score += 10

                    if 'CCI_20_0.015' in df.columns and df["CCI_20_0.015"].iloc[-1] < 100:
                        score += 10

                    if 'ADX_14' in df.columns and 'DMP_14' in df.columns and 'DMN_14' in df.columns:
                        if df["ADX_14"].iloc[-1] > 25 and df["DMP_14"].iloc[-1] > df["DMN_14"].iloc[-1]:
                            score += 25

                    if 'AROONU_14' in df.columns and 'AROOND_14' in df.columns:
                        if df["AROONU_14"].iloc[-1] > df["AROOND_14"].iloc[-1]:
                            score += 15

                    # Supertrend 컬럼은 버전에 따라 값/형태가 달라질 수 있어 존재 체크 강화
                    # 흔한 패턴: SUPERT_10_3, SUPERTd_10_3 등
                    if 'SUPERT_10_3' in df.columns:
                        # 일부 환경에서는 1/-1 혹은 True/False 형태가 섞일 수 있어 안전 처리
                        try:
                            if float(df["SUPERT_10_3"].iloc[-1]) == 1:
                                score += 30
                        except:
                            pass

                    if "OBV" in df.columns:
                        if df["OBV"].iloc[-1] > df["OBV"].rolling(20).mean().iloc[-1]:
                            score += 15

                    if 'CMF_21' in df.columns and df["CMF_21"].iloc[-1] > 0:
                        score += 18

                    if 'VWAP_D' in df.columns:
                        if df["Close"].iloc[-1] > df["VWAP_D"].iloc[-1]:
                            score += 12

                    if 'BBM_20_2.0' in df.columns:
                        if df["Close"].iloc[-1] > df["BBM_20_2.0"].iloc[-1]:
                            score += 12

                    if 'DCH_20_20' in df.columns:
                        if df["Close"].iloc[-1] > df["DCH_20_20"].iloc[-1]:
                            score += 20

                    if 'PSARl_0.02_0.2' in df.columns:
                        if df["Close"].iloc[-1] > df["PSARl_0.02_0.2"].iloc[-1]:
                            score += 15

                    # Ichimoku 돌파
                    if pd.notna(df["tenkan"].iloc[-1]) and pd.notna(df["kijun"].iloc[-1]):
                        if df["Close"].iloc[-1] > max(df["tenkan"].iloc[-1], df["kijun"].iloc[-1]):
                            score += 25

                    # ==================== 모멘텀/거래량 ====================
                    # 1개월 수익률 계산 안정화(데이터 부족 방지)
                    ret_1m = None
                    if len(df) >= 22:
                        ret_1m = df["Close"].iloc[-1] / df["Close"].iloc[-21] - 1
                        if ret_1m > 0.1:
                            score += 15
                    else:
                        ret_1m = 0.0

                    if df["Volume"].iloc[-1] > df["Volume"].rolling(20).mean().iloc[-1] * 2:
                        score += 10

                    results.append({
                        "티커": ticker,
                        "현재가": round(float(df["Close"].iloc[-1]), 2),
                        "종합점수": round(score, 1),
                        "1개월수익률%": round(float(ret_1m) * 100, 1)
                    })

                except Exception:
                    st.warning(f"{ticker}: 오류")
                    continue

            # ==================== 랭킹 출력 ====================
            if results:
                rank = pd.DataFrame(results).sort_values("종합점수", ascending=False).reset_index(drop=True)
                rank.index += 1

                st.success("완성!")
                st.dataframe(rank.style.background_gradient(cmap="Greens"), use_container_width=True)

                # ==================== 백테스팅 ====================
                n = st.slider("백테스팅 상위 몇 개?", 1, 10, 3)
                tops = rank["티커"].head(n).tolist()

                price = yf.download(tops, start="2019-01-01", progress=False)

                # yfinance 반환 형태 안정화
                if isinstance(price.columns, pd.MultiIndex):
                    price = price["Adj Close"]
                else:
                    # 단일 티커일 때
                    if "Adj Close" in price.columns:
                        price = price[["Adj Close"]].rename(columns={"Adj Close": tops[0]})
                    else:
                        price = pd.DataFrame()

                price = price.dropna(how="all")

                if not price.empty:
                    pf = vbt.Portfolio.from_holding(price, freq="1M")
                    stats = pf.stats()

                    st.subheader(f"백테스팅 – 상위 {n}개")

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("연평균", f"{stats.get('CAGR%', 0):.1f}%")
                    c2.metric("누적", f"{stats.get('Total Return%', 0):.0f}%")
                    c3.metric("최대낙폭", f"{stats.get('Max Drawdown%', 0):.1f}%")
                    c4.metric("샤프", f"{stats.get('Sharpe Ratio', 0):.2f}")

                    fig = go.Figure()
                    value = pf.value()
                    fig.add_trace(go.Scatter(
                        x=value.index,
                        y=value / value.iloc[0] * 100,
                        name="내 전략"
                    ))

                    spy = yf.download("SPY", start="2019-01-01", progress=False)
                    if not spy.empty:
                        spy_adj = spy["Adj Close"]
                        fig.add_trace(go.Scatter(
                            x=spy_adj.index,
                            y=spy_adj / spy_adj.iloc[0] * 100,
                            name="S&P500",
                            line=dict(dash="dash")
                        ))

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("백테스팅 가격 데이터를 불러오지 못했습니다.")
            else:
                st.warning("유효한 결과가 없습니다. 티커/데이터 기간을 확인해주세요.")

st.caption("Grok Ranker Ultimate v5.0 – 2025-12-09 05:40")
