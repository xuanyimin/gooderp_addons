# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016  德清武康开源软件().
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

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
from lxml import etree
import time
import base64


# 字段只读状态
READONLY_STATES = {
        'done': [('readonly', True)],
    }

MOVE_STATE = [
        ('draft', u'草稿'),
        ('done', u'已完成'),]

#每月销售发票
class wearhouse_to_invoice(models.Model):
    _name = 'wearhouse.to.invoice'
    _order = "end_date"
    name = fields.Char(u'单据编号', index=True, copy=False,
                       default='/', help=u"创建时它会自动生成下一个编号")
    wearhouse_ids = fields.Many2many('wh.move.line',  string=u'出库明细',
                               states=READONLY_STATES, copy=False)
    invoice_ids = fields.Many2many('cn.account.invoice', string=u'销售发票明细',
                               states=READONLY_STATES, copy=False)
    end_date = fields.Date(u'截止日期', copy=False)
    partner_id = fields.Many2one('partner', u'业务伙伴', ondelete='restrict',
                                 help=u'该单据对应的业务伙伴')
    amount = fields.Float(u'金额',digits=dp.get_precision('Amount'),compute = '_compute_amount', store = True,
                          help=u'单据的金额,计算得来')
    state = fields.Selection(MOVE_STATE, u'状态', copy=False, default='draft',
                             index=True,
                             help=u'移库单状态标识，新建时状态为草稿;确认后状态为已确认',
                             track_visibility='always')
    attachment_number = fields.Integer(compute='_compute_attachment_number', string=u'附件号')

    @api.multi
    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'wearhouse.to.invoice'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'wearhouse.to.invoice', 'default_res_id': self.id}
        return res

    @api.multi
    @api.depends('wearhouse_ids')
    def _compute_amount(self):
        self.amount = sum(line.amount for line in self.wearhouse_ids)

    @api.multi
    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'wearhouse.to.invoice'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)

    @api.model
    def create(self, values):
        # 创建单据时生成单据编号
        values.update(
                {'name': self.env['ir.sequence'].next_by_code('wearhouse.to.invoice')})
        return super(wearhouse_to_invoice, self).create(values)

class WhMoveLine(models.Model):
    _inherit = 'wh.move.line'

    partner_id = fields.Many2one('partner', u'业务伙伴', ondelete='restrict',
                                 help=u'该单据对应的业务伙伴')
    is_invoice = fields.Boolean(u'是否已开票',
                             help=u'此明细行已开发票')

    @api.multi
    def _move_partner_id(self):
        self.partner_id = self.line_out_ids.partner_id.id

class CreateInvoiceXmlWizard(models.TransientModel):
    '''生成XML'''
    _name = 'create.invoice.xml.wizard'
    _description = u'生成发票XML向导'


    SELECT = [('dz', u'电子发票'),
               ('zz', u'增值税发票')]

    xml_type = fields.Selection(SELECT, u'XML用于导入',
                                  required=True,
                                  default='zz')

    @api.multi
    def moveline_to_invoice(self):
        toxml = self.env['wearhouse.to.invoice'].browse(self.env.context.get('active_id'))
        partner_id = toxml.partner_id
        Kp = etree.Element("Kp")
        Version = etree.SubElement(Kp, 'Version')
        Version.text = u'3.0'
        Fpxx = etree.SubElement(Kp, 'Fpxx')

        invoice_number = toxml.amount // self.env['ir.values'].get_default('tax.config.settings',
                                                                          'default_invoice_topamount') + 1
        i = 0
        while i < invoice_number:
            i += 1
            Zsl = etree.SubElement(Fpxx, 'Zsl')  # 此文件含有的单据信息数量
            Zsl.text = str(int(i))
            Fpsj = etree.SubElement(Fpxx, 'Fpsj')
            Fp = etree.SubElement(Fpsj, 'Fp')
            self.invoice_top(partner_id, Fp,toxml)
            self.invoice_mx(toxml.wearhouse_ids, Fp)

        tree = etree.ElementTree(Kp)
        tree.write('outinvoice.xml', pretty_print=True,
                   xml_declaration=True, encoding='GBK')
        file_object = open('outinvoice.xml', "r")
        try:
            xml_file = file_object.read()
        finally:
            file_object.close()
        # 生成附件
        self.env['ir.attachment'].create({
            'datas': xml_file.encode('base64'),
            'name': u'开票导入文件',
            'datas_fname': 'outinvoice.xml',
            'res_model': 'wearhouse.to.invoice',
            'res_id': toxml.id, })

    @api.multi
    def invoice_mx(self, mx, Fp):
        Spxx = etree.SubElement(Fp, 'Spxx')

        n = 0
        for line in mx:
            Sph = etree.SubElement(Spxx, 'Sph')
            n += 1
            Xh = etree.SubElement(Sph, 'Xh')  # 序号
            Xh.text = str(int(n))
            Spmc = etree.SubElement(Sph, 'Spmc')  # 商品名称
            Spmc.text = line.goods_id.name
            Ggxh = etree.SubElement(Sph, 'Ggxh')  # 规格型号
            Ggxh.text = ''
            Jldw = etree.SubElement(Sph, 'Jldw')  # 计量单位
            Jldw.text = line.uom_id.name or ''
            Spbm = etree.SubElement(Sph, 'Spbm')  # 商品编码
            Spbm.text = line.goods_id.category_id.tax_category_id.code
            Qyspbm = etree.SubElement(Sph, 'Qyspbm')  # 企业商品编码
            Qyspbm.text = line.goods_id.code or ''
            Syyhzcbz = etree.SubElement(Sph, 'Syyhzcbz')  # 优惠政策标识
            Syyhzcbz.text = ''
            Lslbz = etree.SubElement(Sph, 'Lslbz')  # 零税率标识
            Lslbz.text = '0'
            Yhzcsm = etree.SubElement(Sph, 'Yhzcsm')  # 优惠政策说明
            Dj = etree.SubElement(Sph, 'Dj')  # 单价
            Dj.text = str(round(line.price, 6))
            Sl = etree.SubElement(Sph, 'Sl')  # 数量
            Sl.text = str(round(line.goods_qty, 2))
            Slv = etree.SubElement(Sph, 'Slv')  # 税率
            Slv.text = str(round(line.tax_amount / line.amount, 2))
            Je = etree.SubElement(Sph, 'Je')  # 金额
            Je.text = str(round(line.amount, 2))
            Kce = etree.SubElement(Sph, 'Kce')  # 扣除额

    @api.multi
    def invoice_top(self, partner_id, Fp,toxml):
        partner_name = partner_id.name
        tax_num = partner_id.tax_num
        partner_add_mobile = u'%s %s' % (partner_id.main_address, partner_id.main_mobile)
        partner_bank_num = u'%s %s' % (partner_id.bank_name, partner_id.bank_num)
        company_name = self.env.user.company_id.name
        BMB = self.env['ir.values'].get_default('tax.config.settings', 'default_invoice_spbmbbh')
        seq = u'%s%s%s' % (partner_id.id, toxml.end_date, toxml.name)

        Djh = etree.SubElement(Fp, 'Djh')  # 单据号
        Djh.text = seq
        Gfmc = etree.SubElement(Fp, 'Gfmc')  # 购方名称
        Gfmc.text = partner_name
        Gfsh = etree.SubElement(Fp, 'Gfsh')  # 购方税号
        Gfsh.text = tax_num
        Gfyhzh = etree.SubElement(Fp, 'Gfyhzh')  # 购方银行账号
        Gfyhzh.text = partner_bank_num
        Gfdzdh = etree.SubElement(Fp, 'Gfdzdh')  # 购方地址电话
        Gfdzdh.text = partner_add_mobile
        Bz = etree.SubElement(Fp, 'Bz')  # 备注
        Bz.text = ''
        Fhr = etree.SubElement(Fp, 'Fhr')  # 复核人
        Fhr.text = ''
        Skr = etree.SubElement(Fp, 'Skr')  # 收款人
        Skr.text = ''
        Spbmbbh = etree.SubElement(Fp, 'Spbmbbh')  # 商品编码版本号
        Spbmbbh.text = str(BMB)
        Hsbz = etree.SubElement(Fp, 'Hsbz')  # 收款人
        Hsbz.text = '1'

    @api.multi
    def moveline_to_dzinvoice(self):
        toxml = self.env['wearhouse.to.invoice'].browse(self.env.context.get('active_id'))
        partner_id = toxml.partner_id
        business = etree.Element("business", comment=u"发票开具", id="FPKJ")
        REQUEST_COMMON_FPKJ = etree.SubElement(business, 'REQUEST_COMMON_FPKJ')
        self.dzinvoice_top(partner_id, REQUEST_COMMON_FPKJ,toxml)
        self.dzinvoice_mx(toxml.wearhouse_ids, REQUEST_COMMON_FPKJ)
        tree = etree.ElementTree(business)
        tree.write('outinvoice.xml', pretty_print=True,
                   xml_declaration=True, encoding='GBK')
        file_object = open('outinvoice.xml', "r")
        try:
            xml_file = file_object.read()
        finally:
            file_object.close()
        # 生成附件
        self.env['ir.attachment'].create({
            'datas': xml_file.encode('base64'),
            'name': u'开票导入文件',
            'datas_fname': 'outinvoice.xml',
            'res_model': 'wearhouse.to.invoice',
            'res_id': toxml.id, })

    @api.multi
    def dzinvoice_mx(self, mx, REQUEST_COMMON_FPKJ):
        COMMON_FPKJ_XMXXS = etree.SubElement(REQUEST_COMMON_FPKJ, 'COMMON_FPKJ_XMXXS')
        COMMON_FPKJ_XMXXS.set("class", "COMMON_FPKJ_XMXX")
        COMMON_FPKJ_XMXXS.set("size", "1")
        for line in mx:
            COMMON_FPKJ_XMXX = etree.SubElement(COMMON_FPKJ_XMXXS, 'COMMON_FPKJ_XMXX')
            FPHXZ = etree.SubElement(COMMON_FPKJ_XMXX, 'FPHXZ')  # 发票行性质，0正常行，1折扣行，2被折扣行
            FPHXZ.text = u'0'
            XMMC = etree.SubElement(COMMON_FPKJ_XMXX, 'XMMC')  # 商品名称
            XMMC.text = line.goods_id.name
            GGXH = etree.SubElement(COMMON_FPKJ_XMXX, 'GGXH')  # 规格型号
            GGXH.text = ''
            DW = etree.SubElement(COMMON_FPKJ_XMXX, 'DW')  # 计量单位
            DW.text = line.uom_id.name or ''
            SPBM = etree.SubElement(COMMON_FPKJ_XMXX, 'SPBM')  # 税收编码
            SPBM.text = line.goods_id.category_id.tax_category_id.code
            ZXBM = etree.SubElement(COMMON_FPKJ_XMXX, 'ZXBM')  # 企业编码
            ZXBM.text = line.goods_id.code or ''
            YHZCBS = etree.SubElement(COMMON_FPKJ_XMXX, 'YHZCBS')  # 优惠政策标识：0不使用，1使用
            YHZCBS.text = u'0'
            LSLBS = etree.SubElement(COMMON_FPKJ_XMXX, 'LSLBS')  # 零标识，0出口退税，1免税
            ZZSTSGL = etree.SubElement(COMMON_FPKJ_XMXX, 'ZZSTSGL')  # 优惠政策说明？？
            ZZSTSGL.text = u''
            XMSL = etree.SubElement(COMMON_FPKJ_XMXX, 'XMSL')  # 数量
            XMSL.text = str(round(line.goods_qty, 2))
            XMDJ = etree.SubElement(COMMON_FPKJ_XMXX, 'XMDJ')  # 单价
            XMDJ.text = str(round(line.price, 6))
            XMJE = etree.SubElement(COMMON_FPKJ_XMXX, 'XMJE')  # 金额
            XMJE.text = str(round(line.amount, 2))
            SE = etree.SubElement(COMMON_FPKJ_XMXX, 'SE')  # 税额
            SE.text = str(round(line.tax_amount, 2))
            SL = etree.SubElement(COMMON_FPKJ_XMXX, 'SL')  # 税率
            SL.text = str(round(line.tax_amount / line.amount, 2))
            KCE = etree.SubElement(COMMON_FPKJ_XMXX, 'KCE')  # 扣除额
            KCE.text = u'0'

    @api.multi
    def dzinvoice_top(self, partner_id, REQUEST_COMMON_FPKJ,toxml):
        partner_name = partner_id.name
        tax_num = partner_id.tax_num
        partner_add_mobile = u'%s %s' % (partner_id.main_address, partner_id.main_mobile)
        partner_bank_num = u'%s %s' % (partner_id.bank_name, partner_id.bank_num)
        company_name = self.env.user.company_id.name
        BMB = self.env['ir.values'].get_default('tax.config.settings', 'default_invoice_spbmbbh')
        seq = u'%s%s%s' % (partner_id.id, toxml.end_date, toxml.name)

        REQUEST_COMMON_FPKJ.set("class", "REQUEST_COMMON_FPKJ")
        COMMON_FPKJ_FPT = etree.SubElement(REQUEST_COMMON_FPKJ, 'COMMON_FPKJ_FPT')
        COMMON_FPKJ_FPT.set("class", "COMMON_FPKJ_FPT")
        FPQQLSH = etree.SubElement(COMMON_FPKJ_FPT, 'FPQQLSH')  # 开票请求流水号
        FPQQLSH.text = seq
        KPLX = etree.SubElement(COMMON_FPKJ_FPT, 'KPLX')  # 开票类型 0为蓝字，1为红字
        KPLX.text = u'0'
        XSF_NSRSBH = etree.SubElement(COMMON_FPKJ_FPT, 'XSF_NSRSBH')  # 销售方纳税人识别号
        XSF_NSRSBH.text = company_name
        XSF_MC = etree.SubElement(COMMON_FPKJ_FPT, 'XSF_MC')  # 销售方名称
        XSF_MC.text = ''
        XSF_DZDH = etree.SubElement(COMMON_FPKJ_FPT, 'XSF_DZDH')  # 销售方地址、电话
        XSF_DZDH.text = ''
        XSF_YHZH = etree.SubElement(COMMON_FPKJ_FPT, 'XSF_YHZH')  # 销售方银行帐号
        XSF_YHZH.text = partner_bank_num
        GMF_NSRSBH = etree.SubElement(COMMON_FPKJ_FPT, 'GMF_NSRSBH')  # 购买主纳税人识别号
        GMF_NSRSBH.text = tax_num
        GMF_MC = etree.SubElement(COMMON_FPKJ_FPT, 'GMF_MC')  # 购方名称
        GMF_MC.text = partner_name
        GMF_DZDH = etree.SubElement(COMMON_FPKJ_FPT, 'GMF_DZDH')  # 购方地址、电话
        GMF_DZDH.text = partner_add_mobile
        GMF_YHZH = etree.SubElement(COMMON_FPKJ_FPT, 'GMF_YHZH')  # 购方银行帐号
        GMF_YHZH.text = partner_bank_num
        KPR = etree.SubElement(COMMON_FPKJ_FPT, 'KPR')  # 开票人
        KPR.text = u''
        SKR = etree.SubElement(COMMON_FPKJ_FPT, 'SKR')  # 收款人
        SKR.text = u''
        FHR = etree.SubElement(COMMON_FPKJ_FPT, 'FHR')  # 复核人
        FHR.text = u''
        YFP_DM = etree.SubElement(COMMON_FPKJ_FPT, 'YFP_DM')  # 原发票代码，红字必须
        YFP_DM.text = u''
        YFP_HM = etree.SubElement(COMMON_FPKJ_FPT, 'YFP_HM')  # 原发票号码，红字必须
        YFP_HM.text = u''
        BZ = etree.SubElement(COMMON_FPKJ_FPT, 'BZ')  # 备注
        BMB_BBH = etree.SubElement(COMMON_FPKJ_FPT, 'BMB_BBH')  # 版本号
        BMB_BBH.text = str(BMB)
        JSHJ = etree.SubElement(COMMON_FPKJ_FPT, 'JSHJ')  # 价税合计
        HJJE = etree.SubElement(COMMON_FPKJ_FPT, 'HJJE')  # 合计金额（不含税）
        HJSE = etree.SubElement(COMMON_FPKJ_FPT, 'HJSE')  # 合计税额

class SellOrder(models.Model):
    _inherit = 'sell.order'

    @api.one
    def get_delivery_line(self, line, single=False):
        '''返回销售发货/退货单行'''
        qty = 0
        discount_amount = 0
        if single:
            qty = 1
            discount_amount = line.discount_amount \
                              / ((line.quantity - line.quantity_out) or 1)
        else:
            qty = line.quantity - line.quantity_out
            discount_amount = line.discount_amount

        return {
            'type': self.type == 'sell' and 'out' or 'in',
            'sell_line_id': line.id,
            'goods_id': line.goods_id.id,
            'attribute_id': line.attribute_id.id,
            'uos_id': line.goods_id.uos_id.id,
            'goods_qty': qty,
            'uom_id': line.uom_id.id,
            'cost_unit': line.goods_id.cost,
            'price': line.price,
            'price_taxed': line.price_taxed,
            'discount_rate': line.discount_rate,
            'discount_amount': discount_amount,
            'tax_rate': line.tax_rate,
            'note': line.note or '',
            'partner_id':self.partner_id.id,
        }
