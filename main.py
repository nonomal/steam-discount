#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : EXP
# -----------------------------------------------

import time
import random
import argparse
from pypdm.dbc._sqlite import SqliteDBC
from src.core.steam_crawler import SteamCrawler
from src.config import settings
from src.core import saver
from src.core import pager
from color_log.clog import log


GIT_CRAWL_PWD = "3uJtWFf4Vx1S2dSQXJCK"

def args() :
    parser = argparse.ArgumentParser(
        prog='', # 会被 usage 覆盖
        usage='Steam 特惠游戏榜单 - 帮助信息',  
        description='从商城爬取游戏的【打折】【零元购】【测评】【热度】情况的榜单整理并展示',  
        epilog='\r\n'.join([
            '无代理: ', 
            '  python main.py -p 10 -l 500', 
            '有代理: ', 
            '  python main.py -p 10 -l 500 -c "127.0.0.1:18888"', 
        ])
    )
    parser.add_argument('-g', '--git', dest='git', type=str, default=GIT_CRAWL_PWD, help='Github Action 的启动密码（避免被 Fork 时别人可以直接运行，导致目标站点被 DDos）')
    parser.add_argument('-c', '--proxy', dest='proxy', type=str, default="", help='HTTP 代理服务，如 127.0.0.1:18888')
    parser.add_argument('-p', '--pages', dest='pages', type=int, default=10, help='爬取 steam 商城的游戏页数')
    parser.add_argument('-z', '--zone', dest='zone', type=str, default='CN', help='指定 steam 商城的地区，会影响售价单位')
    parser.add_argument('-s', '--specials', dest='specials', action='store_true', default=False, help='是否只爬取正在打折的游戏')
    parser.add_argument('-f', '--filter', dest='filter', type=str, default='globaltopsellers', help='其他过滤参数')
    parser.add_argument('-l', '--limit', dest='limit', type=int, default=500, help='最终界面展示的游戏数量')
    return parser.parse_args()


def get_args(args) :
    if args.git != GIT_CRAWL_PWD :
        # Github Action 调用了 -g 参数，若仓库没有设置 secrets.CRAWL_PWD 会赋予为空值
        # 导致验证 Github Action 的 secrets.CRAWL_PWD 失败，爬虫进程终止执行
        # 目的是在仓库被 Fork 时，可以保护目标站点不被 DDos
        exit(0)

    proxy_svc = f'http://{args.proxy}'
    proxy = { "http": proxy_svc, "https": proxy_svc } if args.proxy else {}

    zone = args.zone or settings.steam['zone']
    specials = args.specials or settings.steam['specials']
    filter = args.filter or settings.steam['filter']
    pages = args.pages or settings.crawler['pages']
    limit = args.limit or settings.crawler['limit']
    return [ proxy, pages, zone, specials, filter, limit ]



def main(proxy, pages, zone, specials, filter, limit) :
    log.info('+++++++++++++++++++++++++++++++++++++++')
    # update_rank(proxy)                                          # 更新游戏排名
    update_top_discount(proxy, pages, zone, specials, filter)   # 更新销售 top 的游戏的折扣信息
    update_random_discount(proxy, zone)         # 更新随机游戏的折扣信息（主要为了扩充数据库）
    pager.to_page(limit)
    log.info('---------------------------------------')


def update_rank(proxy) :
    try :
        sc = SteamCrawler(settings.steam['game_stats_url'], proxy=proxy)

        log.info('正在抓取游戏排名数据 ...')
        html = sc.get_html()
        tsgs = sc.parse_rank(html)

        log.info('正在更新游戏排名数据 ...')
        saver.to_db(tsgs, True, False)
    except :
        log.error('更新游戏排名数据失败')


def update_top_discount(proxy, pages, zone, specials, filter) :
    for page in range(1, pages + 1) :
        _update_discount(proxy, page, zone, specials, filter)
        time.sleep(5)


def update_random_discount(proxy, zone) :
    for cnt in range(1, 10) :
        page = random.randint(1, settings.steam['total_pages'])
        _update_discount(proxy, page, zone, False, '')


def _update_discount(proxy, page, zone, specials, filter) :
    try :
        sc = SteamCrawler(settings.steam['game_price_url'], page, proxy, options={
            'cc': zone,
            'specials': 1 if specials else 0,
            'filter': filter
        })

        log.info('正在抓取第 [%i] 页的游戏数据 ...' % page)
        html = sc.get_html()
        tsgs = sc.parse_game(html)

        log.info('正在更新第 [%i] 页的游戏数据 ...' % page)
        saver.to_db(tsgs, False, True)
    except :
        log.error('更新第 [%i] 页的游戏数据失败' % page)


def init() :
    sdbc = SqliteDBC(options=settings.database)
    sdbc.exec_script(settings.database['sqlpath'])



if __name__ == "__main__" :
    init()
    main(*get_args(args()))
