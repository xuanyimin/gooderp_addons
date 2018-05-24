
# {
#   'name':'Tutorial theme',
#   'description': 'A description for your theme.',
#   'version':'1.0',
#   'author':'Your name',
#
#  'data': [
#      'views/budget.xml',
#      'views/budget_conf.xml',
#  ],
#   'category': 'Theme/Creative',
#   'depends': ['website', 'website_blog', 'sale'],
# }
# -*- coding: utf-8 -*-
{
    'name': "预算模块",
    'author': "JOB",
    'website': "http://www.osbzr.com",
    'category': 'gooderp',
    "description":'预算模块描述',
    'depends': ['core', 'finance'],
    'version': '11.11',
    'data': [
      # 'views/budget.xml',
      # 'action/budget_action.xml',
      # 'views/budget_conf.xml',
      'data/budget_export_template_data.xml',
      'data/budget_data.xml',
      'views/view_budget.xml',



    ],
    'application': True,
    'active': False,
}
