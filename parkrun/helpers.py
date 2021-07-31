import csv
import os
import random
from datetime import date, timedelta

import aiohttp

from utils import redis

PARKRUNS_FILE = os.path.join(os.path.dirname(__file__), 'all_parkruns.txt')
CLUBS_FILE = os.path.join(os.path.dirname(__file__), 'all_clubs.csv')

PARKRUNS = []
with open(PARKRUNS_FILE, 'r', newline='\n') as file:
    for line in file:
        PARKRUNS.append(line.strip())

CLUBS = []
with open(CLUBS_FILE, 'r', encoding='utf-8') as file:
    fieldnames = ['id', 'name', 'participants', 'runs', 'link']
    reader = csv.DictReader(file, fieldnames=fieldnames)
    for rec in reader:
        CLUBS.append(rec)

CLUBS.append({'id': '24630', 'name': 'ENGIRUNNERS', 'participants': '29', 'runs': '2157',
              'link': 'https://instagram.com/engirunners'})  # NOTE: personal order for D.Petrov


class ParkrunSite:
    __PARKRUN_HEADERS = [
        {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0"},
        {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/83.0.4103.61 Safari/537.36"},
        {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/89.0.4389.86 YaBrowser/21.3.0.740 Yowser/2.5 Safari/537.36"},
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/90.0.4430.85 Safari/537.36"},
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:77.0) Gecko/20100101 Firefox/77.0"},
        {"User-Agent": "Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16.2"},
        {"User-Agent": "Opera/9.80 (Macintosh; Intel Mac OS X 10.14.1) Presto/2.12.388 Version/12.16"}
    ]

    __PARKRUN_URL = {
        'largestclubs': 'https://www.parkrun.ru/results/largestclubs/',
        'courserecords': 'https://www.parkrun.ru/results/courserecords/'
    }

    def __init__(self, key=''):
        self.__key = key
        self.__redis_key = f'parkrun_{key}'
        self.headers = random.choice(ParkrunSite.__PARKRUN_HEADERS)

    @staticmethod
    def _compare_dates(date1: str, date2) -> bool:
        if not date1:
            return False
        date1 = date.fromisoformat(date1)
        date_sun = date2 if date2.isoweekday() == 7 else date2 - timedelta(date2.isoweekday())
        return date1 >= date_sun

    async def get_html(self, url=None):
        content = await redis.get_value(self.__redis_key)
        content_date = content.get('date', None)
        today = date.today()
        if ParkrunSite._compare_dates(content_date, today):
            return content['html']
        if not url:
            url = ParkrunSite.__PARKRUN_URL[self.__key]
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as resp:
                html = await resp.text()
        await redis.set_value(self.__redis_key, date=today.isoformat(), html=html)
        return html

    async def update_info(self, actual_date: str):
        """
        Method to set actual date of content. It is used to rewrite date of access to requested
        page that will be assign by default in get_html().
        """
        await redis.set_value(self.__redis_key, date=actual_date)


def min_to_mmss(m) -> str:
    mins = int(m)
    return f'{mins}:{round((m - mins) * 60):02d}'
