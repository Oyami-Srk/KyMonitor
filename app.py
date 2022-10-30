import datetime
import io

from flask import Flask, Response, request, render_template

import analyze

app = Flask(__name__)


@app.route('/')
def index():  # put application's code here
    return render_template("index.html", dates=analyze.get_available_date())


@app.route('/get_traffic_chart')
def get_flow_chart():
    year = datetime.datetime.now().year
    month = datetime.datetime.now().month
    if request.args.get('year'):
        try:
            year = int(request.args.get('year'))
        except:
            raise Exception("Arg year invalid.")
    if request.args.get('month'):
        try:
            month = int(request.args.get('month'))
            if month < 1 or month > 12:
                raise Exception("Arg month invalid.")
        except:
            raise Exception("Arg month invalid.")

    plot, safe_level = analyze.do_all(year, month)
    output = io.BytesIO()
    plot.savefig(output, format='svg')
    return Response(output.getvalue(), mimetype='image/svg+xml')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=9955)
