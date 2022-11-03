from analyze import datetime, timedelta, get_period, get_remaining_dataframe, get_predict
import urllib.request
from urllib.parse import urlencode
import json
from config import *

title_str = r"Ky剩余流量：{remaining} GB，剩余天数：{days}天"
context_str = r"""# Kycloud 流量详情和图表
---
## 流量信息详情
* 上传流量：{upload} GB
* 下载流量：{download} GB
* 剩余流量：{remaining} GB{possible_predict}
---
## 图表
![{hosturl}]({hosturl}/get_traffic_chart)
"""
predict_str = r"""
---
## 指数平滑流量预测（最后一天）
* 剩余流量预测：{mean:.2f} GB
* 置信上限：{upper:.2f} GB
* 置信下限：{lower:.2f} GB"""


def get_now():
    now = datetime.now()
    year = now.year
    month = now.month
    if now.day < RESET_DATE:
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return year, month


def gen_text():
    year, month = get_now()
    begin, end = get_period(year, month)
    is_need_predict = end - datetime.now() > timedelta(days=1)
    days = (end - datetime.now()).days
    df, last_record = get_remaining_dataframe(year, month)
    predicted = None
    if is_need_predict:
        predicted = get_predict(df)
    title = title_str.format(remaining=last_record[3], days=days)
    possible_predict = ""
    if predicted is not None:
        s = "，"
        last = predicted.tail(1).values[0]
        mean = last[0]
        upper = last[2]
        lower = last[1]
        if upper < 0:
            s += "流量用尽危险"
        elif mean < 0:
            s += "流量可能用尽"
        elif lower < 0:
            s += "流量可能触底"
        else:
            s += "流量余量安全"
        title += s
        possible_predict = predict_str.format(mean=mean, upper=upper, lower=lower)

    context = context_str.format(upload=last_record[1], download=last_record[2], remaining=last_record[3],
                                 possible_predict=possible_predict, hosturl=HOST_URL)
    return title, context


def push_to_serverchan(title, context):
    data = {
        'title': title,
        'desp': context
    }
    req = urllib.request.Request(url=SERVERCHAN_URL, data=urlencode(data).encode('utf-8'), method='POST')
    res = urllib.request.urlopen(req)


def main():
    title, context = gen_text()
    push_to_serverchan(title, context)


if __name__ == '__main__':
    main()
