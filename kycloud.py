import re
import sqlite3
import time
import urllib.request
from datetime import datetime

from config import *

TABLE_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS `kycloud` (
	id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	time DATETIME NOT NULL UNIQUE,
	upload REAL NOT NULL, /* in GB like below */
	download REAL NOT NULL,
	remaining REAL NOT NULL
);
"""
INSERT_SQL = """
INSERT INTO `kycloud` (time, upload, download, remaining) VALUES (?, ?, ?, ?);
"""


def migrate(conn: sqlite3.dbapi2):
    cur = conn.cursor()
    # log_file = r"D:\Shiroko\Desktop\kycloud.log"
    with open(log_file, 'r', encoding='UTF-8') as f:
        for line in f.readlines():
            line = line.strip().split(',')
            if len(line) != 5:
                continue
            time = line[0].replace(r'/', '-')
            upload = float(line[1].replace(' GB', ''))
            download = float(line[2].replace(' GB', ''))
            remaining = float(line[4].replace(' GB', ''))
            cur.execute(INSERT_SQL, (time, upload, download, remaining))
    cur.close()
    conn.commit()


# Return: time, upload, download, remaining
# def fetcher() -> tuple[str, float, float, float]:
def fetcher():
    resp = urllib.request.urlopen(FETCH_URL)
    result = resp.readlines()[0].decode('UTF-8')
    result = list(map(lambda x: int(x), re.findall(r"upload=(\d*?);.*download=(\d*?);", result)[0]))
    upload = round(result[0] / 1024 / 1024 / 1024, 2)
    download = round(result[1] / 1024 / 1024 / 1024, 2)
    remaining = round((TOTAL_AVAIL * 1024 * 1024 * 1024 - result[0] - result[1]) / 1024 / 1024 / 1024, 2)
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return time, upload, download, remaining


def main():
    result = ()
    for i in range(0, 3):
        try:
            result = fetcher()
        except:
            time.sleep(5)
        else:
            break
    if result == ():
        exit(-1)

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(TABLE_CREATE_SQL)
        cur.close()
        conn.commit()
        if False:
            migrate(conn)
            conn.commit()
            exit()
        print(f"Result to be inserted: {result}")
        cur = conn.cursor()
        cur.execute(INSERT_SQL, result)
        cur.close()
        conn.commit()


if __name__ == '__main__':
    main()
