# -*- coding: utf-8 -*-
{
    'name': "GOODERP 非营利组织出纳模块",
    'author': "xuan@osbzr.com",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description":
    '''
                            该模块实现了 GoodERP 中 非营利组织出纳 的功能。
    ''',
    'version': '11.11',
    'depends': ['finance',],
    'data': [
        #'security/groups.xml',
        'views/nonprofit_money_order_view.xml',
        'data/mony_flow_data.xml',
    ],
    'demo': [
        'demo/money_demo.xml',
    ],
}
