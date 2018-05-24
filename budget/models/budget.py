# -*- coding: utf-8 -*-

from odoo import models, fields, api
import time
import logging
import os
from odoo.addons.web_export_view_good.controllers.controllers import ExcelExportView, ReportTemplate
from odoo.exceptions import UserError
import xmltodict
_logger = logging.getLogger(__name__)

class BudgetSheet(models.Model):
    """ 预算申报模板
    """
    _name = 'budget.create.sheet'
    # _order = "sequence,id"
    _description = u'预算申报表'

    balance = fields.Char(u'项目', help=u'报表的行次的总一个名称')
    line_num = fields.Char(u'行次', help=u'生成报表的行次')
    create_year = fields.Char(u'年份', help=u'预算年份')
    current_restricted = fields.Float(u'限定性', help=u'本年申报限定性')
    current_unrestricted = fields.Float(u'非限定性', help=u'本年申报非限定性')    
    current_total = fields.Float(u'合计', help=u'本年累计数合计', compute='_compute_total_current')

    def _compute_total_current(self):
         for record in self:
            record.current_total = record.current_restricted + record.current_unrestricted

    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

class BudgetSheet(models.Model):
    """ 预算查询模板
    """
    _name = 'budget.query.sheet'
    # _order = "sequence,id"
    _description = u'预算查询表'

    balance = fields.Char(u'项目', help=u'报表的行次的总一个名称')
    line_num = fields.Char(u'行次', help=u'生成报表的行次')
    create_year = fields.Char(u'年份', help=u'预算年份')
    current_restricted = fields.Float(u'限定性', help=u'本年申报限定性')
    current_unrestricted = fields.Float(u'非限定性', help=u'本年申报非限定性')
    activity_restricted = fields.Float(u'限定性-发生额', help=u'本年消耗限定性')
    activity_unrestricted = fields.Float(u'非限定性-发生额', help=u'本年消耗非限定性')    
    compute_total = fields.Float(u'合计', help=u'本年剩余数合计', compute='_compute_total')
    current_total = fields.Float(u'合计', help=u'本年累计数合计', compute='_compute_total_current')

    def _compute_total_current(self):
         for record in self:
            record.current_total = record.current_restricted + record.current_unrestricted

    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())
    def _compute_total(self):
         for record in self:
            record.compute_total = record.current_restricted + record.current_unrestricted - record.activity_restricted - record.activity_unrestricted

class BudgetWizard(models.TransientModel):
    # 创建向导
    _name = 'create.budget.wizard'
    _description = u'创建预算向导'

    year = fields.Selection(string=u'年度', selection=lambda self: self._get_years(),
                            default=lambda self: self._get_default_year())

    @api.model
    def _get_years(self):
        period_ids = self.env['finance.period'].search([])
        years = []
        for period_id in period_ids:
            if period_id.year not in years:
                years.append(period_id.year)
        return [('%s' % year, u'%s年' % year) for year in years]

    @api.model
    def _get_default_year(self):
        return time.strftime("%Y", time.localtime(time.time()))

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

        # excel_data_rows.append(operation_row)

        return xml_data_dict, excel_title_row, excel_data_rows

    @api.model
    def _get_report_template(self, model, report_month, report_time_slot):
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
            'cash.flow.statement': 'cashFlow',
            'inout.flow.statement': 'inoutFlow',
            'budget.create.sheet':'budget_create',
            'budget.query.sheet':'budget_query',
        }

        folder_name = folder_name_mapping.get(model)

        file_name = '%s_%s_%s' % (database_name, folder_name, report_time_slot)

        export_file_name = False

        if save:
            if roo_path:
                path = '%s/%s/%s/%s' % (roo_path, database_name, folder_name, report_month)
            else:
                path = '%s/%s/%s' % (database_name, folder_name, report_month)
            if not os.path.exists(path):
                os.makedirs(path)

            export_file_name = '%s/%s' % (path, file_name)

        return save, export_file_name, file_address, blank_rows, header_rows


    @api.model
    def export_excel(self, model, data, report_month, report_time_slot):
        save, export_file_name, template_file, blank_rows, header_rows = self._get_report_template(model, report_month, report_time_slot)
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
    def export_xml(self, model, data, report_month, report_time_slot):
        save, export_file_name, template_file, blank_rows, header_rows = self._get_report_template(model, report_month, report_time_slot)
        if save:
            import sys
            reload(sys)
            sys.setdefaultencoding('utf8')
            xml_file = open('%s.xml' % (export_file_name), 'wb')
            xml_string = xmltodict.unparse(data, pretty=True)
            xml_file.write(xml_string)
            xml_file.close()

    @api.multi
    def create_budget_sheet(self):
        self.ensure_one()
        view_id = self.env.ref('budget.view_budget_tree_create').id
        report_item_ids = self.env['budget.create.sheet'].search([('create_year', '=', self.year),])

        period_ids = self.env['finance.period'].search([('year', '=', self.year)])
        lastest_month = max(period_ids.mapped('month'))
        period_id = self.env['finance.period'].search([('year', '=', self.year), ('month', '=', lastest_month)])


        balance_wizard = self.env['create.balance.sheet.wizard'].create({'period_id': period_id.id})
        balance_wizard.create_activity_statement()

        # 如果表里没有数据，则插入空值数据
        if not len(report_item_ids):
            # 写入新一年空白数据
            new_year_ids = self.env['budget.create.sheet'].search([('create_year','=', None)])
            for record in new_year_ids:
                balance_value = record.balance
                line_num_value = record.line_num
                record.create({
                    'balance':balance_value,
                    'line_num':line_num_value,
                    'create_year':self.year,
                })
        report_item_ids = self.env['budget.create.sheet'].search([('create_year', '=', self.year)])

        domain = [('id', 'in', [report_item.id for report_item in report_item_ids])]

        force_company = self._context.get('force_company')
        if not force_company:
            force_company = self.env.user.company_id.id
        company_row = self.env['res.company'].browse(force_company)
        # days = calendar.monthrange(
        #     int(self.period_id.year), int(self.period_id.month))[1]
        # attachment_information = u'编制单位：' + company_row.name + u',,' + self.period_id.year \
        #                          + u'年' + self.period_id.month + u'月' + u',' + u'单位：元'

        attachment_information = u'编制单位：' + company_row.name + u',,' + self.year \
                         + u'年' + u',' + u'单位：元'

        report_time_slot = report_month = "%s"%(period_id.year)

        field_list = [
            'balance','line_num','current_restricted','current_unrestricted','current_total'
        ]
        # excel_data_rows = []
        export_data = {
            "database": self.pool._db.dbname,
            "company": company_row.name,
            "date": self.year + u'年',
            "report_name": u"预算申报表",
            "report_code": u"预算02表",
            "rows": self.env['budget.create.sheet'].search_count(domain),
            "cols": len(field_list),
            "report_item": []
        }

        export_data, excel_title_row, excel_data_rows = self._prepare_export_data(
            'budget.create.sheet', field_list, domain, attachment_information, export_data
        )

        self.export_xml('budget.create.sheet', {'data': export_data}, report_month, report_time_slot)
        self.export_excel('budget.create.sheet', {'columns_headers': excel_title_row, 'rows': excel_data_rows}, report_month, report_time_slot)

        return {  # 返回生成预算申报表的数据的列表
            'type': 'ir.actions.act_window',
            'name': u'预算申报表：' + self.year,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'budget.create.sheet',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'context': {'period_id': period_id.id,'attachment_information': attachment_information},
            'domain': domain,
            'limit': 65535,
        }

    @api.multi
    def query_budget_sheet(self):
        # self.ensure_one()


        period_ids = self.env['finance.period'].search([('year', '=', self.year)])
        lastest_month = max(period_ids.mapped('month'))
        period_id = self.env['finance.period'].search([('year','=', self.year), ('month', '=', lastest_month)])
# ============================================================================#
        # 更新活动表


        balance_wizard = self.env['create.balance.sheet.wizard'].create({'period_id': period_id.id})
        balance_wizard.create_activity_statement()
        
#============================================================================#
        # 年度数据查询
        report_item_ids = self.env['business.activity.statement'].search([])

        activity_restricted = []
        activity_unrestricted = []

        for report_item in report_item_ids:
            activity_restricted.append(report_item.current_restricted)
            activity_unrestricted.append(report_item.current_unrestricted)

#============================================================================#
        # 查询申报数据
        report_item_ids = self.env['budget.create.sheet'].search([('create_year','=',self.year)])

        current_restricted = []
        current_unrestricted = []

        for report_item in report_item_ids:
            current_restricted.append(report_item.current_restricted)
            current_unrestricted.append(report_item.current_unrestricted)

#============================================================================#
        # 插入年度数据
        report_item_ids = self.env['budget.query.sheet'].search([])
        for index, record in enumerate(report_item_ids):
            record.write({'activity_restricted': activity_restricted[index],
                      'activity_unrestricted': activity_unrestricted[index],
                      'current_restricted':current_restricted[index],
                      'current_unrestricted':current_unrestricted[index],
                      }
            )

        # 关联返回视图
        view_id = self.env.ref('budget.view_budget_tree_query').id
        domain = [('id', 'in', [report_item.id for report_item in report_item_ids])]

        force_company = self._context.get('force_company')
        if not force_company:
            force_company = self.env.user.company_id.id
        company_row = self.env['res.company'].browse(force_company)
        # days = calendar.monthrange(
        #     int(self.period_id.year), int(self.period_id.month))[1]
        # attachment_information = u'编制单位：' + company_row.name + u',,' + self.period_id.year \
        #                          + u'年' + self.period_id.month + u'月' + u',' + u'单位：元'

        attachment_information = u'编制单位：' + company_row.name + u',,' + self.year \
                         + u'年' + u',' + u'单位：元'

        report_time_slot = report_month = "%s"%(period_id.year)

        field_list = [
            'balance','line_num','current_restricted','current_unrestricted','activity_restricted','activity_unrestricted','compute_total','current_total'
        ]
        # excel_data_rows = []
        export_data = {
            "database": balance_wizard.pool._db.dbname,
            "company": company_row.name,
            "date": self.year + u'年',
            "report_name": u"预算查询表",
            "report_code": u"预算03表",
            "rows": self.env['budget.query.sheet'].search_count(domain),
            "cols": len(field_list),
            "report_item": []
        }

        export_data, excel_title_row, excel_data_rows = balance_wizard._prepare_export_data(
            'budget.query.sheet', field_list, domain, attachment_information, export_data
        )

        balance_wizard.export_xml('budget.query.sheet', {'data': export_data}, report_month, report_time_slot)
        balance_wizard.export_excel('budget.query.sheet', {'columns_headers': excel_title_row, 'rows': excel_data_rows}, report_month, report_time_slot)

        return {  # 返回生成预算查询表的数据的列表
            'type': 'ir.actions.act_window',
            'name': u'预算查询表：' + self.year,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'budget.query.sheet',
            'target': 'current',
            'view_id': False,
            'views': [(view_id, 'tree')],
            'context': {'period_id': period_id.id,'attachment_information': attachment_information},
            'domain': domain,
            'limit': 65535,
        }
