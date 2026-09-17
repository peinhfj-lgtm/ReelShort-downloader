import asyncio
import inspect
import json
import os
import re
import requests

from datetime import datetime
import random

import asyncio
import ssl


def get_value_from_path(data, path):
    current = data
    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current

class ReelShortError(Exception):
    def __init__(self, message, book_id=None):
        self.message = message
        self.book_id = book_id

        frame = inspect.currentframe().f_back
        self.location = f"{os.path.basename(frame.f_code.co_filename)}:{frame.f_lineno}"
        self.location = f"{frame.f_lineno}"

        super().__init__(self._format_message())

    def _format_message(self):
        if self.book_id is not None:
            base = f"[eposide ID: {self.book_id}] {self.message}"
        else:
            base = self.message
        return f"{base} (location: {self.location})"


class ReelShortDownload:
    def __init__(self, url: str = None, dir_name: str = None):
        self.book_pic = None
        self.name = None
        self.episode = None
        self.episodes_list = []
        self.url = url
        self.title = dir_name

        illegal_chars = r'[<>:"/\\|?*]'
        safe_name = re.sub(illegal_chars, '_', dir_name)
        safe_name = safe_name.strip('. ')
        self.dir_name = safe_name if safe_name is not None else "tmp"

        self.get_episodes()

    def get_episodes(self):
        if self.url is None or self.url == '':
            raise ReelShortError("empty", self.url)
        try:
            response = requests.get(self.url)
            if response.status_code == 200:
                try:
                    data = response.text
                    pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
                    pattern1 = r'<script type="application/ld+json">([\s\S]*?)</script>'
                    pattern1 = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>'
                    match = re.search(pattern, data, re.DOTALL)
                    match1 = re.search(pattern1, data, re.DOTALL)
                    if match and match1:
                        json_str = match.group(1)
                        json_str1 = match1.group(1)
                        try:
                            tmp_data = json.loads(json_str)
                            self.book_pic = tmp_data["props"]["pageProps"]["data"]["book_pic"]
                            for chap in tmp_data["props"]["pageProps"]["data"]["online_base"]:
                                if chap['serial_number'] == 0:
                                    continue    
                                self.episodes_list.append(chap["chapter_id"])
                            tmp_data1 = json.loads(json_str1)
                            try:
                                self.name = tmp_data1["name"]
                            except Exception as e:
                                try:
                                    self.name = tmp_data1[0]["name"]
                                except Exception as e:
                                    self.name =tmp_data1['@graph'][0]['name']
                        except json.JSONDecodeError as e:
                            print("JSON parse error:", e)
                    else:
                        pass
                    pass
                except Exception as e:
                    raise ReelShortError(f"ERROR_1, code： {e}", self.url)
        except Exception as e:
            raise ReelShortError(f"ERROR_2, code： {e}", self.url)

    def download_episodes(self):
        dir_name = BASE_PATH_VIDEOS / 'ReelShort' / self.dir_name
        os.makedirs(dir_name, exist_ok=True)
        asyncio.run(run(self.episodes_list, dir_name))

        # process_videos_async(dir_name, title=self.title, max_workers=4)  


async def run(episodes_list, dir_name):
    await download_all_async(episodes_list, dir_name, max_concurrent=10)


def main(url, dir_=None):
    url = clean_reel_short_url(url)
    p_downloader = ReelShortDownload(url=url, dir_name=dir_)
    p_downloader.download_episodes()
    p_list = p_downloader.episodes_list
    return p_downloader.book_pic

def clean_reel_short_url(url):
    decoded_url = url.replace('/episodes/', '/movie/')
    if '?' in decoded_url and '-' in decoded_url:
        parts = decoded_url.rsplit('-', 1)
        decoded_url = parts[0]
    return decoded_url
  

    

