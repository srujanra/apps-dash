import os
import sys
from datetime import datetime
from os.path import dirname

import numpy as np
import pandas as pd
import polars as pl
from qablet.black_scholes.mc import LVMCModel
from qablet_contracts.eq.autocall import AutoCallable

sys.path.append(dirname(dirname(__file__)))
from src.model import CFModelPyCSV, get_cf
from src.utils import compute_irr


ROOTDIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def base_dataset():
    """Create the base dataset. Asset data and model parameters will be
    added later, specific to each pricing date."""
    return {
        "MC": {
            "PATHS": 10_000,
            "TIMESTEP": 100,  # BSM doesn't need small timesteps
            "SEED": 1,
        },
        "BASE": "USD",
    }


def backtest_acn(ticker="SPX"):
    # load price data
    filename = ROOTDIR + "\\data\\SP500.csv"

    # get all month ends
    data = pl.read_csv(
        filename, try_parse_dates=True, infer_schema_length=None
    ).set_sorted("date")

    # Use current divs and risk free for historical pricings
    dataset = base_dataset()

    # Rates and divs data
    times = np.array([0.0, 2.0])
    rates = np.array([0.03, 0.03])
    discount_data = ("ZERO_RATES", np.column_stack((times, rates)))
    assets_data = {"USD": discount_data}
    divs = 0.02  # get_divs(basket)

    # Create the models
    model = LVMCModel()
    # filename = "data/SP500.csv"
    bk_model = CFModelPyCSV(filename=filename, base="USD")

    results = []
    all_stats = []
    all_ts = []
    monthend_dates = pd.bdate_range(
        datetime(2019, 5, 31), datetime(2024, 4, 30), freq="1BME"
    )
    m_per = 3
    m_exp = 12
    num_trials = len(monthend_dates) - m_exp
    for i in range(num_trials):
        pricing_ts = monthend_dates[i]  # timestamp of trading date
        barrier_dts = monthend_dates[i + m_per : i + m_exp + 1 : m_per]

        # update assets data with equity forwards (need only one)
        row_idx = data["date"].search_sorted(pricing_ts)
        spot = data.item(row_idx, ticker)
        fwds = spot * np.exp((rates - divs) * times)
        assets_data[ticker] = ("FORWARDS", np.column_stack((times, fwds)))

        # update dataset
        dataset["PRICING_TS"] = int(
            pricing_ts.value / 1e6
        )  # ns to ms timestamp
        dataset["ASSETS"] = assets_data
        dataset["LV"] = {
            "ASSET": ticker,
            "VOL": 0.3,  # hardcoded vol
        }

        cpn_rate = 0.05
        timetable = AutoCallable(
            ccy="USD",
            asset_name=ticker,
            initial_spot=spot,
            strike=spot * 0.8,
            accrual_start=pricing_ts,
            maturity=barrier_dts[-1],
            barrier=spot,
            barrier_dates=barrier_dts,
            cpn_rate=cpn_rate,
        ).timetable()

        # Compute prices of 0 and unit coupon
        px, _ = model.price(timetable, dataset)

        # Compute backtest stats and irr
        stats = bk_model.cashflow(timetable)
        yrs_vec, cf_vec, ts_vec = get_cf(pricing_ts, timetable, stats)
        irr = compute_irr(cf_vec, yrs_vec, px)

        # Calculate is_ko and duration
        is_ko = False  # FIXFIX cf_vec_0[-1] == 0
        # max_cf_idx = np.max(np.nonzero(cf_vec_0))
        duration = 1.0  # yrs_vec[max_cf_idx]
        results.append((pricing_ts, irr, is_ko, duration))
        all_stats.append((ts_vec.astype("uint64").tolist(), cf_vec.tolist()))
        all_ts.append(pricing_ts.value)

    df = pd.DataFrame(
        results,
        columns=["date", "irr", "isKO", "duration"],
    )
    # results.set_index("date", inplace=True)
    return df, {"stats": all_stats, "ts": all_ts}


if __name__ == "__main__":
    sys.path.append(dirname(dirname(__file__)))

    df, _ = backtest_acn()

    import plotly.express as px

    fig = px.scatter(
        x=df["date"],
        y=df["irr"],
        # hover_name=df["date"],
    )
    fig.update_layout(
        margin={"l": 40, "b": 40, "t": 10, "r": 0}, hovermode="closest"
    )
    # fig.show()
    fig.write_html("first_figure.html", auto_open=True)
