# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016  德清武康开源软件().
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundaption, either version 3 of the
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

from odoo import api, fields, models, tools, _
from odoo.tools.config import config
import pymssql
import xlrd
import xlwt
import re
import base64
from odoo.exceptions import UserError

#增加引出K3销售相关内容
class GoodK3ErpIn(models.Model):
    _inherit = 'tax.invoice.in'

    k3_sql = fields.Many2one('k3.category', u'自方公司', copy=False)
    attachment_number = fields.Integer(compute='_compute_attachment_number', string=u'附件号')

    @api.multi
    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'tax.invoice.in'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'tax.invoice.in', 'default_res_id': self.id}
        return res

    @api.multi
    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'tax.invoice.in'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)

    # COPY excel
    @api.multi
    def worksheetcopy(self,worksheet1,worksheet2):
        ncows = worksheet1.nrows
        ncols = worksheet1.ncols
        for i in range(0,ncows):
            row = worksheet1.row_values(i)
            for j in range(0,ncols):
                worksheet2.write(i,j,row[j])

    # 读取excel
    @api.multi
    def readexcel(self,table):
        ncows = table.nrows
        ncols = 0
        colnames = table.row_values(0)
        list = []
        for rownum in range(1,ncows):
            row = table.row_values(rownum)
            if row:
                app = {}
                for i in range(len(colnames)):
                    app[colnames[i]] = row[i]
                list.append(app)
                ncols += 1
        return list,colnames

    #插入物料
    @api.multi
    def createexcel(self, excel, line, worksheet, number, groups_name, max_code, colnames):

        for i in excel:
            # 修改内容。
            i[u'名称'] = line.product_name #名称
            i[u'规格型号'] = line.product_type #规格型号
            i[u'计量单位组_FName']=i[u'基本计量单位_FGroupName']=i[u'采购计量单位_FGroupName']=i[u'销售计量单位_FGroupName']=i[u'生产计量单位_FGroupName']=i[u'库存计量单位_FGroupName'] = groups_name #单位组
            i[u'采购计量单位_FName'] = i[u'销售计量单位_FName'] = i[u'生产计量单位_FName'] = i[u'库存计量单位_FName']  =i[u'基本计量单位_FName']=line.product_unit #单位
            i[u'存货科目代码_FNumber'] = self.k3_sql.stock_code_in #存货科目代码
            i[u'销售收入科目代码_FNumber'] = self.k3_sql.income_code_in #销售收入科目代码
            i[u'销售成本科目代码_FNumber'] = self.k3_sql.cost_code_out #销售成本科目代码
            i[u'代码'] = max_code #物料代码

        j = 0
        for key in colnames:
            # 写入excel
            worksheet.write(number,j,i[key])
            j += 1

    # 插入发票
    @api.multi
    def createstockin(self, conn, line, excel, worksheet, colnames, number, billno):
        partner_code = self.search_patner_code(conn, line.partner_name_in)
        dep_code,dep_name = self.search_department(conn)
        user_code,user_name = self.search_user(conn)
        for i in excel:
            # 修改内容。
            i[u'审核日期'] = i[u'日期'] = i['付款日期'] = line.invoice_date
            i[u'编    号'] = billno
            i[u'供应商_FNumber'] = partner_code
            i[u'供应商_FName'] = line.partner_name_in
            i[u'部门_FNumber'] = dep_code
            i[u'部门_FName'] = dep_name.encode('latin-1').decode('gbk')
            i[u'制单人_FName'] = i[u'审核人_FName'] = u'宣一敏'
            i[u'负责人_FNumber'] = i[u'验收_FNumber'] = i[u'保管_FNumber'] = i[u'业务员_FNumber']= user_code
            i[u'负责人_FName'] = i[u'验收_FName'] = i[u'保管_FName'] = i[u'业务员_FName']= user_name.encode('latin-1').decode('gbk')

        j = 0
        for key in colnames:
            # 写入excel
            worksheet.write(number,j,i[key])
            j += 1

    # 插入发票明细
    @api.multi
    def createstockinline(self, conn, line, excel, worksheet, colnames, number, line_number, billno):
        good_id = self.search_goods(conn, line)
        good_code, good_name, good_model = good_id
        unit_code = self.search_groups_name(conn, line)[0]
        wearhouse = self.search_wearhouse(conn)
        wearhouse_code, wearhouse_name = wearhouse
        for i in excel:
            # 修改内容。
            i[u'行号'] = str(line_number)
            i[u'单据号_FBillno'] = billno
            i[u'物料编码_FNumber'] = good_code
            i[u'物料编码_FName'] = line.product_name
            i[u'实收数量'] = i[u'基本单位实收数量'] = line.product_count
            i[u'金额'] = line.product_amount
            i[u'单价'] = round(line.product_amount/line.product_count,6)
            i[u'单位_FName'] = line.product_unit
            i[u'单位_FNumber'] = unit_code.encode('latin-1').decode('gbk')
            i[u'收料仓库_FNumber'] = wearhouse_code
            i[u'收料仓库_FName'] = wearhouse_name.encode('latin-1').decode('gbk')

        j = 0
        for key in colnames:
            # 写入excel
            worksheet.write(number, j, i[key])
            j += 1

    # 导出K3销售发票
    @api.multi
    def exp_k3(self):
        xls_data = xlrd.open_workbook('./excel/buy_in.xls')
        Page1 = xls_data.sheet_by_name('Page1')
        Page2 = xls_data.sheet_by_name('Page2')
        Page3 = xls_data.sheet_by_name('Page3')
        Page4 = xls_data.sheet_by_name('t_Schema')
        conn = self.createConnection()
        excel1, colnames1 = self.readexcel(Page1)  # 读模版，返回字典及表头数组
        excel2, colnames2 = self.readexcel(Page2)
        workbook = xlwt.Workbook(encoding='utf-8')  # 生成文件
        worksheet = workbook.add_sheet(u'Page1')  # 在文件中创建一个名为Page1的sheet
        worksheet2 = workbook.add_sheet(u'Page2')
        worksheet3 = workbook.add_sheet(u'Page3')
        self.worksheetcopy(Page3, worksheet3)
        worksheet4 = workbook.add_sheet(u't_Schema')
        self.worksheetcopy(Page4, worksheet4)
        i = j = number = number2 =0
        for key in colnames1:
            worksheet.write(0,j,key)
            j += 1
        for key in colnames2:
            worksheet2.write(0,i,key)
            i += 1
        max_code= self.search_max_fbillno(conn)[0]
        t= int(re.findall("\d+", max_code)[0])
        for invoice in self.line_ids:
            number += 1
            billno = '%s%s' % ('WIN', "%06d" %(t + number))
            self.createstockin(conn, invoice, excel1, worksheet, colnames1, number, billno)
            line_number = 0
            for line in invoice.line_ids:
                number2 += 1
                line_number += 1
                self.createstockinline(conn, line, excel2, worksheet2, colnames2, number2, line_number, billno)

        workbook.save(u'stock_in.xls')
        self.closeConnection(conn)
        # 生成附件
        f = open('stock_in.xls', 'rb')
        self.env['ir.attachment'].create({
            'datas': base64.b64encode(f.read()),
            'name': u'K3采购入库单导入',
            'datas_fname': u'%s采购入库%s.xls' % (self.k3_sql.name, self.name.name),
            'res_model': 'tax.invoice.in',
            'res_id': self.id, })

    # 导出K3物料
    @api.multi
    def exp_k3_goods(self,order = False):
        xls_data = xlrd.open_workbook('./excel/good.xls')
        Page1 = xls_data.sheet_by_name('Page1')
        Page2 = xls_data.sheet_by_name('Page2')
        Page3 = xls_data.sheet_by_name('Page3')
        Page4 = xls_data.sheet_by_name('t_Schema')
        #连接数据库
        conn = self.createConnection()
        excel,colnames = self.readexcel(Page1) #读模版，返回字典及表头数组
        workbook = xlwt.Workbook(encoding = 'utf-8')   # 生成文件
        worksheet = workbook.add_sheet(u'Page1')# 在文件中创建一个名为Page1的sheet
        worksheet2 = workbook.add_sheet(u'Page2')
        self.worksheetcopy(Page2,worksheet2)
        worksheet3 = workbook.add_sheet(u'Page3')
        self.worksheetcopy(Page3, worksheet3)
        worksheet4 = workbook.add_sheet(u't_Schema')
        self.worksheetcopy(Page4, worksheet4)

        i = j = 0
        good = []
        values = self.k3_sql.stock_code_in
        max_code = self.search_max_code(conn,values)[0]
        print max_code
        o,a,b = max_code.split('.')
        for key in colnames:
            worksheet.write(0,j,key)
            j += 1
        for invoice in self.line_ids:
            for line in invoice.line_ids:
                good_id = self.search_goods(conn,line)
                if not good_id:
                    if (line.product_name + line.product_type) in good:
                        continue
                    good.append(line.product_name + line.product_type)
                    groups_name = self.search_groups_name(conn, line)[0]
                    i += 1
                    code = '%s.%s'%(a,int(b)+i)
                    self.createexcel(excel, line, worksheet, i, groups_name.encode('latin-1').decode('gbk'), code, colnames)

        workbook.save(u'goods.xls')
        self.closeConnection(conn)
        # 生成附件
        f = open('goods.xls', 'rb')
        self.env['ir.attachment'].create({
            'datas': base64.b64encode(f.read()),
            'name': u'K3采购物料导出',
            'datas_fname': u'%s物料%s.xls' % (self.k3_sql.name, self.name.name),
            'res_model': 'tax.invoice.in',
            'res_id': self.id, })

    # 创建数据库连接
    @api.multi
    def createConnection(self):
        if config['k3_server'] and config['k3_server'] != 'None':
            k3_server = config['k3_server']
        else:
            raise Exception('k3 服务没有找到.')
        if config['k3_user'] and config['k3_user'] != 'None':
            k3_user = config['k3_user']
        else:
            raise Exception('k3 用户没有找到.')
        if config['k3_password'] and config['k3_password'] != 'None':
            k3_password = config['k3_password']
        else:
            raise Exception('k3 用户密码没有找到.')
        conn = pymssql.connect(server=k3_server, user=k3_user, password=k3_password, database=self.k3_sql.code, charset='utf8')
        return conn

    # 关闭数据库连接。
    @api.multi
    def closeConnection(self,conn):
        conn.close()

    # 查询物料数据
    @api.multi
    def search_goods(self, conn, line):
        cursor = conn.cursor()
        sql = "select fnumber,fname,fmodel from t_ICItem WHERE fname='%s' and fmodel='%s';"
        values = (line.product_name, line.product_type)
        cursor.execute(sql%values)
        good_id = cursor.fetchone()
        if good_id:
            return good_id
        else:
            return False

    # 查询单位组
    @api.multi
    def search_groups_name(self, conn, line):
        cursor = conn.cursor()
        sql = "select Funitgroupid from t_MeasureUnit WHERE fname='%s';"
        values = (line.product_unit)
        cursor.execute(sql % values)
        groups_id = cursor.fetchone()
        if groups_id:
            cursor.execute("select fname from t_UnitGroup WHERE Funitgroupid='%s';" % (groups_id))
            groups_name = cursor.fetchone()
        else:
            raise UserError('请到K3系统增加计量单位%s.' % line.product_unit)
        return groups_name

    # 查询入库单最大编号
    @api.multi
    def search_max_fbillno(self, conn):
        cursor = conn.cursor()
        cursor.execute("select max(FBillno) from ICStockBill where ftrantype = '1';")
        FBillno = cursor.fetchone()
        return FBillno

    # 查询单位编码
    @api.multi
    def search_unit_code(self, conn, name):
        cursor = conn.cursor()
        sql = "select fnumber from t_MeasureUnit WHERE fname='%s';"
        values = (name)
        cursor.execute(sql % values)
        unit_code = cursor.fetchone()
        return unit_code

    # 查询单位CODE
    @api.multi
    def search_unit_code(self, conn, name):
        cursor = conn.cursor()
        sql = "select fnumber from t_MeasureUnit WHERE fname='%s';"
        values = (name)
        cursor.execute(sql%values)
        unit_code = cursor.fetchone()
        return unit_code

    # 查询物料最大code
    @api.multi
    def search_max_code(self, conn, values):
        cursor = conn.cursor()
        sql = "select max(fnumber) from t_ICItem WHERE FAcctID=(select faccountid from t_Account where fnumber= '%s');"
        cursor.execute(sql % values)
        max_code = cursor.fetchone()
        return max_code

    # 查询单位编码
    @api.multi
    def search_patner_code(self, conn, name):
        cursor = conn.cursor()
        sql = "select FNumber from t_Supplier WHERE fname='%s';"
        values = (name)
        cursor.execute(sql % values)
        partner_code = cursor.fetchone()
        if not partner_code:
            raise UserError(u'请在K3系统中增加供应商:%s'% name)
        return partner_code

    # 查询部门
    @api.multi
    def search_department(self, conn):
        cursor = conn.cursor()
        cursor.execute("select top 1 FNumber,Fname from t_Department ;")
        department = cursor.fetchone()
        return department

    # 查询仓库
    @api.multi
    def search_wearhouse(self, conn):
        cursor = conn.cursor()
        cursor.execute("select top 1 FNumber,Fname from t_Stock ;")
        wearhouse = cursor.fetchone()
        return wearhouse

    # 查询员工
    @api.multi
    def search_user(self, conn):
        cursor = conn.cursor()
        cursor.execute("select top 1 FNumber,Fname from t_Emp ;")
        user = cursor.fetchone()
        return user
