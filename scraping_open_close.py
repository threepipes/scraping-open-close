from pyquery import PyQuery as pq
from logging import getLogger, DEBUG, INFO, StreamHandler
from urllib.parse import urlencode
from tinydb import TinyDB, Query
import traceback
import datetime
import sys
import time
import re
import json
import os

SLEEP_INTERVAL_SEC = 3.0

# ログ出力用: 今回程度の用途ならprintでもよい
logger = getLogger(__file__)
logger.addHandler(StreamHandler())
logger.setLevel(DEBUG)

# 飲食店の一覧
list_url = 'https://kaiten-heiten.com/category/restaurant/'
Restaurant = Query()
output_dir = './output/'


def update_db(db: TinyDB, key: str, value):
    old = db.search(Restaurant.key == key)
    if old:
        db.update(value, Restaurant.key == key)
    else:
        db.insert({'key': key, 'value': value})


def pq_with_retry(url: str) -> pq:
    for _ in range(3):
        try:
            return pq(url)
        except:
            logger.warning(traceback.format_exc())
            logger.warning('failed to get. retrying...')
            time.sleep(30)
    logger.error('failed to get dom from: ' + url)
    return None


def parse_service(begin_index=1, end_index=-1, query='【閉店】'):
    """
    各一覧ページ(1ページ目, 2ページ目, ...)ごとにparse_list_pageでデータを取得し
    ページが完了する度にcsvへの追記を行う
    :return: お店データのリスト
    """
    db = TinyDB('history.json')
    last = db.search(Restaurant.key == query)
    logger.debug('previous last: ' + json.dumps(last))
    query_string = urlencode({'s': query})
    base_page_url = list_url + 'page/%d/?'
    index = begin_index
    if end_index < begin_index:
        end_index = 100000000000
        if last:
            last = last[0].get('value', {}).get('URL', '')

    with open('column_list.csv') as f:
        column_list = [row.strip() for row in f]

    if index == 1:
        open_mode = 'w'
    else:
        open_mode = 'a'

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M')
    filename = output_dir + f'attack_list_{timestamp}.csv'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(filename, open_mode) as f:
        if open_mode == 'w':
            f.write(','.join(column_list) + '\n')

        while True:
            logger.info('scraping page: %d' % index)
            next_url = (base_page_url % index) + query_string
            has_restaurant = False

            for restaurant in parse_list_page(next_url):
                has_restaurant = True
                row = [restaurant.get(col, '').replace(',', '、') for col in column_list]
                if restaurant['URL'] == last:
                    has_restaurant = False
                    break
                f.write(','.join(row).replace('\n', ' / ') + '\n')
                if index == begin_index:
                    update_db(db, query, restaurant)
            f.flush()

            index += 1
            time.sleep(SLEEP_INTERVAL_SEC)

            # parse_list_pageがレストランを返さない = 終端に達したら抜ける
            if not has_restaurant or index > end_index:
                break


def parse_list_page(list_page_url: str):
    """
    お店一覧のページから、各お店の情報を取得する
    :param list_page_url: お店一覧ページのurl
    :return: お店データのリスト (なければ空の配列)
    """
    dom = pq(list_page_url)
    main_row = pq(dom.find('div.mainarea'))

    for link in main_row.find('a.post_links'):
        restaurant_url = pq(link).attr('href')
        restaurant_info = parse_restaurant_page(restaurant_url)
        if not restaurant_info:
            continue
        logger.debug(restaurant_info)
        time.sleep(SLEEP_INTERVAL_SEC)
        yield restaurant_info


def parse_restaurant_page(restaurant_url: str):
    """
    お店ページから、お店情報を取得
    :param restaurant_url: お店url
    :return: お店データ
    """
    logger.debug('scraping: %s' % restaurant_url)
    dom = pq_with_retry(restaurant_url)
    if not dom:
        return
    title = dom.find('h1.entry-title').text()
    logger.info('restaurant: %s' % title)

    metadata_dom = pq(dom.find('div.post_meta'))
    category = get_category(metadata_dom)  # ジャンル取得
    update_date = get_update_date(metadata_dom)  # 更新日取得
    open_date = get_open_date(pq(dom.find('div.post_body > h3')))  # 開店日取得
    table_data = get_table_data(pq(dom.find('table#address')))

    table_data.update({
        '店名': title,
        'ジャンル': category,
        '更新日': update_date,
        '開店日': open_date,
        'URL': restaurant_url,
    })

    return table_data


def have_restaurant_url(inner_link):
    return inner_link and len(inner_link) == 1 and inner_link.attr('href') and 'tel:' not in inner_link.attr('href')


def get_table_data(table_dom: pq):
    """
    お店の情報表からデータを取得する
    :param table_dom: 表
    :return: 表の内容のdict
    """
    table_data = {}
    for row in table_dom.find('tr'):
        row_dom = pq(row)
        row_data = []
        for col in row_dom.find('td'):
            col_dom = pq(col)
            inner_link = col_dom.find('a')
            # お店URLの場合だけ、hrefから取得するので場合分け
            if have_restaurant_url(inner_link):
                row_data.append(inner_link.attr('href'))
            else:
                row_data.append(pq(col).text())
        if len(row_data) != 2:
            logger.debug('wrong num on table row: ' + str(row_dom))
            continue
        # 住所の場合は郵便番号を切り出す
        if row_data[0] == '住所':
            postal_code_match = re.search(r'〒\d{3}-\d{4}', row_data[1])
            if postal_code_match:
                postal_code = postal_code_match.group()
                table_data['郵便番号'] = postal_code
                row_data[1] = row_data[1].replace(postal_code, '')

        table_data[row_data[0]] = row_data[1]
    return table_data


def get_open_date(title_dom: pq):
    """
    お店の開店日を取得する
    現在は X年X月X日 の形式で書かれている場合のみ取得可能
    :param title_dom: 開店日を含むタイトル
    :return: 開店日
    """
    try:
        text = title_dom.text()
        date = re.search(r'\d+年\d+月\d+日', text)
        return date.group()
    except Exception as e:
        logger.error('開店日を取得できませんでした')
        logger.debug(e)

    return ''


def get_category(attr_dom: pq):
    """
    お店のジャンルを取得する
    ジャンルはラベル付けされていないので、URLを見てそれっぽいものを探す
    :param attr_dom: お店属性一覧のタグ
    :return: お店ジャンル
    """
    category_url_pattern = list_url + r'[^/]+/'
    for candidate in attr_dom.find("a[rel='category tag']"):
        cand_dom = pq(candidate)
        url = cand_dom.attr('href')
        if url and re.match(category_url_pattern, url):
            return cand_dom.text()

    return ''


def get_update_date(attr_dom: pq):
    """
    お店情報の更新日を取得する
    :param attr_dom: お店属性一覧のタグ
    :return: 更新日
    """
    date_dom = attr_dom.find('span.post_time > i')
    if not date_dom:
        return ''
    return pq(date_dom).attr('title')


if __name__ == '__main__':
    args = sys.argv
    begin_index = 1
    end_index = -1
    if len(args) >= 2:
        begin_index = int(args[1])
    if len(args) >= 3:
        end_index = int(args[2])
    logger.info(f'page: from {begin_index} to {end_index}')
    parse_service(begin_index, end_index)
