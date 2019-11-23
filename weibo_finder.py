import math
import random
import sys
import traceback
from collections import OrderedDict
from datetime import datetime, timedelta
from time import sleep

import requests
from lxml import etree


class Weibo:
    def __init__(self, user_id, since_date):
        if user_id:
            self.user_id = user_id
        else:
            self.user_id = ''
        if since_date:
            self.since_date = since_date
        else:
            self.since_date = '1900-01-01'
        self.user = {}
        self.got_count = 0
        self.weibo_id_list = []
        self.base_url = 'https://m.weibo.cn/api/container/getIndex?'
        self.weibo = []

    def get_json(self, params):
        url = self.base_url
        r = requests.get(url, params=params)
        return r.json()

    def get_weibo_json(self, page):
        params = {'containerid': '107603' + str(self.user_id), 'page': page}
        js = self.get_json(params)
        return js

    def get_info_json(self):
        params = {'containerid': '100505' + str(self.user_id)}
        js = self.get_json(params)
        return js

    def standardize_info(self, weibo):
        for k, v in weibo.items():
            if 'int' not in str(type(v)) and 'long' not in str(
                    type(v)) and 'bool' not in str(type(v)):
                weibo[k] = v.replace(u"\u200b", "").encode(
                    sys.stdout.encoding, "ignore").decode(sys.stdout.encoding)
        return weibo

    def get_page_count(self):
        weibo_count = self.user['statuses_count']
        page_count = int(math.ceil(weibo_count / 10.0))
        return page_count

    def get_user_info(self):
        json_got = self.get_info_json()
        if json_got['ok']:
            info = json_got['data']['userInfo']
            user_info = {}
            user_info['id'] = self.user_id
            user_info['followers_count'] = info.get('followers_count', 0)
            user_info['statuses_count'] = info.get('statuses_count', 0)
            user = self.standardize_info(user_info)
            self.user = user
            return user
        else:
            return None

    def print_user_info(self):
        print(u'用户id：%s' % self.user['id'])
        print(u'微博数：%d' % self.user['statuses_count'])
        print(u'粉丝数：%d' % self.user['followers_count'])

    def string_to_int(self, string):
        if isinstance(string, int):
            return string
        elif string.endswith(u'万+'):
            string = int(string[:-2] + '0000')
        elif string.endswith(u'万'):
            string = int(string[:-1] + '0000')
        return int(string)

    def parse_weibo(self, weibo_info):
        weibo = OrderedDict()
        if weibo_info['user']:
            weibo['user_id'] = weibo_info['user']['id']
            weibo['screen_name'] = weibo_info['user']['screen_name']
        else:
            weibo['user_id'] = ''
            weibo['screen_name'] = ''
        weibo['id'] = int(weibo_info['id'])
        weibo['bid'] = weibo_info['bid']
        text_body = weibo_info['text']
        selector = etree.HTML(text_body)
        weibo['text'] = etree.HTML(text_body).xpath('string(.)')
        weibo['created_at'] = weibo_info['created_at']
        weibo['source'] = weibo_info['source']
        weibo['attitudes_count'] = self.string_to_int(
            weibo_info['attitudes_count'])
        weibo['comments_count'] = self.string_to_int(
            weibo_info['comments_count'])
        weibo['reposts_count'] = self.string_to_int(
            weibo_info['reposts_count'])
        return self.standardize_info(weibo)

    def standardize_date(self, created_at):
        if u"刚刚" in created_at:
            created_at = datetime.now().strftime("%Y-%m-%d")
        elif u"分钟" in created_at:
            minute = created_at[:created_at.find(u"分钟")]
            minute = timedelta(minutes=int(minute))
            created_at = (datetime.now() - minute).strftime("%Y-%m-%d")
        elif u"小时" in created_at:
            hour = created_at[:created_at.find(u"小时")]
            hour = timedelta(hours=int(hour))
            created_at = (datetime.now() - hour).strftime("%Y-%m-%d")
        elif u"昨天" in created_at:
            day = timedelta(days=1)
            created_at = (datetime.now() - day).strftime("%Y-%m-%d")
        elif created_at.count('-') == 1:
            year = datetime.now().strftime("%Y")
            created_at = year + "-" + created_at
        return created_at

    def get_one_weibo(self, info):
        try:
            weibo_info = info['mblog']
            retweeted_status = weibo_info.get('retweeted_status')
            if not retweeted_status:
                weibo = self.parse_weibo(weibo_info)
            else:
                return OrderedDict()
            weibo['created_at'] = self.standardize_date(
                weibo_info['created_at'])
            return weibo
        except Exception as e:
            print("Error: ", e)
            traceback.print_exc()

    def print_weibo(self, weibo):
        print('-----------------')
        print(u'微博正文：%s' % weibo['text'])
        print(u'发布时间：%s' % weibo['created_at'])
        print(u'点赞数：%d' % weibo['attitudes_count'])
        print(u'评论数：%d' % weibo['comments_count'])
        print(u'转发数：%d' % weibo['reposts_count'])

    def is_pinned_weibo(self, info):
        weibo_info = info['mblog']
        title = weibo_info.get('title')
        if title and title.get('text') == u'置顶':
            return True
        else:
            return False

    def get_one_page(self, page):
        try:
            js = self.get_weibo_json(page)
            if js['ok']:
                weibo_body = js['data']['cards']
                for w in weibo_body:
                    if w['card_type'] == 9:
                        wb = self.get_one_weibo(w)
                        if wb:
                            if len(wb) <= 0:
                                continue
                            else:
                                if wb['id'] in self.weibo_id_list:
                                    continue
                                created_at = datetime.strptime(
                                    wb['created_at'], "%Y-%m-%d")
                                since_date = datetime.strptime(
                                    self.since_date, "%Y-%m-%d")
                                if created_at < since_date:
                                    if self.is_pinned_weibo(w):
                                        continue
                                    else:
                                        return True
                                if 'retweet' not in wb.keys():
                                    self.weibo.append(wb)
                                    self.weibo_id_list.append(wb['id'])
                                    self.got_count = self.got_count + 1
                                    self.print_weibo(wb)
        except Exception as e:
            print("Error: ", e)
            traceback.print_exc()

    def get_pages(self):
        self.get_user_info()
        self.print_user_info()
        page_count = self.get_page_count()
        page_pin = 0
        random_pages = random.randint(1, 5)
        for page in range(1, page_count + 1):
            is_end = self.get_one_page(page)
            if is_end:
                break
            if page - page_pin == random_pages and page < page_count:
                sleep(random.randint(6, 10))
                page_pin = page
                random_pages = random.randint(1, 5)


def main():
    now = datetime.now()
    target_date = now - timedelta(days=30)
    print('before', target_date.strftime("%Y-%m-%d"))
    # 5281889184  <->  炼金实验室ALCHEMLAB
    weibo = Weibo(user_id='5281889184',
                  since_date=target_date.strftime("%Y-%m-%d"))
    weibo.get_pages()


if __name__ == '__main__':
    main()
