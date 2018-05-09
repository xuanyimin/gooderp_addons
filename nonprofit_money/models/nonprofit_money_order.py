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

LINE_TYPES = [('get', u'销售收款'),
              ('pay', u'采购付款'),
              ('category', u'收支'),
              ('begin', u'科目期初'),
              ('end', u'科目期末'),
              ('lines', u'表行计算'),
              ('inopen_account', u'本期收入发生额'),
              ('outopen_account', u'本期支出发生额')]

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

class CoreCategory(models.Model):
    _inherit = 'core.category'
    inout_activities_template_id = fields.Many2one(
        'inout.activities.template', string=u'收支情况表项目')

class InoutActivitiesTemplate(models.Model):
    _name = 'inout.activities.template'
    _order = 'sequence'

    sequence = fields.Integer(u'序号')
    name = fields.Char(u'项目')
    line_type = fields.Selection(LINE_TYPES, u'行类型')
    # for type sum
    category_ids = fields.One2many('core.category', 'inout_activities_template_id', string=u'收支活动表类别',
                                copy=False, )
    # for type begin
    begin_ids = fields.Char(string=u'期初科目范围')
    # for type end
    end_ids = fields.Char(string=u'期末科目范围')
    # for type lines
    plus_ids = fields.Many2many(
        'inout.activities.template', 'activitiesc_p', 'activitiesc_id', 'activitiesp_id', string=u'+表行')
    nega_ids = fields.Many2many(
        'inout.activities.template', 'activitiesc_n', 'activitiesc_id', 'activitiesn_id', string=u'-表行')
    # for type
    d_account_ids = fields.Many2many('finance.account', string=u'借方累计会计科目')
    # for type begin
    c_account_ids = fields.Many2many('finance.account', string=u'贷方累计会计科目')


class InoutFlowStatement(models.Model):
    _name = 'inout.flow.statement'
    name = fields.Char(u'项目')
    sequence = fields.Char(u'行次')
    amount = fields.Float(u'本月数', digits=dp.get_precision('Amount'))