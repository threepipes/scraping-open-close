from pyquery import PyQuery as pq
from logging import getLogger, DEBUG, INFO, StreamHandler
from urllib.parse import urlencode
import time
import re

# ログ出力用: 今回程度の用途ならprintでもよい
logger = getLogger(__file__)
logger.addHandler(StreamHandler())
logger.setLevel(INFO)

# 飲食店の一覧
list_url = 'http://kaiten-heiten.com/category/restaurant/'


def parse_service():
    """
    各一覧ページ(1ページ目, 2ページ目, ...)ごとにparse_list_pageでデータを取得し
    ページが完了する度にcsvへの追記を行う
    :return: お店データのリスト
    """
    query_string = urlencode({'s': '【開店】'})
    base_page_url = list_url + 'page/%d/?'
    index = 1

    with open('column_list.csv') as f:
        column_list = [row.strip() for row in f]

    with open('attack_list.csv', 'w') as f:
        f.write(','.join(column_list) + '\n')

        while True:
            logger.info('scraping page: %d' % index)
            next_url = (base_page_url % index) + query_string
            page_restaurant_list = parse_list_page(next_url)
            index += 1
            time.sleep(1)

            # parse_list_pageがレストランを返さない = 終端に達したら抜ける
            if len(page_restaurant_list) == 0:
                break

            for restaurant in page_restaurant_list:
                row = [restaurant.get(col, '') for col in column_list]
                f.write(','.join(row).replace('\n', ' ') + '\n')
                f.flush()


def parse_list_page(list_page_url: str):
    """
    お店一覧のページから、各お店の情報を取得する
    :param list_page_url: お店一覧ページのurl
    :return: お店データのリスト (なければ空の配列)
    """
    dom = pq(list_page_url)
    main_row = pq(dom.find('div.mainarea'))
    restaurant_list = []

    for link in main_row.find('a.post_links'):
        restaurant_url = pq(link).attr('href')
        restaurant_info = parse_restaurant_page(restaurant_url)
        restaurant_list.append(restaurant_info)
        logger.debug(restaurant_info)
        time.sleep(1)

    return restaurant_list


def parse_restaurant_page(restaurant_url: str):
    """
    お店ページから、お店情報を取得
    :param restaurant_url: お店url
    :return: お店データ
    """
    logger.debug('scraping: %s' % restaurant_url)
    dom = pq(restaurant_url)
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


def get_table_data(table_dom: pq):
    """

    :param table_dom:
    :return:
    """
    table_data = {}
    for row in table_dom.find('tr'):
        row_dom = pq(row)
        row_data = []
        for col in row_dom.find('td'):
            col_dom = pq(col)
            inner_link = col_dom.find('a')
            if inner_link and 'tel:' not in inner_link.attr('href'):
                row_data.append(inner_link.attr('href'))
            else:
                row_data.append(pq(col).text())
        if len(row_data) != 2:
            logger.debug('wrong num on table row: ' + str(row_dom))
            continue
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
    parse_service()
