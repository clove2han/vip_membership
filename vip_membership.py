# -*- coding: utf-8 -*-
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp
import urllib2
#定义会员状态
CARD_STATUS= [
    (1, '挂失'),
    (2, '正常'),
    (3, '注销'),
]

#定义会员性别
SEX_STATUS= [
    (1, '男'),
    (2, '女'),
]

#手机状态
PHONE_STATUS = [
    (1, '未验证'),
    (2, '已验证'),
]

#兑换商品状态
ACTIVE2_TYPE=[
    (1,'激活状态'),
    (2,'失效状态')
]

#预付款表
class vip_money(osv.osv):
    _name='vip.money'

    _columns = {
        'member_id': fields.many2one('vip.member',string='会员卡号', select=True, ondelete='cascade', required=True),
        'total_money': fields.float('充值金额',digits=(16,2), required=True),
        'comment': fields.char('备注',size=128),
    }
    
    _defaults = {
        'total_money': 0,
    }

#     def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
#         if not context: context = {}
#         active_model = context.get('active_model', False) or False
#         active_ids = context.get('active_ids', []) or []
#         records = []
#         if active_model and active_ids:
#             records = self.pool.get(active_model).browse(cr, uid, active_ids, context=context)
#         if len(records)>1:
#             raise osv.except_osv( '警告!','请选择一个会员进行查询！')
#         
#         res = super(vip_money, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
# 
#         if records:
# #             records = records[0]
# #             print records.m_name
# #             this_records = self.pool.get(self._name).browse(cr, uid, [('name','=','123456')])
#             pass
#         else:
#             res['arch'] = u'''<form string="添加会员卡" version="7.0">
#                         <sheet>
#                             <group>
#                                 <group>
#                                     <field name="name"/>
#                                     <field name="card_status"/>
#                                     <field name="comment"/>
#                                 </group>
#                                 <group>
#                                     <button name="readforboard" class="oe_highlight" type="object"><label string="读取卡号"/></button>
#                                     <label string="*请将会员卡放入感应区！"/>
#                                     <field name="m_password"/>
#                                     <field name="m_password1"/>
#                                 </group>
#                             </group>
#                          </sheet>
#                      </form>'''
#         return res
    
#     def default_get(self, cr, uid, fields, context=None):
#         if context is None:
#             context = {}
#         res = super(vip_money, self).default_get(cr, uid, fields, context=context)
#         ids = self.pool.get(self._name).search(cr, uid, [('name','=','123456')])
#         this_records = self.pool.get(self._name).read(cr, uid, ids)
#         print '========this===============',this_records
#         res.update(this_records[0])
#         return res
#     
#     def readforboard(self, cr, uid, ids, context=None):
#         self.pool.get('vip.money').unlink(cr, uid, ids)
#         raise osv.except_osv(u'警告!',u'亲，暂时未开放此功能！')

#积分表
class vip_points(osv.osv):
    _name='vip.points'

    _columns = {
        'member_id': fields.many2one('vip.member',string='会员卡号', select=True, ondelete='cascade', required=True),
        'points': fields.integer('消费积分', required=True),
        'comment': fields.char('备注',size=128),
    }
    
    _defaults = {
        'points': 0,
    }

#会员表
class vip_member(osv.osv):
    '''pos member'''
    _name = 'vip.member'
    
    def create(self, cr, uid, vals, context=None):
        ids = super(vip_member, self).create(cr, uid, vals, context=context)
        self.pool['vip.money'].create(cr, uid, {'member_id':ids})
        self.pool['vip.points'].create(cr, uid, {'member_id':ids})
        return ids
    
    def _get_member_id(self, cr, uid, ids, field_names, arg, context=None):
        result = {}
        part_obj = self.pool.get('vip.member')
        for charge in self.browse(cr, uid, ids, context=context):
            result[charge.id] = {}.fromkeys(field_names, False)
            if charge.member_id:
                address = part_obj.read(cr, openerp.SUPERUSER_ID, charge.member_id, field_names, context=context)
                if address:
                    for field in field_names:
                        result[charge.id][field] = address[field] or ''
            else:
                for field in field_names:
                    result[charge.id][field] =False
        return result
    
    def _get_total_money(self, cr, uid, ids, field_names, arg, context=None):
        result = {}
        part_obj = self.pool.get('vip.money')
        for charge in self.browse(cr, uid, ids, context=context):
            result[charge.id] = 0.00
            
            if charge.member_id:
                money_obj = part_obj.search(cr, uid, [('member_id','=',ids[0])], context=context)
                money_data = part_obj.read(cr, uid, money_obj, context=context)
                if money_data:
                    money_dict = money_data[0]
                    result[charge.id] = money_dict[field_names]
        return result
    
    def _get_points(self, cr, uid, ids, field_names, arg, context=None):
        result = {}
        part_obj = self.pool.get('vip.points')
        for charge in self.browse(cr, uid, ids, context=context):
            result[charge.id] = 0

            if charge.member_id:
                money_obj = part_obj.search(cr, uid, [('member_id','=',ids[0])], context=context)
                money_data = part_obj.read(cr, uid, money_obj, context=context)
                if money_data:
                    money_dict = money_data[0]
                    result[charge.id] = money_dict[field_names]
        return result
    
    def _get_card_status(self, cr, uid, ids, field_names, arg, context=None):
        result = {}
        for charge in self.browse(cr, uid, ids, context=context):
            result[charge.id] = 0
            if charge.m_normal:
                result[charge.id] = '正常'
            elif charge.m_loss:
                result[charge.id] = '挂失'
            elif charge.m_off:
                result[charge.id] = '注销'
            else:
                raise osv.except_osv( _('错误!'),_('查询会员状态异常，请联系管理员'))
        return result

    _columns = {
        'member_id': fields.char('会员卡号', size=32, select=True, required=True),
        'card_status': fields.function(_get_card_status,type='char', string='会员卡状态'),
        'm_password': fields.char('支付密码',size=12),
        'm_normal': fields.boolean('激活状态', required=True),
        'm_loss': fields.boolean('挂失状态', required=True),
        'm_off': fields.boolean('注销状态', required=True),
        'm_level': fields.many2one('vip.level',string='会员等级', required=True),
        'm_name': fields.char('姓名', size=24, select=1),
        'm_sex': fields.selection(SEX_STATUS, '性别'),
        'm_telephone': fields.char('手机号码', size=12, select=1),
        'm_address': fields.char('联系地址', size=128),
        'm_email': fields.char('电子邮件', size=32),
        'm_birthdate': fields.date('生日'),
        'm_identity_no': fields.char('身份证', size=24),
        'comment': fields.char('备注',size=128),
        #'name': fields.function(_get_member_id,type='char', size=32, string='会员卡号',multi='name'),
        'total_money': fields.function(_get_total_money,type='float', string='充值金额'),
        'points': fields.function(_get_points,type='integer', string='消费积分'),
    }
    _defaults = {
        'm_name': '',
        'm_password':'',
        'm_sex': 1,
        'm_level': 1,
        'm_normal': True,
        'm_loss': False,
        'm_off': False,
 }

    _sql_constraints = [
        ('name_uniq', 'unique(member_id)',u'会员卡号已存在！'),
    ]
    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """ To call the init() method timely
        """
        res = super(vip_member, self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        return res
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        for inst in self.browse(cr, uid, ids, context=context):
            name = inst.member_id or ''
            res.append((inst.id, name))
        return res
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('member_id','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('member_id',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)
    
    def change_password(self, cr, uid, ids, old_passwd, new_passwd, context=None):
        """Change current user password. Old password must be provided explicitly
        to prevent hijacking an existing user session, or for cases where the cleartext
        password is not used to authenticate requests.

        :return: True
        :raise: openerp.exceptions.AccessDenied when old password is wrong
        :raise: except_osv when new password is not set or empty
        """
#         self.check(cr.dbname, uid, old_passwd)
#         if new_passwd:
#             return self.write(cr, uid, ids, {'m_password': new_passwd})
        raise osv.except_osv(_('Warning!'), _("Setting empty passwords is not allowed for security reasons!"))
    
    #充值
    def member_money(self, cr, uid, ids, context=None):
        return {
            'name': "充值",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'member.charge',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
            'context': context,
        }
        
    #挂失
    def member_loss(self, cr, uid, ids, context=None):
        return {
            'name': "挂失",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'member.loss',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
            'context': context,
        }
        
    #激活
    def member_active(self, cr, uid, ids, context=None):
        return {
            'name': "激活",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'member.active',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
            'context': context,
        }
    
    #修改密码
    def member_pwd(self, cr, uid, ids, context=None):
        return {
            'name': "修改密码",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'member.pwd',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
            'context': context,
        }
    
    #找回密码
    def member_sms_pwd(self, cr, uid, ids, context=None):
        self.pool.get('message.setting').send_sms(cr, uid, 'this is ', '18025447851')

        return {
            'name': "找回密码",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'member.pwd',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
            'context': context,
        }

    #注销
    def member_off(self, cr, uid, ids, context=None):
        return {
            'name': "注销",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'member.off',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
            'context': context,
        }
        
    #兑换商品
    def pro_exchange(self, cr, uid, ids, context=None):
        return {
            'name': "度环商品",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pro.exchange',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
            'context': context,
        }

#消费记录表
class vip_money_log(osv.osv):
    _name='vip.money.log'
    _order = 'date desc'

    _columns = {
        'member_id': fields.many2one('vip.member',string='会员卡号', select=True, ondelete='cascade', required=True),
        'moneys': fields.float('消费金额', digits=(16,2), required=True),
        'name': fields.many2one('pos.config','销售点名称', required=True),
        'date':  fields.datetime('日期', readonly=True, select=True),
        'user_id': fields.many2one('res.users', '操作员', required=True),
        'comment': fields.char('备注',size=36),
        #'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
    }
    
    _defaults = {
        'date': lambda self, cr, uid, context={}: context.get('date', time.strftime("%Y-%m-%d %H:%M:%S")),
        'user_id': lambda self, cr, uid, context: uid,
        #'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

#积分记录表
class vip_points_log(osv.osv):
    _name='vip.points.log'
    _order = 'date desc'

    _columns = {
        'member_id': fields.many2one('vip.member',string='会员卡号', select=True, ondelete='cascade', required=True),
        'points': fields.integer('消费积分', required=True),
        'name': fields.many2one('pos.config','销售点名称', required=True),
        'date':  fields.datetime('日期', readonly=True, select=True, required=True),
        'user_id': fields.many2one('res.users', '操作员', required=True),
        'comment': fields.char('备注',size=36),
        #'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
    }
    
    _defaults = {
        'date': lambda self, cr, uid, context={}: context.get('date', time.strftime("%Y-%m-%d %H:%M:%S")),
        'user_id': lambda self, cr, uid, context: uid,
        #'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

#充值记录表
class vip_charge_log(osv.osv):
    _name='vip.charge.log'
    _order = 'date desc'

    _columns = {
        'member_id': fields.many2one('vip.member',string='会员卡号', select=True, ondelete='cascade', required=True),
        'moneys': fields.float('充值金额',digits=(16,2), required=True),
        'date':  fields.datetime('日期', readonly=True, select=True),
        'user_id': fields.many2one('res.users', '操作员', required=True),
        'comment': fields.char('备注',size=36),
        #'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
    }
    
    _defaults = {
        'date': lambda self, cr, uid, context={}: context.get('date', time.strftime("%Y-%m-%d %H:%M:%S")),
        'user_id': lambda self, cr, uid, context: uid,
        #'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

#积分规则表
class vip_setpoints(osv.osv):
    _name='vip.setpoints'

    _columns = {
        'rule_id': fields.integer('积分规则ID', required=True,help='积分规则ID'),
        'rule_money': fields.float('消费金额(元)', required=True, digits=(16,2),help='每次订单消费多少金额'),
        'rule_point': fields.integer('返回积分', required=True, help='返回积分'),
    }
    
    _defaults = {
        'rule_money': 1,
        'rule_point': 1,
    }

#商品兑换表
class vip_product(osv.osv):
    _name='vip.product'
    _order = 'product_name'

    _columns = {
        'product_id': fields.integer('商品ID',required=True),
        'product_name': fields.char('商品名称', size=12),
        'product_point': fields.integer('所需积分',required=True),
        # 'qty_available': fields.integer('商品数量',required=True),
        'start_date':  fields.date('开始日期',required=True),
        'end_date':  fields.date('结束日期',required=True),
        'product_status': fields.selection(ACTIVE2_TYPE, '状态',required=True),
        'comment': fields.char('备注',size=128),
    }
    
    _defaults = {
        'product_point': 0,
        'product_status': 1
    }

#会员等级表
class vip_level(osv.osv):
    _name = 'vip.level'
    
    _columns = {
        'level_name': fields.char('等级名称', size=10, required=True, help='设置会员等级的名称'),
        'min_money': fields.float('最小金额', digits=(16,2),required=True, help='最小金额上限'),
        'max_money': fields.float('最大金额', digits=(16,2),required=True, help='最大金额上限'),
        'percent': fields.float('享受折扣',digits=(16,2),required=True,help='该会员等级享受的折扣，填写0.88表示为打8.8折'),
    }
    
    _sql_constraints = [
        ('percent_low_than_1', 'CHECK (percent<=1.00)', u'折扣值不能大于1!'),
        ('percent_uniq', 'unique(percent)',u'享受折扣不能和其他重复！'),
        ('percent_uniq', 'CHECK(min_money<=max_money)',u'最大金额必须大于等于最小金额！'),
    ]
    def get_max_money(self, cr, uid, context={}):
        res = 0.00
        max_obj = self.search(cr, uid, [], limit=1,order='max_money DESC', context=context)
        max_level = self.read(cr, uid, max_obj)
        if max_level and len(max_level) == 1:
            res = max_level[0]['max_money']
        return res
        
    _defaults = {
        'min_money': get_max_money,
        'percent': 1.0,
    }

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for inst in self.browse(cr, uid, ids, context=context):
            name = inst.level_name or ''
            res.append((inst.id, name))
        return res
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('level_name','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('level_name',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

#短信账户设置表
class message_setting(osv.osv):
    _name = 'message.setting'

    _columns = {
        'account': fields.char('用户名', size=18, required=True, help='发送短信需申请的账户信息'),
        'password': fields.char('密码', size=18,required=True, help='您申请的发送短信的账号的密码'),
    }
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        for inst in self.browse(cr, uid, ids, context=context):
            name = '账户信息'
            res.append((inst.id, name))
        return res

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """ To call the init() method timely
        """
        res = super(message_setting, self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        return res
    
    def send_sms(self, cr, uid, msginfo, mobile, context=None):
        res = {}
        account = ''
        password = ''
        msg = ''
        message=self.read(cr,uid,[1],['account','password'])
        if message:
            account=message[0]['account']
            password=message[0]['password']
        if  msginfo and mobile and account:
            try:
                sms_res=urllib2.urlopen('http://106.ihuyi.com/webservice/sms.php?method=Submit&account='+account+'&password='+password+'&mobile='+mobile+'&content='+msginfo).read()
            except:
                raise osv.except_osv( _('发送短信失败!'),_('无连接到短信发送服务器！'))
            
            code=res[sms_res.index("<code>")+6:sms_res.index("</code>")]
            msg=res[sms_res.index("<msg>")+5:sms_res.index("</msg>")]
            if code!='2':
                raise osv.except_osv( _('发送短信失败!'),_(msg))


class message_template(osv.osv):
    _name='message.template'

    _columns = {
        'name': fields.char('短信类型',size=18, required=True, readonly=True),
        'sms1': fields.char('短信组成一',size=64),
        'sms2': fields.char('短信组成二',size=64),
        'sms3': fields.char('短信组成三',size=64),
        'sms4': fields.char('短信组成四',size=64),
        'sms5': fields.char('短信组成五',size=64),
    }