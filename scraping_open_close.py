from pyquery import PyQuery as pq
from logging import getLogger, DEBUG, StreamHandler
from urllib.parse import urlencode
import time

# ログ出力用: 今回程度の用途ならprintでもよい
logger = getLogger(__file__)
logger.addHandler(StreamHandler())
logger.setLevel(DEBUG)

# 飲食店の一覧
list_url = 'http://kaiten-heiten.com/category/restaurant/'


def parse_service():
    """
    各一覧ページ(1ページ目, 2ページ目, ...)ごとにparse_list_pageでデータを取得する
    :return: お店データのリスト
    """
    query_string = urlencode({'s': '【開店】'})
    base_page_url = list_url + 'page/%d/?'
    index = 1
    restaurant_list = []
    while True:
        logger.debug('scraping page: %d' % index)
        next_url = (base_page_url % index) + query_string
        page_restaurant_list = parse_list_page(next_url)
        index += 1

        time.sleep(1)

        # parse_list_pageがレストランを返さない = 終端に達したら抜ける
        if len(page_restaurant_list) == 0:
            break

    return restaurant_list


def parse_list_page(list_page_url: str):
    """
    お店一覧のページから、各お店の情報を取得する
    :param list_page_url:
    :return: お店データのリスト (なければ空の配列)
    """
    dom = pq(list_page_url)
    main_row = pq(dom.find('div.mainarea'))
    for link in main_row.find('a.post_links'):
        restaurant_url = pq(link).attr('href')
        restaurant_info = parse_restaurant_page(restaurant_url)
        time.sleep(1)

    return []


def parse_restaurant_page(restaurant_url: str):
    """
    お店ページから、お店情報を取得
    :param restaurant_url:
    :return: お店データ
    """
    logger.debug('scraping: %s' % restaurant_url)
    dom = pq(restaurant_url)
    title = dom.find('h1.entry-title').text()
    logger.debug('title: %s' % title)

    return {}


if __name__ == '__main__':
    parse_service()
