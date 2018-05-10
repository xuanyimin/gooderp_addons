# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import fields, models, api
import calendar


class InoutFlowWizard(models.TransientModel):
    _name = "inout.flow.wizard"

    def _default_period_id_impl(self):
        """
        默认是当前会计期间
        :return: 当前会计期间的对象
        """
        return self.env['finance.period'].get_date_now_period_id()

    @api.model
    def _default_period_id(self):

        return self._default_period_id_impl()

    period_id = fields.Many2one('finance.period', string=u'会计期间',
                                default=_default_period_id)

    @api.model
    def get_amount(self, tem, report_ids, period_id):
        '''
             [('get',u'销售收款'),
              ('pay',u'采购付款'),
              ('category',u'其他收支'),
              ('begin',u'科目期初'),
              ('end',u'科目期末'),
              ('lines',u'表行计算')
              ('in_account_ids',u'本期收入发生额'),
              ('out_account_ids',u'本期支出发生额')]
        '''
        date_start, date_end = self.env['finance.period'].get_period_month_date_range(
            period_id)
        ret = 0
        if tem.line_type == 'get' or tem.line_type == 'pay':
            # 收款单或付款单金额合计
            ret = sum([order.amount for order in self.env['money.order'].search([('type', '=', tem.line_type),
                                                                                 ('state',
                                                                                  '=', 'done'),
                                                                                 ('date', '>=',
                                                                                  date_start),
                                                                                 ('date', '<=', date_end)])])
        if tem.line_type == 'category':
            # 其他收支单金额合计
            ret = sum([line.amount for line in self.env['other.money.order.line'].search([('category_id', 'in', [c.id for c in tem.category_ids]),
                                                                                          ('other_money_id.state', '=', 'done'),
                                                                                          ('other_money_id.date', '>=', date_start),
                                                                                          ('other_money_id.date', '<=', date_end)])])
        if tem.line_type == 'begin':
            # 科目期初金额合计
            formula_list = tem.begin_ids.split('~')
            ret = 0
            if len(formula_list) == 1:
                subject_ids = self.env['finance.account'].search(
                    [('code', '=', formula_list[0]), ('account_type', '!=', 'view')])
            else:
                subject_ids = self.env['finance.account'].search(
                    [('code', '>=', formula_list[0]), ('code', '<=', formula_list[1]), ('account_type', '!=', 'view')])
            trial_balances = self.env['trial.balance'].search([('subject_name_id', 'in', [
                subject.id for subject in subject_ids]), ('period_id', '=', period_id.id)])
            for account in trial_balances:
                ret += account.initial_balance_debit - account.initial_balance_credit
        if tem.line_type == 'end':
            pass
        if tem.line_type == 'lines':
            # 根据其他报表行计算
            for line in self.env['inout.flow.statement'].browse(report_ids):
                for l in tem.plus_ids:
                    if str(l.sequence) == str(line.sequence):
                        ret += line.amount
                for l in tem.nega_ids:
                    if str(l.sequence) == str(line.sequence):
                        ret -= line.amount
        if tem.line_type == 'inopen_account':
            # 科目本期借方合计
            ret = sum([acc.current_occurrence_debit
                       for acc in self.env['trial.balance'].search([('period_id', '=', period_id.id),
                                                                    ('subject_name_id', 'in',
                                                                     [o.id for o in tem.d_account_ids])])])
        if tem.line_type == 'outopen_account':
            # 科目本期贷方合计
            ret = sum([acc.current_occurrence_credit
                       for acc in self.env['trial.balance'].search([('period_id', '=', period_id.id),
                                                                    ('subject_name_id', 'in',
                                                                     [o.id for o in tem.c_account_ids])])])

        return ret

    @api.model
    def get_year_amount(self, tem, report_ids, period_id):
        '''
             [('get',u'销售收款'),
              ('pay',u'采购付款'),
              ('category',u'其他收支'),
              ('begin',u'科目期初'),
              ('end',u'科目期末'),
              ('lines',u'表行计算'),
              ('in_account_ids',u'本期收入发生额'),
              ('out_account_ids',u'本期支出发生额')]
        '''
        date_start, date_end = self.env['finance.period'].get_period_month_date_range(
            period_id)
        date_start = date_start[0:5] + '01-01'
        ret = 0
        if tem.line_type == 'get' or tem.line_type == 'pay':
            # 收款单或付款单金额合计
            ret = sum([order.amount for order in self.env['money.order'].search([('type', '=', tem.line_type),
                                                                                 ('state',
                                                                                  '=', 'done'),
                                                                                 ('date', '>=',
                                                                                  date_start),
                                                                                 ('date', '<=', date_end)])])
        if tem.line_type == 'category':
            # 其他收支单金额合计
            ret = sum([line.amount for line in self.env['other.money.order.line'].search([('category_id', 'in', [c.id for c in tem.category_ids]),
                                                                                          ('other_money_id.state', '=', 'done'),
                                                                                          ('other_money_id.date', '>=', date_start),
                                                                                          ('other_money_id.date', '<=', date_end)])])
        if tem.line_type == 'begin':
            pass
        if tem.line_type == 'end':
            # 科目期末金额合计
            pass
        if tem.line_type == 'lines':
            # 根据其他报表行计算
            for line in self.env['inout.flow.statement'].browse(report_ids):
                for l in tem.plus_ids:
                    if l.sequence == line.sequence:
                        ret += line.year_amount
                for l in tem.nega_ids:
                    if l.sequence == line.sequence:
                        ret -= line.year_amount

        if tem.line_type == 'inopen_account':
            # 科目本期借方合计
            ret = sum([acc.cumulative_occurrence_debit
                       for acc in self.env['trial.balance'].search([('period_id', '=', period_id.id),
                                                                    ('subject_name_id', 'in',
                                                                     [o.id for o in tem.d_account_ids])])])
        if tem.line_type == 'outopen_account':
            # 科目本期贷方合计
            ret = sum([acc.cumulative_occurrence_credit
                       for acc in self.env['trial.balance'].search([('period_id', '=', period_id.id),
                                                                    ('subject_name_id', 'in',
                                                                     [o.id for o in tem.c_account_ids])])])

        return ret

    @api.multi
    def inout_show(self):
        """生成现金流量表"""
        rep_ids = []
        if self.period_id:
            templates = self.env['inout.activities.template'].search([])
            for tem in templates:
                new_rep = self.env['inout.flow.statement'].create(
                    {
                        'name': tem.name,
                        'sequence': tem.sequence,
                        'amount': self.get_amount(tem, rep_ids, self.period_id),
                    }
                )
                rep_ids.append(new_rep.id)
        view_id = self.env.ref('nonprofit_money.inout_flow_statement_tree').id
        days = calendar.monthrange(int(self.period_id.year), int(self.period_id.month))[1]
        attachment_information = u'编制单位：' + self.env.user.company_id.name + u',' + self.period_id.year\
                                 + u'年' + self.period_id.month + u'月' + u',' + u'单位：元'

        # 第一行 为字段名
        #  从第二行开始 为数据

        field_list = ['name', 'amount']
        domain = [('id', 'in', rep_ids)]
        export_data = {
            "database": self.pool._db.dbname,
            "company": self.env.user.company_id.name,
            "date":  self.period_id.year + u'年' + self.period_id.month + u'月' ,
            "report_name": u"现金流量表",
            "report_code": u"会民非03表",
            "rows": self.env['inout.flow.statement'].search_count(domain),
            "cols": len(field_list),
            "report_item": []
        }
        '''
        export_data, excel_title_row, excel_data_rows = self.env['create.balance.sheet.wizard']._prepare_export_data(
            'inout.flow.statement', field_list, domain, attachment_information, export_data
        )

        self.env['create.balance.sheet.wizard'].export_xml('inout.flow.statement', {'data': export_data})
        self.env['create.balance.sheet.wizard'].export_excel('inout.flow.statement', {'columns_headers': excel_title_row,
                                                                                     'rows': excel_data_rows})
        '''
        return {
            'type': 'ir.actions.act_window',
            'name': u'收支情况表：' + self.period_id.name,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'inout.flow.statement',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'context': {'period_id': self.period_id.id, 'attachment_information': attachment_information},
            'domain': domain,
            'limit': 65535,
        }
