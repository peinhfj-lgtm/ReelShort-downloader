import asyncio
import inspect
import json
import os
import re
import requests
from download_ytdlp import download_with_ytdlp_async
from datetime import datetime
import random
from yt_dlp import YoutubeDL
import asyncio
import ssl

if getattr(sys, 'frozen', False):
    BASE_PATH = Path(sys.executable).parent
else:
    BASE_PATH = Path(__file__).parent.parent
BASE_PATH_DATA = BASE_PATH / 'data'
BASE_PATH_VIDEOS = BASE_PATH/ 'videos'

def get_value_from_path(data, path):
    current = data
    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current

async def download_with_ytdlp_async(url, file_name):
    delay = random.uniform(0.1, 1)
    await asyncio.sleep(delay)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    ydl_opts = {
        'outtmpl': file_name,
        'retries': 10,
        'fragment_retries': 10,
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'nocheckcertificate': True, 
        'legacyserverconnect': True,  
    }

    trys = 20
    while trys:
        try:
            ydl = YoutubeDL(ydl_opts)
            ydl.params['ssl_context'] = ssl_context
            await asyncio.to_thread(lambda: ydl.download([url]))
            return True

            # await asyncio.to_thread(lambda: YoutubeDL(ydl_opts).download([url]))
            # return True
        except Exception as e:
            print(f"❌ 下载失败, 正在重试 文件: {file_name}  错误: {e}")
            trys -= 1
            await asyncio.sleep(10)
    print(f"❌ 下载失败 20 次，请手动下载 文件: {file_name}, url: {url}")
    await asyncio.sleep(2)
    return False

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
            base = f"[剧集ID: {self.book_id}] {self.message}"
        else:
            base = self.message
        return f"{base} (位置: {self.location})"


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
            raise ReelShortError("剧集URL输入不能为空", self.url)
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
                            print("JSON解析失败:", e)
                    else:
                        print("未找到 __NEXT_DATA__ 标签")
                    pass
                except Exception as e:
                    raise ReelShortError(f"ERROR_1, 错误代码： {e}, 请联系技术人员", self.url)
        except Exception as e:
            raise ReelShortError(f"ERROR_2, 错误代码： {e}, 请联系技术人员", self.url)

    def download_episodes(self):
        dir_name = BASE_PATH_VIDEOS / 'ReelShort' / self.dir_name
        os.makedirs(dir_name, exist_ok=True)
        # print(f"   🖼️ 封面链接: {self.book_pic}\n")
        asyncio.run(run(self.episodes_list, dir_name))

        # process_videos_async(dir_name, title=self.title, max_workers=4)  # 4个并发


async def run(episodes_list, dir_name):
    await download_all_async(episodes_list, dir_name, max_concurrent=10)


async def download_all_async(episodes_list, dir_name, max_concurrent=5):
    """并发下载所有视频"""
    os.makedirs(dir_name, exist_ok=True)

    semaphore = asyncio.Semaphore(max_concurrent)

    async def download_with_semaphore(index, chapter_id):
        async with semaphore:
            download_url = f'https://www.reelshort.com/episodes/wo-shi-ni-die-693b8f146a2054699d00944d-{chapter_id}'
            file_name = f'{dir_name}/{str(index).zfill(3)}.mp4'
            print(f'📥 开始下载 [{index}/{len(episodes_list)}]')

            await download_with_ytdlp_async(download_url, file_name)

    tasks = []
    for index, chapter_id in enumerate(episodes_list, start=1):
        task = asyncio.create_task(
            download_with_semaphore(index, chapter_id)
        )
        tasks.append(task)

    await asyncio.gather(*tasks, return_exceptions=True)

    print("🎉 所有下载任务完成！")

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
  
def run_reel_short(book_id_):
    main(f'https://www.reelshort.com/episodes/trailer-find-your-way-back-to-me-my-childhood-sweetheart-{book_id}', book_id_)

if __name__ == "__main__":
    book_id = '69ab77dad2f2cfe8f2089395'
    run_reel_short(book_id)
    

