#!/usr/bin/env python3
"""
PhD-Level Stock Screener with ATR-Based Risk Management
Based on: Jegadeesh-Titman, Llorente, Lo-Mamaysky-Wang, Bernard-Thomas
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import warnings
warnings.filterwarnings('ignore')

def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    high = df['High']
    low = df['Low']
    close = df['Close']

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analyze_stock(ticker, capital=1000):
    """Analyze a single stock and return trade parameters"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")

        if len(df) < 50:
            return None

        current_price = df['Close'].iloc[-1]

        # Calculate ATR
        atr = calculate_atr(df)
        current_atr = atr.iloc[-1]
        atr_pct = (current_atr / current_price) * 100

        # Calculate momentum (Jegadeesh-Titman 12-1)
        if len(df) >= 252:
            mom_12m = (df['Close'].iloc[-22] / df['Close'].iloc[-252] - 1) * 100
        else:
            mom_12m = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100

        # Calculate RSI
        rsi = calculate_rsi(df['Close'])
        current_rsi = rsi.iloc[-1]

        # 52-week high/low
        high_52w = df['High'].max()
        low_52w = df['Low'].min()
        pct_from_high = ((current_price - high_52w) / high_52w) * 100

        # Volume analysis (Llorente)
        avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
        current_volume = df['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

        # Calculate stops and targets (ATR-based)
        stop_loss = current_price - (2 * current_atr)
        stop_pct = ((stop_loss - current_price) / current_price) * 100

        target_1 = current_price + (3 * current_atr)
        target_1_pct = ((target_1 - current_price) / current_price) * 100

        target_2 = current_price + (5 * current_atr)
        target_2_pct = ((target_2 - current_price) / current_price) * 100

        # Position sizing
        risk_per_share = current_price - stop_loss
        if risk_per_share > 0:
            shares = int(capital * 0.02 / risk_per_share)  # 2% risk rule
            shares = max(1, min(shares, int(capital / current_price)))
        else:
            shares = int(capital / current_price)

        position_value = shares * current_price
        max_loss = shares * risk_per_share

        # Composite score (0-10)
        score = 0

        # Momentum score (0-3)
        if mom_12m > 30:
            score += 3
        elif mom_12m > 15:
            score += 2
        elif mom_12m > 0:
            score += 1

        # RSI score (0-2)
        if 40 <= current_rsi <= 60:
            score += 2  # Neutral zone, room to run
        elif 30 <= current_rsi < 40 or 60 < current_rsi <= 70:
            score += 1

        # Breakout potential (0-2)
        if pct_from_high > -5:
            score += 2  # Near highs
        elif pct_from_high > -15:
            score += 1

        # Volume confirmation (0-2)
        if volume_ratio > 1.5:
            score += 2
        elif volume_ratio > 1.0:
            score += 1

        # Trend strength (0-1)
        sma_20 = df['Close'].rolling(20).mean().iloc[-1]
        sma_50 = df['Close'].rolling(50).mean().iloc[-1]
        if current_price > sma_20 > sma_50:
            score += 1

        return {
            'ticker': ticker,
            'price': current_price,
            'atr': current_atr,
            'atr_pct': atr_pct,
            'stop_loss': stop_loss,
            'stop_pct': stop_pct,
            'target_1': target_1,
            'target_1_pct': target_1_pct,
            'target_2': target_2,
            'target_2_pct': target_2_pct,
            'shares': shares,
            'position_value': position_value,
            'max_loss': max_loss,
            'momentum': mom_12m,
            'rsi': current_rsi,
            'pct_from_high': pct_from_high,
            'volume_ratio': volume_ratio,
            'score': score,
            '52w_high': high_52w,
            '52w_low': low_52w
        }

    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

def print_trade_card(result):
    """Print a formatted trade card for a stock"""
    print(f"\n{'='*60}")
    print(f"  {result['ticker']}  |  Score: {result['score']}/10")
    print(f"{'='*60}")
    print(f"  Current Price:    ${result['price']:.2f}")
    print(f"  52-Week Range:    ${result['52w_low']:.2f} - ${result['52w_high']:.2f}")
    print(f"  From 52W High:    {result['pct_from_high']:.1f}%")
    print(f"  ATR (14):         ${result['atr']:.2f} ({result['atr_pct']:.1f}%)")
    print(f"  RSI (14):         {result['rsi']:.1f}")
    print(f"  12M Momentum:     {result['momentum']:.1f}%")
    print(f"  Volume Ratio:     {result['volume_ratio']:.2f}x avg")
    print()
    print(f"  ╔{'═'*56}╗")
    print(f"  ║  TRADE SETUP                                         ║")
    print(f"  ╠{'═'*56}╣")
    print(f"  ║  Entry:       ${result['price']:<10.2f}                        ║")
    print(f"  ║  Stop Loss:   ${result['stop_loss']:<10.2f} ({result['stop_pct']:>6.1f}%)             ║")
    print(f"  ║  Target 1:    ${result['target_1']:<10.2f} ({result['target_1_pct']:>+6.1f}%)             ║")
    print(f"  ║  Target 2:    ${result['target_2']:<10.2f} ({result['target_2_pct']:>+6.1f}%)             ║")
    print(f"  ╠{'═'*56}╣")
    print(f"  ║  Shares:      {result['shares']:<10}                        ║")
    print(f"  ║  Position:    ${result['position_value']:<10.2f}                      ║")
    print(f"  ║  Max Loss:    ${result['max_loss']:<10.2f}                      ║")
    print(f"  ╚{'═'*56}╝")

def print_trading_rules():
    """Print mandatory trading rules"""
    print(f"\n{'='*60}")
    print("🚨 MANDATORY TRADING RULES - CSU.TO LESSON")
    print(f"{'='*60}")
    print("""
  1. SET STOP LIMIT ORDER IMMEDIATELY AFTER BUYING
     - Use Stop Limit (not Stop Market)
     - Good Till: 90 days, then RENEW

  2. NEVER BUY WITHOUT KNOWING YOUR EXIT
     ✓ Entry price
     ✓ Stop loss price
     ✓ Target price
     ✓ Position size

  3. CSU.TO REMINDER: 48% loss could have been 10-15%

  4. EXCEPTION: Index ETFs (XEQT) - hold forever, DCA
    """)

def main():
    parser = argparse.ArgumentParser(description='Stock Screener with ATR-Based Stops')
    parser.add_argument('--tickers', nargs='+', default=['TQQQ', 'MU', 'AMD', 'INTC', 'NVDA'],
                        help='Tickers to analyze')
    parser.add_argument('--capital', type=float, default=5000,
                        help='Capital to allocate')

    args = parser.parse_args()

    print(f"\n{'#'*60}")
    print(f"#  STOCK SCREENER - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"#  Capital: ${args.capital:,.0f}")
    print(f"{'#'*60}")

    results = []
    for ticker in args.tickers:
        print(f"\nAnalyzing {ticker}...", end=" ")
        result = analyze_stock(ticker, args.capital)
        if result:
            results.append(result)
            print(f"✓ Score: {result['score']}/10")
        else:
            print("✗ Failed")

    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)

    # Print trade cards
    for result in results:
        print_trade_card(result)

    # Print trading rules
    print_trading_rules()

    print(f"\n{'='*60}")
    print("Analysis complete. SET YOUR STOPS BEFORE YOU BUY.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
