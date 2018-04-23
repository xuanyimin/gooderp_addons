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

SELECTION = [
        ('other_pay', u'支出'),
        ('other_get', u'收入'),
    ]
class OtherMoneyOrderLine(models.Model):
    _inherit ='other.money.order.line'
    _description = u'流水单明细'

    cash_flow_template_ids = fields.Many2one(
        'cash.flow.template', string=u'现金流量表行')

    @api.onchange('category_id')
    def onchange_category_id(self):
        '''当类别发生变化时，带出现金流量表项'''
        if self.category_id:
            self.cash_flow_template_ids = self.category_id.cash_flow_template_ids

    @api.multi
    def write(self, vals):
        res = super(OtherMoneyOrderLine, self).write(vals)
        # 如果没有现金流量表项则报错
        if self.other_money_id.is_init:
            pass
        if not self.category_id.cash_flow_template_ids:
            raise UserError(u'请到类型%s设置现金流量表项'%self.category_id.name)
        return res

class mony_flow(models.Model):
    ''' 是对其他收支业务的更细分类 '''
    _name = 'mony.flow'
    _description = u'收支项'

    type = fields.Selection(SELECTION, u'类型',
                            default=lambda self: self._context.get('type'))
    name = fields.Char(u'名称', required=True)
    active = fields.Boolean(u'启用', default=True )
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())