# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016  开阖软件(<http://www.osbzr.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
from odoo import fields, models, api
from odoo.tools import float_compare

class OtherMoneyOrderLine(models.Model):
    _inherit ='other.money.order.line'
    _description = u'流水单明细'

    mony_flow = fields.Many2one('mony.flow', u'现金流量表项目', ondelete='restrict',
                              help=u'该笔收支对应现金流量表的项目')


class mony_flow(models.Model):
    ''' 是对其他收支业务的更细分类 '''
    _name = 'mony.flow'
    _description = u'收支项'

    SELECTION = [
        ('other_pay', u'支出'),
        ('other_get', u'收入'),
    ]

    type = fields.Selection(SELECTION, string=u'类型', readonly=True,
                            default=lambda self: self._context.get('type'),
                            states={'draft': [('readonly', False)]},
                            help=u'类型：收入 或者 支出')
    line_ids = fields.One2many('other.money.order.line', 'other_money_id',
                               string=u'收支单行', readonly=True,
                               copy=True,
                               states={'draft': [('readonly', False)]},
                               help=u'流水表明细行')

    name = fields.Char(u'名称', required=True)
    active = fields.Boolean(u'启用', default=True )
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())