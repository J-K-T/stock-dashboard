import streamlit as st
import yfinance as yf
import pandas as pd
import time
from functools import lru_cache
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="darkgrid")

# Extended stock list
stocks = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'BAC', 'DIS',
    'V', 'MA', 'PYPL', 'ADBE', 'NFLX', 'INTC', 'CSCO', 'ORCL', 'CRM', 'T',
    'KO', 'PEP', 'MCD', 'WMT', 'CVX', 'XOM', 'BA', 'GS', 'CAT', 'GE',
    'IBM', 'MMM', 'MDT', 'NEE', 'TXN', 'LIN', 'UNH', 'JNJ', 'PFE', 'MRK',
    'AMGN', 'COST', 'LOW', 'HD', 'SBUX', 'QCOM', 'SPGI', 'BLK', 'AXP', 'BK'
]

def score_stock(stock):
    score = 0

    if stock['Price Change %'] is not None:
        score += max(min(stock['Price Change %'], 10), -10) * 3

    if stock['Volume Change %'] is not None:
        score += max(min(stock['Volume Change %'], 50), -50) * 0.4

    pe = stock['P/E Ratio']
    if pe and pe > 0:
        if 10 <= pe <= 25:
            score += 10
        else:
            score -= abs(pe - 17.5) * 0.5

    dy = stock['Dividend Yield']
    if dy > 1:
        score += min(dy, 5) * 2

    dist = stock['Dist from 52W High %']
    if dist is not None:
        if dist >= -20:
            score += (20 + dist) * 0.5
        else:
            score -= 10

    rec = stock['Analyst Rec']
    if rec is not None:
        if rec <= 2:
            score += 10
        elif rec <= 3:
            score += 5
        else:
            score -= 5

    return score

@lru_cache(maxsize=128)
def fetch_stock_info(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.info

def fetch_batch_data(symbols):
    try:
        data = yf.download(symbols, period='2d', group_by='ticker', threads=True)
    except Exception as e:
        st.warning(f"Rate limit or download error, retrying after 60 seconds... {e}")
        time.sleep(60)
        return fetch_batch_data(symbols)
    return data

def analyze_stocks(stock_list):
    data = []
    hist_data = fetch_batch_data(stock_list)
    for symbol in stock_list:
        try:
            if symbol in hist_data.columns.levels[0]:
                hist = hist_data[symbol]
            else:
                st.warning(f"Skipping {symbol}: no historical data")
                continue

            if len(hist) < 2:
                st.warning(f"Skipping {symbol}: insufficient historical data")
                continue

            try:
                prev_close = hist['Close'].iloc[-2]
                last_close = hist['Close'].iloc[-1]
                price_change_pct = ((last_close - prev_close) / prev_close) * 100

                prev_vol = hist['Volume'].iloc[-2]
                last_vol = hist['Volume'].iloc[-1]
                vol_change_pct = ((last_vol - prev_vol) / prev_vol) * 100 if prev_vol != 0 else 0
            except Exception as e:
                st.error(f"Error calculating price/volume changes for {symbol}: {e}")
                continue

            info = fetch_stock_info(symbol)

            pe_ratio = info.get('trailingPE', None)
            dividend_yield = info.get('dividendYield', 0) or 0
            market_cap = info.get('marketCap', 0) or 0

            fifty_two_week_high = info.get('fiftyTwoWeekHigh', None)
            if fifty_two_week_high and fifty_two_week_high != 0:
                dist_52w_high_pct = ((last_close - fifty_two_week_high) / fifty_two_week_high) * 100
            else:
                dist_52w_high_pct = None

            recommendation = info.get('recommendationMean', None)

            stock = {
                'Symbol': symbol,
                'Price Change %': price_change_pct,
                'Volume Change %': vol_change_pct,
                'P/E Ratio': pe_ratio,
                'Dividend Yield': dividend_yield * 100,
                'Market Cap': market_cap,
                'Dist from 52W High %': dist_52w_high_pct,
                'Analyst Rec': recommendation
            }

            stock['Score'] = score_stock(stock)
            data.append(stock)

        except Exception as e:
            st.error(f"Error processing {symbol}: {e}")
            continue

    df = pd.DataFrame(data)
    df = df.sort_values(by='Score', ascending=False)
    return df

def plot_scores(df):
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x='Score', y='Symbol', data=df, ax=ax, palette="viridis")
    ax.set_title('Stock Scores')
    st.pyplot(fig)

def show_news_section(df, keywords=None):
    st.markdown("## 📰 Recent News")
    keywords = [k.lower() for k in (keywords or ["earnings", "acquisition", "merger", "upgrade", "buyout"])]

    for _, row in df.iterrows():
        symbol = row["Symbol"]
        st.subheader(f"🗞️ {symbol} News")
        try:
            ticker = yf.Ticker(symbol)
            news_items = ticker.news
            count = 0

            for article in news_items:
                title = article.get("title")
                link = article.get("link")

                if not title or not link:
                    continue

                if any(kw in title.lower() for kw in keywords):
                    st.markdown(f"- [{title}]({link})")
                    count += 1

                if count >= 5:
                    break

            if count == 0:
                st.markdown("_No relevant news found based on filters._")

        except Exception as e:
            st.error(f"Could not load news for {symbol}: {e}")

def main():
    st.title("📈 Advanced Stock Analyzer with Batch Data, Caching & News")

    selected_stocks = st.multiselect("Select stocks to analyze", stocks, default=stocks[:15])

    keyword_input = st.text_input("Filter news by keywords (comma-separated):", "earnings, acquisition, merger, upgrade, buyout")
    keywords = [k.strip().lower() for k in keyword_input.split(",")]

    if st.button("Analyze"):
        with st.spinner("Fetching and analyzing stock data..."):
            analyzed_df = analyze_stocks(selected_stocks)
            st.dataframe(analyzed_df[['Symbol', 'Score', 'Price Change %', 'Volume Change %',
                                      'P/E Ratio', 'Dividend Yield', 'Dist from 52W High %', 'Analyst Rec']])
            plot_scores(analyzed_df)
            show_news_section(analyzed_df, keywords)

if __name__ == "__main__":
    main()
