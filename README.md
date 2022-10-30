# Kycloud Traffic Monitor & Analyzer

## Configuration
Edit `config.py` to fill with your configuration.
`FETCH_URL` is for fetch the traffic info from Kycloud.

Change `sid` to your service id. and `token` to your suscription token.

You can find it at your suscription info on your service page. (From `https://my.cloudnx.cc/clientarea.php`)

Then copy the suscription url and get `sid` and `token` from it.

## Usage
* Install requirements using `pip install -r requirements.txt`
* Run `kycloud.py` once per hour to fetch traffic info to database. (Using corntab or other task runner)
* Run `kynotify.py` at any time you like to push info to ServerChan. (You need register ServerChan first)
* Run `app.py` to start web-host service. By default it is listening to port `9955` at `127.0.0.1`, I recommand you to use nginx reverse proxy to public it.

## Note
I host this toolset on my Synology NAS. If you cannot install requirements from `requirements.txt` you can manually use pip install following package: `matplotlib`, `pandas`, `flask`, `statsmodels`