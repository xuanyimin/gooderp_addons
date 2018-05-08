# -*- coding: utf-8 -*-
{
    'name': "GOODERP 非营利组织模块",
    'author': "",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    'summary': 'GoodERP非营利组织解决方案包',
    "description":
    '''
                            该模块实现了非营利组织的功能。
    ''',
    'version': '11.11',
    'depends': ['keep_good','auto_exchange'],
    'data': [
        'views/nonprofit_money_order_view.xml',
        'views/inout_activities_view.xml',
        'security/groups_ccb.xml',
        'data/inout_activities_template.xml',
    ],
    'demo': [],
    'application': True,
}

