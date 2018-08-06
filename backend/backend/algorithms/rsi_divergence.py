import sys
sys.path.append('..')
from technical_analysis import analysis
import pandas as pd
import math
from zipline.api import order_target, symbol, order_target_percent
from zipline import run_algorithm


def rsi_div_run(start_date, end_date, capital_base, ticker, log_channel):
    def create_rsi_price_array(rsi, closelist):
        price_rsi = []
        prices_close_list = list(closelist.values.flatten())

        for price, rsi in zip(rsi, prices_close_list):
            price_rsi.append([rsi, price])

        return price_rsi

    def bullish_divergence(price_rsi, percent_baseline, low):
        get_rsi = []
        get_price = []
        low_vals = []
        trough_vals = []
        # get array of just price
        for rsi in price_rsi:
            rsi = rsi[1]
            get_rsi.append(rsi)

        # get array of just rsi
        for price in price_rsi:
            price = price[0]
            get_price.append(price)

        for value in get_rsi:
            if value < low:
                low_vals.append(value)
        # filter actual troughs from potentials
        for item in low_vals:
            try:
                if get_rsi[get_rsi.index(item) - 1] > item and \
                        get_rsi[get_rsi.index(item) + 1] > item and \
                        get_rsi.index(item) != 0:
                    trough_vals.append(item)
            except:
                pass
        # check to see if potential pattern.
        # A potential pattern means it is current and RSI is gaining strength (bullish)
        try:
            if trough_vals[-1] == get_rsi[-2] and trough_vals[-1] > trough_vals[-2]:

                delta = get_rsi[(get_rsi.index(trough_vals[-2])):(get_rsi.index(trough_vals[-1]))]
                payload = []
                for item in delta:
                    if item > trough_vals[-1] and item > trough_vals[-2]:
                        difference = item - trough_vals[-2]
                        percent_dif = difference / trough_vals[-2]

                        if percent_dif >= percent_baseline:

                            trough_vals = trough_vals[-2:]
                            trough_one_index = (get_rsi.index(trough_vals[-1]))
                            trough_two_index = (get_rsi.index(trough_vals[-2]))
                            price_signal = get_price[trough_one_index]
                            price_setup = get_price[trough_two_index]
                            # confirm divergence by comparing price action
                            if price_signal < price_setup:
                                payload.append(trough_vals)
                                payload.append(len(delta))
                                payload.append([price_setup, price_signal])
                                break
                if len(payload) != 0:
                    return payload
        except:
            pass
        return

    def set_trailing_stop(context, data):
        if context.portfolio.positions[context.stock].amount:
            price = data[context.stock].price
            context.stop_price = max(context.stop_price, context.stop_percentage * price)

    def initialize(context):
        context.max_notional = 100000
        context.stock = symbol(ticker)
        context.stop_price = 0
        context.stop_percentage = 0.85

    def handle_data(context, data):

        lookback = 200
        percent_baseline = 0.5  # RSI retracement amount
        low = 30  # RSI low value
        RSI_time_period = 3
        divergence_strength = 0

        prices_close = data.history(assets=context.stock, bar_count=lookback,
                                    frequency='1d', fields='price')

        prices = data.history(assets=context.stock, bar_count=lookback,
                              frequency='1d', fields='price')

        rsi = analysis.RSI(prices, RSI_time_period)

        rsi_prices = create_rsi_price_array(rsi, prices_close)
        num_shares = math.floor(context.max_notional / data[context.stock].close_price)

        if num_shares > 0:
            set_trailing_stop(context, data)

        if data[context.stock].price < context.stop_price:
            order_target(context.stock, 0)  # Sell all the stock
            print("selling")
            context.stop_price = 0

        current_shares = context.portfolio.positions[context.stock].amount

        divergence = bullish_divergence(rsi_prices, percent_baseline, low)

        if divergence is not None and divergence[1] > 1 and current_shares == 0:
            troughs = divergence[0]
            trough_diff = troughs[1] - troughs[0]  # strength of divergence

            if trough_diff > divergence_strength:
                order_target_percent(context.stock, 1.0)
                print("buying")
                # Bought shares

    start = pd.to_datetime(start_date).tz_localize('US/Eastern')
    end = pd.to_datetime(end_date).tz_localize('US/Eastern')

    result = run_algorithm(start=start, end=end, initialize=initialize,
                           handle_data=handle_data, capital_base=capital_base,
                           bundle='quantopian-quandl')

    return result


result = rsi_div_run('2016-01-01', '2017-01-01', 1000000, 'FB', 'a')

print(result.tail())
