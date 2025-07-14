import math
import pandas as pd
import numpy as np
# Calculate annualized return, Sharpe ratio and annualized volatility
def calculate_annual_return_sharpe_volatility(df):
    equity_start = df['equity'].iloc[0]
    equity_end = df['equity'].iloc[-1]
    days = len(df)
    # calculate annual return
    annual_return = (equity_end / equity_start) ** (252 / days) - 1
    df['daily_return'] = df['equity'].pct_change()
    # remove NaN
    daily_returns = df['daily_return'].dropna()
    # calculate Sharpe Studio
    if daily_returns.std() and not np.isnan(daily_returns.std()):
        sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
    else:
        sharpe_ratio = 0  # or np.nan
    # calculate annualized volatility
    volatility = daily_returns.std() * np.sqrt(252)
    return annual_return, sharpe_ratio, volatility
# calculate max backdrawdown
def calculate_max_drawdown(equity_series: pd.Series):
    roll_max = equity_series.cummax()
    drawdown = equity_series / roll_max - 1
    max_drawdown = drawdown.min()
    return max_drawdown, drawdown

def backtest(df, initial_money, slippage, c_rate):
    df.at[0, 'hold_num'] = 0  
    df.at[0, 'stock_value'] = 0  
    df.at[0, 'actual_pos'] = 0  # everyday
    df.at[0, 'cash'] = initial_money  
    df.at[0, 'equity'] = initial_money  
    after_tax = initial_money 

    # status every day after the first day.
    # start from scond day
    for i in range(1, df.shape[0]):
        # Number of stocks held on the previous day
        hold_num = df.at[i - 1, 'hold_num']

        # Determine whether there is an ex-rights on the day. If there is an ex-rights, hold_num needs to be adjusted
        # If the increase or decrease calculated by the closing price on that day is different from the actual increase or decrease on that day, it means that an ex-rights transaction occurred on that day.
        if abs((df.at[i, 'Close'] / df.at[i - 1, 'Close'] - 1) - df.at[i, 'Percentage']) > 0.001:
            stock_value = df.at[i - 1, 'stock_value']
            # The exchange will announce the ex-rights price
            last_price = df.at[i, 'Close'] / (df.at[i, 'Percentage'] + 1)
            hold_num = stock_value / last_price
            hold_num = int(hold_num)

        # Determine whether to adjust the position: compare the position with the previous day
        # Need to adjust position
        if df.at[i, 'pos'] != df.at[i - 1, 'pos']:

            # How many stocks should be bought for positions that need to be adjusted?
            # Yesterday's total assets * today's position / today's opening price, get the number of stocks you need to hold
            theory_num = df.at[i - 1, 'equity'] * df.at[i, 'pos'] / df.at[i, 'Open']
            # Round up the number of shares you need to hold
            theory_num = int(theory_num)

            # Compare theory_num with the number of stocks held yesterday to determine whether to increase or decrease the position
            # Adding positions
            if theory_num >= hold_num:
                buy_num = theory_num - hold_num
                buy_num = int(buy_num / 100) * 100 

                # Calculate the maximum number of shares you can buy (100 shares as one lot)
                available_cash = df.at[i - 1, 'cash']
                price_with_slippage = df.at[i, 'Open'] + slippage

                # Calculate the number of shares that can be purchased (whole hundred shares)
                buy_num = int((available_cash) / price_with_slippage / 100) * 100

                # Calculate the cash spent on buying stocks
                buy_cash = buy_num * (df.at[i, 'Open'] + slippage)

                # Calculate the number of stocks and cash held at the close
                df.at[i, 'hold_num'] = hold_num + buy_num
                df.at[i, 'cash'] = df.at[i - 1, 'cash'] - buy_cash
            # Lighten up
            else:
                # Calculate the number of stocks sold. The number of stocks sold does not need to be an integer and does not need to be rounded to the nearest hundred.
                sell_num = hold_num - theory_num

                # Calculating Cash Received from Selling Stocks
                sell_cash = sell_num * (df.at[i, 'Open'] - slippage)
                # Calculate the handling fee, 20.315% of the profit
                if (df.at[i - 1, 'cash'] + sell_cash + (hold_num - sell_num) * df.at[i, 'hold_num']) > after_tax:
                    commission = sell_cash * c_rate
                else:
                    commission = 0
                df.at[i, 'Fees'] = commission

                # Calculate the number of stocks and cash held at the end of the day
                df.at[i, 'hold_num'] = hold_num - sell_num
                df.at[i, 'cash'] = df.at[i - 1, 'cash'] + sell_cash - commission
                after_tax = df.at[i, 'cash'] + df.at[i, 'Close'] * (hold_num - sell_num)
        # No need to adjust the position
        else:
            # Calculate the number of stocks and cash held at the end of the day
            df.at[i, 'hold_num'] = hold_num
            df.at[i, 'cash'] = df.at[i - 1, 'cash']

        # The above calculations yield the daily hold_num and cash
        # Calculate various asset data at the close of the day
        df.at[i, 'stock_value'] = df.at[i, 'hold_num'] * df.at[i, 'Close']
        df.at[i, 'equity'] = df.at[i, 'cash'] + df.at[i, 'stock_value']
        df.at[i, 'actual_pos'] = df.at[i, 'stock_value'] / df.at[i, 'equity']

    annual_return, sharpe, volatility = calculate_annual_return_sharpe_volatility(df)
    max_dd, drawdown_series = calculate_max_drawdown(df['equity'])
    # print(f"annual_return: {annual_return:.2%}")
    # print(f"max_drowdown: {max_dd:.2%}")
    # print(f"sharpe_ratio: {sharpe:.2f}")
    # print(f"volatility: {volatility:.2%}")
    return df, annual_return, max_dd, sharpe, volatility
