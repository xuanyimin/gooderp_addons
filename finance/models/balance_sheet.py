# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons.web_export_view_good.controllers.controllers import ExcelExportView, ReportTemplate
from math import fabs
import calendar
import os
import xmltodict
import logging
import time

_logger = logging.getLogger(__name__)


class BalanceSheet(models.Model):
    """资产负债表模板
    模板用来定义最终输出的 资产负债表的格式,
     每行的 科目的顺序 科目的大分类的所属的子科目的顺序
    -- 本模板适合中国会计使用.
    """

    _name = "balance.sheet"
    _order = "sequence,id"
    _description = u'资产负债表模板'

    sequence = fields.Integer(u'序号')
    line = fields.Integer(u'序号', required=True, help=u'资产负债表的行次')
    balance = fields.Char(u'资产')
    line_num = fields.Char(u'行次', help=u'此处行次并不是出报表的实际的行数,只是显示用的用来符合国人习惯')
    ending_balance = fields.Float(u'期末余额')
    balance_formula = fields.Text(
        u'科目范围', help=u'设定本行的资产负债表的科目范围，例如1001~1012999999 结束科目尽可能大一些方便以后扩展')
    beginning_balance = fields.Float(u'年初余额')

    balance_two = fields.Char(u'负债和所有者权益')
    line_num_two = fields.Char(u'行次', help=u'此处行次并不是出报表的实际的行数,只是显示用的用来符合国人习惯')
    ending_balance_two = fields.Float(u'期末余额')
    balance_two_formula = fields.Text(
        u'科目范围', help=u'设定本行的资产负债表的科目范围，例如1001~1012999999 结束科目尽可能大一些方便以后扩展')
    beginning_balance_two = fields.Float(u'年初余额', help=u'报表行本年的年余额')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())


class CreateBalanceSheetWizard(models.TransientModel):
    """创建资产负债 和利润表的 wizard"""
    _name = "create.balance.sheet.wizard"
    _description = u'资产负债表和利润表的向导'

    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.model
    def _default_period_domain(self):
        """
        用来设定期间的 可选的范围(这个是一个范围)
        :return: domain条件
        """
        period_domain_setting = self.env['ir.values'].get_default(
            'finance.config.settings', 'default_period_domain')
        return [('is_closed', '!=', False)] if period_domain_setting == 'cannot' else []

    @api.model
    def _default_period_id(self):

        return self._default_period_id_impl()

    def _default_period_id_impl(self):
        """
                        默认是当前会计期间
        :return: 当前会计期间的对象
        """
        return self.env['finance.period'].get_date_now_period_id()

    period_id = fields.Many2one('finance.period', string=u'会计期间', domain=_default_period_domain,
                                default=_default_period_id, help=u'用来设定报表的期间')

    @api.multi
    def compute_balance(self, parameter_str, period_id, compute_field_list):
        """根据所填写的 科目的code 和计算的字段 进行计算对应的资产值"""
        if parameter_str:
            parameter_str_list = parameter_str.split('~')
            subject_vals = []
            if len(parameter_str_list) == 1:
                subject_ids = self.env['finance.account'].search(
                    [('code', '=', parameter_str_list[0]), ('account_type', '!=', 'view')])
            else:
                subject_ids = self.env['finance.account'].search(
                    [('code', '>=', parameter_str_list[0]), ('code', '<=', parameter_str_list[1]),
                     ('account_type', '!=', 'view')])
            trial_balances = self.env['trial.balance'].search([('subject_name_id', 'in', [
                subject.id for subject in subject_ids]), ('period_id', '=', period_id.id)])
            for trial_balance in trial_balances:
                # 根据参数code 对应的科目的 方向 进行不同的操作
                #  trial_balance.subject_name_id.costs_types == 'assets'解决：累计折旧 余额记贷方
                if trial_balance.subject_name_id.costs_types == 'assets' or trial_balance.subject_name_id.costs_types == 'cost':
                    subject_vals.append(
                        trial_balance[compute_field_list[0]] - trial_balance[compute_field_list[1]])
                elif trial_balance.subject_name_id.costs_types == 'debt' or trial_balance.subject_name_id.costs_types == 'equity':
                    subject_vals.append(
                        trial_balance[compute_field_list[1]] - trial_balance[compute_field_list[0]])
            return sum(subject_vals)

        else:
            return 0

    def deal_with_balance_formula(self, balance_formula, period_id, year_begain_field):
        if balance_formula:
            return_vals = sum([self.compute_balance(one_formula, period_id, year_begain_field)
                               for one_formula in balance_formula.split(';')])
        else:
            return_vals = 0
        return return_vals

    def balance_sheet_create(self, balance_sheet_obj, year_begain_field, current_period_field):
        balance_sheet_obj.write(
            {'beginning_balance': fabs(self.deal_with_balance_formula(balance_sheet_obj.balance_formula,
                                                                      self.period_id, year_begain_field)),
             'ending_balance': fabs(self.deal_with_balance_formula(balance_sheet_obj.balance_formula,
                                                                   self.period_id, current_period_field)),
             'beginning_balance_two': self.deal_with_balance_formula(balance_sheet_obj.balance_two_formula,
                                                                     self.period_id, year_begain_field),
             'ending_balance_two': self.deal_with_balance_formula(balance_sheet_obj.balance_two_formula,
                                                                  self.period_id, current_period_field)})

    @api.multi
    def create_balance_sheet(self):
        """ 资产负债表的创建 """
        balance_wizard = self.env['create.trial.balance.wizard'].create(
            {'period_id': self.period_id.id})
        balance_wizard.create_trial_balance()
        view_id = self.env.ref('finance.balance_sheet_tree_wizard').id
        balance_sheet_objs = self.env['balance.sheet'].search([])
        year_begain_field = ['year_init_debit', 'year_init_credit']
        current_period_field = [
            'ending_balance_debit', 'ending_balance_credit']
        for balance_sheet_obj in balance_sheet_objs:
            self.balance_sheet_create(
                balance_sheet_obj, year_begain_field, current_period_field)
        force_company = self._context.get('force_company')
        if not force_company:
            force_company = self.env.user.company_id.id
        company_row = self.env['res.company'].browse(force_company)
        days = calendar.monthrange(
            int(self.period_id.year), int(self.period_id.month))[1]
        attachment_information = u'编制单位：' + company_row.name + u',,,,' + self.period_id.year \
                                 + u'年' + self.period_id.month + u'月' + \
                                 str(days) + u'日' + u',,,' + u'单位：元'

        # 第一行 为字段名
        #  从第二行开始 为数据

        field_list = [
            'balance', 'line_num', 'beginning_balance', 'ending_balance', 'balance_two', 'line_num_two',
            'beginning_balance_two', 'ending_balance_two'
        ]
        domain = [('id', 'in', [balance_sheet_obj.id for balance_sheet_obj in balance_sheet_objs])]
        export_data = {
            "database": self.pool._db.dbname,
            "date": fields.Date.context_today(self),
            "report_name": u"资产负债表",
            "report_code": u"会民非01表",
            "rows": self.env['balance.sheet'].search_count(domain),
            "cols": len(field_list),
            "report_item": []
        }

        export_data, excel_title_row, excel_data_rows = self._prepare_export_data(
            'balance.sheet', field_list, domain, attachment_information, export_data
        )

        self.export_xml('balance.sheet', {'data': export_data})
        self.export_excel('balance.sheet', {'columns_headers': excel_title_row, 'rows': excel_data_rows})

        return {  # 返回生成资产负债表的数据的列表
            'type': 'ir.actions.act_window',
            'name': u'资产负债表：' + self.period_id.name,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'balance.sheet',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'context': {'period_id': self.period_id.id, 'attachment_information': attachment_information},
            'domain': domain,
            'limit': 65535,
        }

    def deal_with_profit_formula(self, occurrence_balance_formula, period_id, year_begain_field):
        if occurrence_balance_formula:
            return_vals = sum([self.compute_profit(balance_formula, period_id, year_begain_field)
                               for balance_formula in occurrence_balance_formula.split(";")
                               ])
        else:
            return_vals = 0
        return return_vals

    @api.multi
    def create_profit_statement(self):
        """生成利润表"""
        balance_wizard = self.env['create.trial.balance.wizard'].create(
            {'period_id': self.period_id.id})
        balance_wizard.create_trial_balance()
        view_id = self.env.ref('finance.profit_statement_tree').id
        balance_sheet_objs = self.env['profit.statement'].search([])
        year_begain_field = ['cumulative_occurrence_debit',
                             'cumulative_occurrence_credit']
        current_period_field = [
            'current_occurrence_debit', 'current_occurrence_credit']
        for balance_sheet_obj in balance_sheet_objs:
            balance_sheet_obj.write({'cumulative_occurrence_balance': self.deal_with_profit_formula(
                balance_sheet_obj.occurrence_balance_formula, self.period_id, year_begain_field),
                'current_occurrence_balance': self.compute_profit(
                    balance_sheet_obj.occurrence_balance_formula, self.period_id,
                    current_period_field)})
        force_company = self._context.get('force_company')
        if not force_company:
            force_company = self.env.user.company_id.id
        company_row = self.env['res.company'].browse(force_company)
        days = calendar.monthrange(
            int(self.period_id.year), int(self.period_id.month))[1]
        attachment_information = u'编制单位：' + company_row.name + u',,' + self.period_id.year \
                                 + u'年' + self.period_id.month + u'月' + \
                                 str(days) + u'日' + u',' + u'单位：元'

        # 第一行 为字段名
        #  从第二行开始 为数据

        field_list = ['balance', 'line_num', 'cumulative_occurrence_balance', 'current_occurrence_balance']
        domain = [('id', 'in', [balance_sheet_obj.id for balance_sheet_obj in balance_sheet_objs])]
        export_data = {
            "database": self.pool._db.dbname,
            "date": fields.Date.context_today(self),
            "report_name": u"利润表",
            "report_code": u"会企02表",
            "rows": self.env['profit.statement'].search_count(domain),
            "cols": len(field_list),
            "report_item": []
        }

        export_data, excel_title_row, excel_data_rows = self._prepare_export_data(
            'profit.statement', field_list, domain, attachment_information, export_data
        )

        self.export_xml('profit.statement', {'data': export_data})
        self.export_excel('profit.statement', {'columns_headers': excel_title_row, 'rows': excel_data_rows})

        return {  # 返回生成利润表的数据的列表
            'type': 'ir.actions.act_window',
            'name': u'利润表：' + self.period_id.name,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'profit.statement',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'context': {'period_id': self.period_id.id, 'attachment_information': attachment_information},
            'domain': domain,
            'limit': 65535,
        }

    @api.multi
    def compute_profit(self, parameter_str, period_id, compute_field_list):
        """ 根据传进来的 的科目的code 进行利润表的计算 """
        if parameter_str:
            parameter_str_list = parameter_str.split('~')
            subject_vals_in = []
            subject_vals_out = []
            total_sum = 0
            sign_in = False
            sign_out = False
            if len(parameter_str_list) == 1:
                subject_ids = self.env['finance.account'].search(
                    [('code', '=', parameter_str_list[0]), ('account_type', '!=', 'view')])
            else:
                subject_ids = self.env['finance.account'].search(
                    [('code', '>=', parameter_str_list[0]), ('code', '<=', parameter_str_list[1]),
                     ('account_type', '!=', 'view')])
            if subject_ids:  # 本行计算科目借贷方向
                for line in subject_ids:
                    if line.balance_directions == 'in':
                        sign_in = True
                    if line.balance_directions == 'out':
                        sign_out = True
            trial_balances = self.env['trial.balance'].search([('subject_name_id', 'in', [
                subject.id for subject in subject_ids]), ('period_id', '=', period_id.id)])
            for trial_balance in trial_balances:
                if trial_balance.subject_name_id.balance_directions == 'in':
                    subject_vals_in.append(
                        trial_balance[compute_field_list[0]])
                elif trial_balance.subject_name_id.balance_directions == 'out':
                    subject_vals_out.append(
                        trial_balance[compute_field_list[1]])
                if sign_out and sign_in:  # 方向有借且有贷
                    total_sum = sum(subject_vals_out) - sum(subject_vals_in)
                else:
                    if subject_vals_in:
                        total_sum = sum(subject_vals_in)
                    else:
                        total_sum = sum(subject_vals_out)
            return total_sum

    @api.multi
    def compute_activity(self, formula, period_id, report_fields):
        """ 根据传进来的 的科目的code 进行业务活动表的计算 """
        if formula:
            formula_list = formula.split('~')
            subject_vals = []
            if len(formula_list) == 1:
                subject_ids = self.env['finance.account'].search(
                    [('code', '=', formula_list[0]), ('account_type', '!=', 'view')])
            else:
                subject_ids = self.env['finance.account'].search(
                    [('code', '>=', formula_list[0]), ('code', '<=', formula_list[1]), ('account_type', '!=', 'view')])
            trial_balances = self.env['trial.balance'].search([('subject_name_id', 'in', [
                subject.id for subject in subject_ids]), ('period_id', '=', period_id.id)])
            for trial_balance in trial_balances:
                subject_vals.append(trial_balance[report_fields[0]])
                subject_vals.append(trial_balance[report_fields[1]])

            return sum(subject_vals)
        else:
            return 0

    @api.multi
    def compute_vourch_profit(self, report_fields_formula, period_id, report_fields):
        """ 根据传进来的 的科目的code 进行业务活动表的计算 """
        begint, end = report_fields_formula.split(';')
        no, end_date = self.env['finance.period'].get_period_month_date_range(period_id)
        begint_date, no = self.env['finance.period'].get_period_month_date_range(
            self.env['finance.period'].get_year_fist_period_id())
        if begint[0] != '-':
            begint_list = begint.split('~')
            if len(begint_list) == 1:
                subject_ids = self.env['finance.account'].search(
                    [('code', '=', begint_list[0]), ('account_type', '!=', 'view')])
            else:
                subject_ids = self.env['finance.account'].search(
                    [('code', '>=', begint_list[0]), ('code', '<=', begint_list[1]),
                     ('account_type', '!=', 'view')])
            for subject in subject_ids:
                if 'cumulative_occurrence_debit' in report_fields:
                    begint_obj_ids = self.env['voucher.line'].search(
                        [('account_id', '=', subject.id), ('date', '>=', begint_date), ('date', '<=', end_date),
                         ('credit', '>', 0)])
                else:
                    begint_obj_ids = self.env['voucher.line'].search(
                        [('account_id', '=', subject.id), ('period_id', '=', period_id.id), ('credit', '>', 0)])
            end_list = end[1:].split('~')
            if len(end_list) == 1:
                subject_ids2 = self.env['finance.account'].search(
                    [('code', '=', end_list[0]), ('account_type', '!=', 'view')])
            else:
                subject_ids2 = self.env['finance.account'].search(
                    [('code', '>=', end_list[0]), ('code', '<=', end_list[1]),
                     ('account_type', '!=', 'view')])
            for subject2 in subject_ids2:
                if 'cumulative_occurrence_debit' in report_fields:
                    end_obj_ids = self.env['voucher.line'].search(
                        [('account_id', '=', subject2.id), ('date', '>=', begint_date), ('date', '<=', end_date),
                         ('debit', '>', 0)])
                else:
                    end_obj_ids = self.env['voucher.line'].search(
                        [('account_id', '=', subject2.id), ('period_id', '=', period_id.id), ('debit', '>', 0)])

            vouchers = self.env['voucher'].filtered(
                lambda self: len(self.line_ids) == 2 and self.line_ids.mapped('account_id') in (
                    subject_ids + subject_ids2).ids)

            subject_vals = 0
            for begint_obj in begint_obj_ids:
                for end_obj in end_obj_ids:
                    print begint_obj.voucher_id, end_obj.voucher_id
                    if begint_obj.voucher_id == end_obj.voucher_id and len(begint_obj.voucher_id.line_ids) == 2:
                        subject_vals += (begint_obj.debit or begint_obj.credit)
            return subject_vals
        elif begint[0] == '-':
            begint_list = begint[1:].split('~')
            if len(begint_list) == 1:
                subject_ids = self.env['finance.account'].search(
                    [('code', '=', begint_list[0]), ('account_type', '!=', 'view')])
            else:
                subject_ids = self.env['finance.account'].search(
                    [('code', '>=', begint_list[0]), ('code', '<=', begint_list[1]),
                     ('account_type', '!=', 'view')])
            for subject in subject_ids:
                if 'cumulative_occurrence_debit' in report_fields:
                    begint_obj_ids = self.env['voucher.line'].search(
                        [('account_id', '=', subject.id), ('date', '>=', begint_date), ('date', '<=', end_date),
                         ('credit', '>', 0)])
                else:
                    begint_obj_ids = self.env['voucher.line'].search(
                        [('account_id', '=', subject.id), ('period_id', '=', period_id.id), ('credit', '>', 0)])
            end_list = end.split('~')
            if len(end_list) == 1:
                subject_ids2 = self.env['finance.account'].search(
                    [('code', '=', end_list[0]), ('account_type', '!=', 'view')])
            else:
                subject_ids2 = self.env['finance.account'].search(
                    [('code', '>=', end_list[0]), ('code', '<=', end_list[1]),
                     ('account_type', '!=', 'view')])
            for subject2 in subject_ids2:
                if 'cumulative_occurrence_debit' in report_fields:
                    end_obj_ids = self.env['voucher.line'].search(
                        [('account_id', '=', subject2.id), ('date', '>=', begint_date), ('date', '<=', end_date),
                         ('debit', '>', 0)])
                else:
                    end_obj_ids = self.env['voucher.line'].search(
                        [('account_id', '=', subject2.id), ('period_id', '=', period_id.id), ('debit', '>', 0)])

            vouchers = self.env['voucher'].filtered(
                lambda self: len(self.line_ids) == 2 and self.line_ids.mapped('account_id') in (
                    subject_ids + subject_ids2).ids)
            subject_vals = 0
            for begint_obj in begint_obj_ids:
                for end_obj in end_obj_ids:
                    if begint_obj.voucher_id == end_obj.voucher_id and len(begint_obj.voucher_id.line_ids) == 2:
                        subject_vals += (begint_obj.debit or begint_obj.credit)
            return 0 - subject_vals

    @api.multi
    def compute_lines(self, report_fields_formula):
        pass

    def deal_with_activity_formula(self, report_fields_formula, period_id, report_fields, type):
        if type == 'code' and report_fields_formula:
            return_vals = sum([self.compute_profit(formula, period_id, report_fields)
                               for formula in report_fields_formula.split(';')])
        elif type == 'vourch' and report_fields_formula:
            return_vals = self.compute_vourch_profit(report_fields_formula, period_id, report_fields)

        elif type == 'lines' and report_fields_formula:
            return_vals = 0
            self.compute_lines(report_fields_formula)
        else:
            return_vals = 0
        return return_vals

    @api.multi
    def create_activity_statement(self):
        """生成业务活动表"""
        balance_wizard = self.env['create.trial.balance.wizard'].create(
            {'period_id': self.period_id.id})
        balance_wizard.create_trial_balance()
        view_id = self.env.ref('finance.view_business_activity_statement_tree').id
        report_item_ids = self.env['business.activity.statement'].search([])
        current_fields = ['cumulative_occurrence_debit', 'cumulative_occurrence_credit']
        cumulative_fields = ['current_occurrence_debit', 'current_occurrence_credit']

        for report_item in report_item_ids:
            cumulative_restricted = self.deal_with_activity_formula(report_item.formula_restricted, self.period_id,
                                                                    cumulative_fields, report_item.type)
            cumulative_unrestricted = self.deal_with_activity_formula(report_item.formula_unrestricted, self.period_id,
                                                                      cumulative_fields, report_item.type)
            current_restricted = self.deal_with_activity_formula(report_item.formula_restricted, self.period_id,
                                                                 current_fields, report_item.type)
            current_unrestricted = self.deal_with_activity_formula(report_item.formula_unrestricted, self.period_id,
                                                                   current_fields, report_item.type)

            report_item.write({'cumulative_restricted': cumulative_restricted,
                               'cumulative_unrestricted': cumulative_unrestricted,
                               'cumulative_total': cumulative_restricted + cumulative_unrestricted,
                               'current_restricted': current_restricted,
                               'current_unrestricted': current_unrestricted,
                               'current_total': current_restricted + current_unrestricted,

                               })
        force_company = self._context.get('force_company')
        if not force_company:
            force_company = self.env.user.company_id.id
        company_row = self.env['res.company'].browse(force_company)
        days = calendar.monthrange(
            int(self.period_id.year), int(self.period_id.month))[1]
        attachment_information = u'编制单位：' + company_row.name + u',,' + self.period_id.year \
                                 + u'年' + self.period_id.month + u'月' + \
                                 str(days) + u'日' + u',' + u'单位：元'

        # 第一行 为字段名
        #  从第二行开始 为数据
        domain = [('id', 'in', [report_item.id for report_item in report_item_ids])]

        field_list = [
            'balance', 'line_num', 'current_unrestricted', 'current_restricted', 'current_total',
            'cumulative_unrestricted',
            'cumulative_restricted', 'cumulative_total'
        ]
        # excel_data_rows = []
        export_data = {
            "database": self.pool._db.dbname,
            "date": fields.Date.context_today(self),
            "report_name": u"业务活动表",
            "report_code": u"会民非02表",
            "rows": self.env['business.activity.statement'].search_count(domain),
            "cols": len(field_list),
            "report_item": []
        }

        export_data, excel_title_row, excel_data_rows = self._prepare_export_data(
            'business.activity.statement', field_list, domain, attachment_information, export_data
        )

        self.export_xml('business.activity.statement', {'data': export_data})
        self.export_excel('business.activity.statement', {'columns_headers': excel_title_row, 'rows': excel_data_rows})

        return {  # 返回生成业务活动表的数据的列表
            'type': 'ir.actions.act_window',
            'name': u'业务活动表：' + self.period_id.name,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'business.activity.statement',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'context': {'period_id': self.period_id.id, 'attachment_information': attachment_information},
            'domain': domain,
            'limit': 65535,
        }

    @api.model
    def _prepare_export_data(self, model, field_list, domain, attachment_information, export_data):
        excel_data_rows = []
        xml_data_dict = export_data
        header = {}
        excel_title_row = []
        company_row = attachment_information.split(',')
        header_row = []
        operation_row = []
        idx = 1
        for field in field_list:
            header.update({'col%s' % idx: self.env[model]._fields.get(field).string})
            excel_title_row.append('')
            header_row.append(self.env[model]._fields.get(field).string)
            operation_row.append('')
            idx += 1
        xml_data_dict['report_item'].append(header)
        excel_title_row[0] = xml_data_dict.get('report_name')
        excel_data_rows.append(company_row)
        excel_data_rows.append(header_row)

        _data_dict = self.env[model].search_read(domain, field_list)

        for _data in _data_dict:
            row = {}
            sheet_row = []
            idx = 1
            for field in field_list:
                row.update({'col%s' % idx: _data.get(field, False) or ''})
                sheet_row.append(_data.get(field, False) or '')
                idx += 1

            xml_data_dict['report_item'].append(row)
            excel_data_rows.append(sheet_row)

        operation_row[0] = u'操作人'
        operation_row[1] = self.env.user.name
        operation_row[len(operation_row) - 2] = u'操作时间'
        operation_row[len(operation_row) - 1] = fields.Date.context_today(self)

        excel_data_rows.append(operation_row)

        return xml_data_dict, excel_title_row, excel_data_rows

    @api.model
    def _get_report_template(self, model):
        TIMEFORMAT = "%Y%m%d"
        time_now = time.localtime(time.time())
        date_str = time.strftime(TIMEFORMAT, time_now)

        report_model = self.env['report.template'].search([('model_id.model', '=', model)], limit=1)

        save = report_model and report_model[0].save or False
        roo_path = report_model and report_model[0].path or False
        file_address = report_model and report_model[0].file_address or False
        blank_rows = report_model and report_model[0].blank_rows or False
        header_rows = report_model and report_model[0].header_rows or False
        database_name = self.pool._db.dbname

        folder_name_mapping = {
            'balance.sheet': 'liabilities',
            'business.activity.statement': 'business',
            'profit.statement': 'profit',
            'cash.flow.statement': 'cashFlow'
        }

        folder_name = folder_name_mapping.get(model)

        file_name = '%s_%s_%s' % (database_name, folder_name, date_str)

        export_file_name = False

        if save:
            if roo_path:
                path = '%s/%s/%s/%s' % (roo_path, database_name, folder_name, date_str)
            else:
                path = '%s/%s/%s' % (database_name, folder_name, date_str)
            if not os.path.exists(path):
                os.makedirs(path)

            export_file_name = '%s/%s' % (path, file_name)

        return save, export_file_name, file_address, blank_rows, header_rows

    @api.model
    def export_excel(self, model, data):
        save, export_file_name, template_file, blank_rows, header_rows = self._get_report_template(model)
        title = data.get('columns_headers')
        rows = data.get('rows')

        if header_rows:
            i = header_rows
            while i > 0:
                rows.insert(1, [])
                i = i - 1

        if blank_rows:
            i = blank_rows
            while i > 0:
                rows.insert(0, [])
                i = i - 1
        if save:
            ExcelExportViewer = ExcelExportView()
            excel_data = ExcelExportViewer.from_data_excel(title, [rows, template_file])

            excel_file = open('%s.xls' % (export_file_name), 'wb')
            excel_file.write(excel_data)
            excel_file.close()

    @api.model
    def export_xml(self, model, data):
        save, export_file_name, template_file, blank_rows, header_rows = self._get_report_template(model)
        if save:
            import sys
            reload(sys)
            sys.setdefaultencoding('utf8')
            xml_file = open('%s.xml' % (export_file_name), 'wb')
            xml_string = xmltodict.unparse(data, pretty=True)
            xml_file.write(xml_string)
            xml_file.close()


class ProfitStatement(models.Model):
    """利润表模板
        模板主要用来定义项目的 科目范围,
        然后根据科目的范围得到科目范围内的科目 的利润

    """
    _name = "profit.statement"
    _order = "sequence,id"
    _description = u'利润表模板'

    sequence = fields.Integer(u'序号')

    balance = fields.Char(u'项目', help=u'报表的行次的总一个名称')
    line_num = fields.Char(u'行次', help=u'生成报表的行次')
    cumulative_occurrence_balance = fields.Float(u'本年累计金额', help=u'本年利润金额')
    occurrence_balance_formula = fields.Text(
        u'科目范围', help=u'设定本行的利润的科目范围，例如1001~1012999999 结束科目尽可能大一些方便以后扩展')
    current_occurrence_balance = fields.Float(u'本月金额', help=u'本月的利润的金额')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())


class BusinessActivityStatement(models.Model):
    """ 业务活动表模板

    """

    _name = 'business.activity.statement'
    _order = "sequence,id"
    _description = u'业务活动表'

    sequence = fields.Integer(u'序号')
    type = fields.Selection([('code', u'编码'),
                             ('lines', u'行'),
                             ('vourch', u'凭证')], string=u'类别', copy=False, default='code',
                            index=True, )
    balance = fields.Char(u'项目', help=u'报表的行次的总一个名称')
    line_num = fields.Char(u'行次', help=u'生成报表的行次')
    cumulative_total = fields.Float(u'合计', help=u'本年累计数合计', compute='_compute_total')
    cumulative_restricted = fields.Float(u'限定性', help=u'本年累计数限定性')
    cumulative_unrestricted = fields.Float(u'非限定性', help=u'本年累计数非限定性')
    current_total = fields.Float(u'合计', help=u'本月数合计', compute='_compute_total')
    current_restricted = fields.Float(u'限定性', help=u'本月数限定性')
    current_unrestricted = fields.Float(u'非限定性', help=u'本月数非限定性')
    formula_restricted = fields.Text(
        u'限定性科目范围', help=u'设定本行的限定性业务的科目范围，例如1001~1012999999 结束科目尽可能大一些方便以后扩展')
    formula_unrestricted = fields.Text(
        u'非限定性科目范围', help=u'设定本行的非限定性业务的科目范围，例如1001~1012999999 结束科目尽可能大一些方便以后扩展')
    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.depends('cumulative_restricted', 'cumulative_unrestricted', 'current_restricted', 'current_unrestricted')
    def _compute_total(self):
        for record in self:
            record.cumulative_total = record.cumulative_restricted + record.cumulative_unrestricted
            record.current_total = record.current_restricted + record.current_unrestricted
