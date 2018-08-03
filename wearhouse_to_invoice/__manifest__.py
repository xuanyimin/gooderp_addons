# -*- coding: utf-8 -*-
{
    'name': "GOODERP 税务模块-出库开票",
    'author': "德清武康开源软件工作室",
    'website': "无",
    'category': 'gooderp',
    "description":
    '''
                       模块为从出库单生成可用于导入的。
    ''',
    'version': '11.11',
    'depends': ['scm','cn_account_invoice'],
    'data': [
        'view/wearhouse_to_invoice_view.xml',
        'view/wearhouse_to_invoice_action.xml',
        'view/wearhouse_to_invoice_menu.xml',
        'data/wearhouse_to_invoice_data.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}
