# encoding:utf-8
# 蓝奏云上传文件
# Author: https://github.com/celetor
# Date: 2023-12-16

import logging
import os
import sys
import time
import requests

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 日志设置
logger = logging.getLogger('lanzou-api')
logger.setLevel(logging.DEBUG)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter(
    fmt="%(asctime)s [line:%(lineno)d] %(funcName)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(console)


def retry(times=3, interval=10):
    def decorator(func):
        def wrapper(*args, **kwargs):
            retry_time = 0
            while retry_time < times:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retry_time += 1
                    logger.warning(f'第{retry_time}次重试,{e}')
                    time.sleep(interval)
            return func(*args, **kwargs)

        return wrapper

    return decorator


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://pc.woozooo.com/account.php?action=login'
}

cookie = {
    # Cookie 中 ylogin 的值
    'ylogin': os.environ.get('ylogin'),
    # Cookie 中 phpdisk_info 的值
    'phpdisk_info': os.environ.get('phpdisk_info')
}


# 检查是否已登录
def login_by_cookie():
    url_account = "https://pc.woozooo.com/account.php"
    if cookie['phpdisk_info'] is None:
        logger.error('请指定 Cookie 中 phpdisk_info 的值！')
    if cookie['ylogin'] is None:
        logger.error('ERROR: 请指定 Cookie 中 ylogin 的值！')
    res = requests.get(url_account, headers=headers, cookies=cookie, verify=False)
    if '网盘用户登录' in res.text:
        logger.error('ERROR: 登录失败,请更新Cookie')
    else:
        logger.info('登录成功')
        return True
    return False


def set_desc(fid, desc):
    post_data = {'task': 11, 'file_id': fid, 'desc': desc}
    try:
        response = requests.post('https://pc.woozooo.com/doupload.php',
                                 data=post_data, headers=headers, cookies=cookie, verify=False)
        res = response.json()
        logger.info(f"文件描述设置结果 -> {res['info']}")
    except Exception as e:
        logger.error(f"文件描述设置异常 -> {e}")


# 上传文件
@retry(times=3, interval=15)
def upload_file(file_dir, folder_id, description):
    if os.path.getsize(file_dir) > 100 * 1048576:
        logger.warning(f"{file_dir} -> 文件大于100M,不上传")
        return

    file_name = os.path.basename(file_dir)
    upload_url = f"https://up.woozooo.com/fileup.php?uid={cookie['ylogin']}"
    headers['Referer'] = f"https://up.woozooo.com/mydisk.php?item=files&action=index&u={cookie['ylogin']}"
    post_data = {
        "task": "1",
        "vie": "2",
        "ve": "2",
        "id": "WU_FILE_0",
        "folder_id_bb_n": f'{folder_id}',
        "name": file_name,
    }
    files = {'upload_file': (file_name, open(file_dir, "rb"), 'application/octet-stream')}

    response = requests.post(upload_url, data=post_data, files=files,
                             headers=headers, cookies=cookie, verify=False, timeout=3600)
    res = response.json()
    logger.info(f"{file_dir} -> {res['info']}")
    if res['zt'] == 1:
        if description is not None:
            set_desc(int(res["text"][0]["id"]), description)


# 上传文件夹内的文件
def upload_folder(folder_dir, folder_id, description):
    file_list = sorted(os.listdir(folder_dir), reverse=True)
    for file in file_list:
        path = os.path.join(folder_dir, file)
        if os.path.isfile(path):
            upload_file(path, folder_id, description)
        else:
            upload_folder(path, folder_id, description)


# 上传
def upload(dir, folder_id, description=None):
    if dir is None:
        logger.error('请指定上传的文件路径')
        return
    if folder_id is None:
        logger.error('请指定蓝奏云的文件夹id')
        return
    if os.path.isfile(dir):
        upload_file(dir, str(folder_id), description)
    else:
        upload_folder(dir, str(folder_id), description)


if __name__ == '__main__':
    argv = sys.argv[1:]
    if len(argv) < 2:
        logger.error('参数错误,请以这种格式重新尝试\npython lanzou-api.py 需上传的路径 蓝奏云文件夹id 描述文件路径')
    # 需上传的路径
    upload_path = argv[0]
    # 蓝奏云文件夹id
    lzy_folder_id = argv[1]
    desc = None
    if len(argv) > 2:
        # 描述文件路径
        desc_path = argv[2]
        try:
            with open(desc_path, 'r', encoding='utf-8') as f:
                desc = f.read()
        except Exception as e:
            logger.error(f"描述文件读取异常 -> {e}")

    if login_by_cookie():
        upload(upload_path, lzy_folder_id, desc)
