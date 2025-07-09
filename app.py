
import yfinance as yf 
import pandas as pd
import time
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.animation import FuncAnimation

stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'BAC', 'DIS']

def fetch_stock_data(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period='2d')
    info = ticker.info

    if len(hist) < 2:
        return None

    prev_close = hist['Close'][-2]
    last_close = hist['Close'][-1]
    price_change_pct = ((last_close - prev_close) / prev_close) * 100

    prev_vol = hist['Volume'][-2]
    last_vol = hist['Volume'][-1]
    vol_change_pct = ((last_vol - prev_vol) / prev_vol) * 100 if prev_vol != 0 else 0

    pe_ratio = info.get('trailingPE', None)
    dividend_yield = info.get('dividendYield', 0) or 0
    market_cap = info.get('marketCap', 0) or 0

    fifty_two_week_high = info.get('fiftyTwoWeekHigh', None)
    if fifty_two_week_high and fifty_two_week_high != 0:
        dist_52w_high_pct = ((last_close - fifty_two_week_high) / fifty_two_week_high) * 100
    else:
        dist_52w_high_pct = None

    recommendation = info.get('recommendationMean', None)

    return {
        'Symbol': symbol,
        'Price Change %': price_change_pct,
        'Volume Change %': vol_change_pct,
        'P/E Ratio': pe_ratio,
        'Dividend Yield': dividend_yield * 100,
        'Market Cap': market_cap,
        'Dist from 52W High %': dist_52w_high_pct,
        'Analyst Rec': recommendation
    }

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

def analyze_stocks(stock_list):
    data = []
    for symbol in stock_list:
        stock = fetch_stock_data(symbol)
        if stock is None:
            print(f"Skipping {symbol} (insufficient data)")
            continue
        stock['Score'] = score_stock(stock)
        data.append(stock)

    df = pd.DataFrame(data)
    df = df.sort_values(by='Score', ascending=False)
    return df

def live_track_and_plot(stock_symbols, interval=30, duration=5, alert_threshold=1.0):
    print(f"Tracking and plotting stocks: {', '.join(stock_symbols)}")
    print(f"Updating every {interval} seconds for {duration} minutes...\n")

    initial_prices = {}
    price_history = {sym: [] for sym in stock_symbols}
    timestamps = []

    for symbol in stock_symbols:
        ticker = yf.Ticker(symbol)
        price = ticker.info.get('regularMarketPrice', None)
        if price is None:
            print(f"Warning: Could not fetch initial price for {symbol}")
            price = 0
        initial_prices[symbol] = price
        price_history[symbol].append(price)

    start_time = time.time()
    end_time = start_time + duration * 60

    sns.set_theme(style="darkgrid")
    fig, ax = plt.subplots(figsize=(10, 6))
    lines = {}
    for sym in stock_symbols:
        (line,) = ax.plot([], [], label=sym)
        lines[sym] = line

    ax.set_title('Live Stock Prices')
    ax.set_xlabel('Time (HH:MM:SS)')
    ax.set_ylabel('Price ($)')
    ax.legend()

    def update(frame):
        current_time = time.time()
        if current_time > end_time:
            print("Tracking complete.")
            plt.close(fig)
            return

        timestamps.append(time.strftime("%H:%M:%S"))
        for sym in stock_symbols:
            ticker = yf.Ticker(sym)
            price = ticker.info.get('regularMarketPrice', None)
            if price is None:
                price = price_history[sym][-1] if price_history[sym] else 0
            price_history[sym].append(price)

            initial_price = initial_prices[sym]
            if initial_price > 0:
                change_pct = ((price - initial_price) / initial_price) * 100
                if abs(change_pct) >= alert_threshold:
                    print(f"ALERT: {sym} price changed by {change_pct:.2f}% from start price (${initial_price:.2f} → ${price:.2f})")

            lines[sym].set_data(timestamps, price_history[sym])

        ax.relim()
        ax.autoscale_view()
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

    ani = FuncAnimation(fig, update, interval=interval*1000)
    plt.show()

if __name__ == "__main__":
    print("Analyzing stocks with deeper metrics...")
    analyzed_df = analyze_stocks(stocks)
    print(analyzed_df[['Symbol', 'Score', 'Price Change %', 'Volume Change %', 'P/E Ratio', 'Dividend Yield', 'Dist from 52W High %', 'Analyst Rec']])

    to_track = analyzed_df.head(5)['Symbol'].tolist()
    live_track_and_plot(to_track, interval=30, duration=3, alert_threshold=1.0)
