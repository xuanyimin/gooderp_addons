# -*- coding: utf-8 -*-
{
    'name': "GOODERP 税务模块-发票验证",
    'author': "德清武康开源软件工作室",
    'website': "无",
    'category': 'gooderp',
    "description":
    '''
                        该模块实现中国发票的验证。
    ''',
    'version': '11.11',
    'depends': ['base', 'core',  'tax'],
    'data': [
        'view/cn_invoice_verification_view.xml',
        #'view/tree_view_asset.xml',
    ],
    'demo': [
    ],
    'qweb': [
        #"static/src/xml/*.xml",
    ],
}
