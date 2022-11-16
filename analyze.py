import re
import sqlite3
from datetime import datetime, timedelta

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from statsmodels.tsa.exponential_smoothing.ets import ETSModel

from config import *

matplotlib.use('SVG')

QUERY_SQL = """
SELECT time, upload, download, remaining FROM kycloud WHERE time BETWEEN ? AND ?;
"""

QUERY_DATES_SQL = """
SELECT DISTINCT substr(time, 1, 7) FROM kycloud;
"""


def get_period(year: int, month: int):
    begin = datetime(year=year, month=month, day=RESET_DATE)
    end = datetime(
        year=year if month != 12 else year + 1,
        month=month + 1 if month != 12 else 1,
        day=RESET_DATE)
    return begin, end


def get_record_of_month(year: int, month: int):
    begin, end = get_period(year, month)
    result = []
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        c = cur.execute(QUERY_SQL, (begin, end))
        for row in c:
            row = (
                row[0][:-2] + '00',
                row[1],
                row[2],
                row[3]
            )
            result.append(row)
        c.close()
        cur.close()
    # Filter reset delay, supposed reset must happen in reset day
    start = 0
    for i in range(1, len(result)):
        current = result[i]
        if int(re.findall(r'-(\d*) ', current[0])[0]) != RESET_DATE:
            break
        last = result[i - 1]
        if current[3] > last[3]:
            start = i
            break
    return result[start:]


def get_available_date():
    result = []
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        c = cur.execute(QUERY_DATES_SQL)
        for row in c:
            r = tuple(map(lambda x: int(x), str(row[0]).split('-')))
            result.append((r[0], r[1]))
        c.close()
        cur.close()
    return result


def is_date_available(year: int, month: int):
    if (year, month) not in get_available_date():
        return False
    return True


def get_remaining_dataframe(year: int, month: int, sample_freq: str = '3H'):
    data = get_record_of_month(year, month)
    last_record = data[-1]
    data = map(lambda record: (record[0], record[3]), data)
    df = pd.DataFrame(data, columns=['Time', 'Remaining'])
    df.Time = pd.to_datetime(df.Time, format='%Y-%m-%d %H:%M:%S')
    df = df.set_index('Time')
    df = df.asfreq('H')
    df = df.resample('H').interpolate()
    df = df.resample(sample_freq).mean()
    return df, last_record


def get_predict(remaining_df):
    begin_date = remaining_df.index[0]
    last_date = remaining_df.index[-1]
    _, end = get_period(begin_date.year, begin_date.month)
    ets = ETSModel(remaining_df.Remaining, trend='add').fit(full_output=False, disp=False)
    ets_predict = ets.get_prediction(start=last_date, end=end)
    return ets_predict.summary_frame()


def get_plot(remaining_df: pd.DataFrame, predicted: pd.DataFrame = None, info_text: str = "") -> plt:
    plt.rcParams['ytick.labelsize'] = 18
    plt.rcParams['xtick.labelsize'] = 12
    begin_date = remaining_df.index[0]
    _, end = get_period(begin_date.year, begin_date.month)
    plt.figure(figsize=(16, 8))
    plt.plot(remaining_df.Remaining, color="Green")
    ax = plt.gca()
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%d GB'))
    ax.yaxis.set_major_locator(mticker.MultipleLocator(20))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.gcf().autofmt_xdate()
    ax.set_xlim(xmin=begin_date, xmax=end)
    ax.set_ylim(ymin=-20, ymax=TOTAL_AVAIL + 20)
    plt.grid(linestyle=':')
    plt.axhline(y=0, c="r", ls="--", lw=1)
    plt.axvline(x=end, c="r", ls="--", lw=1)
    plt.title(f"Remaining Traffic amount of Kycloud in {begin_date.year}-{begin_date.month}", fontsize=20)
    plt.text(begin_date + timedelta(days=0.5), 10, info_text, fontsize=18, bbox=dict(
        boxstyle="round",
        color="gray",
        alpha=0.3
    ))

    yticks = ax.yaxis.get_major_ticks()
    yticks[1].label1.set_visible(False)
    yticks[13].label1.set_visible(False)
    yticklines = ax.yaxis.get_ticklines()
    yticklines[2].set_visible(False)
    yticklines[26].set_visible(False)

    if predicted is not None:
        plt.plot(predicted["mean"], label="Mean", color="orange")
        plt.plot(predicted["pi_upper"], label="Upper", linestyle="--", color="Gray")
        plt.plot(predicted["pi_lower"], label="Lower", linestyle="--", color="Gray")
        plt.fill_between(predicted.index, predicted["pi_upper"], predicted["pi_lower"], alpha=0.2, color="Gray")
        xy = (remaining_df.index[-1], remaining_df.Remaining[-1])
        plt.scatter(xy[0], xy[1], s=100, color="Blue", zorder=10)
        plt.annotate('{data:.2f} GB'.format(data=remaining_df.Remaining[-1]),
                     xy,
                     xytext=(xy[0], xy[1] + 20),
                     fontsize=20,
                     arrowprops=dict(arrowstyle="->", color="Black")
                     )
    plt.tight_layout()
    return plt


def predicted_flow_warning(predicted: pd.DataFrame):
    last_record = predicted.tail(1).values[0]
    lower = last_record[1]
    upper = last_record[2]
    mean = last_record[0]
    if upper <= 0:
        return 'Would Exceeded'
    if mean <= 0:
        return 'Maybe Exceeded'
    if lower <= 0:
        return 'Almost Exceeded'
    return 'Safe'


def do_all(year: int, month: int):
    if not is_date_available(year, month):
        raise Exception(f"Date {year}-{month} have no data to analyze.")
    begin, end = get_period(year, month)
    is_need_predict = datetime.now() < end
    df, last_record = get_remaining_dataframe(year, month)
    predicted = None
    safe_level = None
    if is_need_predict:
        predicted = get_predict(df)
        safe_level = predicted_flow_warning(predicted)
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info_text = f"""Now: {now_time}
Last record: {last_record[0]}
    - Uploaded: {last_record[1]} GB
    - Downloaded: {last_record[2]} GB
    - Remaining: {last_record[3]} GB
"""
    if safe_level != None:
        info_text += f"Safe Level: {safe_level}"
    plot = get_plot(df, predicted, info_text)
    return plot, safe_level


def main():
    plot, safe_level = do_all(datetime.now().year, datetime.now().month)
    if safe_level is not None:
        print(f"Safe level is {safe_level}")


if __name__ == '__main__':
    main()
