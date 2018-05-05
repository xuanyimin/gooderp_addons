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
    _description = u'日记账明细'

    cash_flow_template_id = fields.Many2one(
        'cash.flow.template', string=u'现金流量表项目')

    @api.onchange('category_id')
    def onchange_category_id(self):
        '''当类别发生变化时，带出现金流量表项'''
        if self.category_id:
            self.cash_flow_template_id = self.category_id.cash_flow_template_id

class OtherMoneyOrder(models.Model):
    _inherit = 'other.money.order'

    @api.multi
    def write(self, vals):
        res = super(OtherMoneyOrder, self).write(vals)
        # 如果没有现金流量表项则报错
        if self.is_init:
            pass
        else:
            for line in self.line_ids:
                if not line.category_id.cash_flow_template_id:
                    raise UserError(u'请到类型%s设置现金流量表项' % self.category_id.name)
                line.write({'cash_flow_template_id': line.category_id.cash_flow_template_id.id})
                return res