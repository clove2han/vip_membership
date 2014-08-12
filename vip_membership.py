# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from random import sample
from string import ascii_letters, digits
import time
import openerp
import re
import urllib2
from AES import AESModeOfOperation,encryptData,decryptData

mode = AESModeOfOperation.modeOfOperation["CFB"]
key='\xde\x99\xbd\xc14_\xe3!\xfe\xd1\xa2\xb6\x01&\xf6F\xf2\x7f\x17\t\xd9\xa3\xadt'

#定义会员性别
SEX_STATUS= [
    (1, u'男'),
    (2, u'女'),
]

#兑换商品状态
ACTIVE2_TYPE=[
    (1,u'激活状态'),
    (2,u'失效状态')
]

def gen_salt(length=6, symbols=None):
    if symbols is None:
        symbols = ascii_letters + digits
    return ''.join(sample(symbols, length))

#预付款表
class vip_money(osv.osv):
    _name='vip.money'

    _columns = {
        'member_id': fields.many2one('vip.member',string=u'会员卡号', select=True, ondelete='cascade', required=True),
        'total_money': fields.float(u'余额',digits=(16,2), required=True),
        'comment': fields.char(u'备注',size=128),
    }
    
    _defaults = {
        'total_money': 0,
    }

    def oper_money(self,cr,uid,type,member_id,money,name='',comment='',context=None):
        '''
        type:正常充值，赠送金额，消费
        member_id:会员卡号
        money:变动金额
        name:销售点名称，消费时需要传入
        comment:备注信息
        '''
        res = {'flag':False,
               'info':''
        }
        mem_obj = self.pool.get('vip.member').search_read(cr, uid, [('member_id','=',member_id)], context=context)
        if mem_obj and len(mem_obj)==1:
            mem_ids = mem_obj[0]['id']
            money_obj = self.search_read(cr, uid, [('member_id','=',mem_ids)], context=context)
            old_money = money_obj[0]['total_money']
            ids = [money_obj[0]['id']]
            # 充值
            if type in [u'正常充值',u'赠送金额']:
                new_money = old_money + money
                self.write(cr, uid, ids, {'total_money': new_money,})
                # 充值记录
                new_records = {
                    'member_id': mem_ids,
                    'moneys': money,
                    'user_id': uid,
                    'type': type,
                    'comment': comment,
                }
                self.pool.get('vip.charge.log').create(cr, uid, new_records)
                res['flag'] = True
            # 消费
            elif type == u'消费':
                new_money = old_money - money
                if new_money >= 0:
                    self.write(cr, uid, ids, {'total_money': new_money,})
                
                    #消费记录
                    new_records = {
                        'member_id': mem_ids,
                        'moneys': money,
                        'user_id': uid,
                        'name': name,
                        'comment': comment,
                    }
                    self.pool.get('vip.money.log').create(cr, uid, new_records)
                    res['flag'] = True
                else:
                    res['info'] = u'你的余额不够，请选择其他支付方式！'
        else:
            res['info'] = u'预付款中不存在会员信息！'
            
        return res
        

#积分表
class vip_points(osv.osv):
    _name='vip.points'

    _columns = {
        'member_id': fields.many2one('vip.member',string=u'会员卡号', select=True, ondelete='cascade', required=True),
        'points': fields.integer(u'积分', required=True),
        'comment': fields.char(u'备注',size=128),
    }
    
    _defaults = {
        'points': 0,
    }

    def oper_points(self,cr,uid,type,member_id,points,name=None,comment='',context=None):
        '''
        type:消费增加积分，消费积分，兑换礼物
        member_id:会员卡号
        points:变动积分
        name:销售点名称，消费时需要传入
        comment:备注信息
        '''
        res = {'flag':False,
               'info':''
        }
        mem_obj = self.pool.get('vip.member').search_read(cr, uid, [('member_id','=',member_id)], context=context)
        if mem_obj and len(mem_obj)==1:
            mem_ids = mem_obj[0]['id']
            points_obj = self.search_read(cr, uid, [('member_id','=',mem_ids)], context=context)
            old_points = points_obj[0]['points']
            ids = [points_obj[0]['id']]
            # 增加积分
            if type == u'消费增加积分':
                new_points = old_points + points
                self.write(cr, uid, ids, {'points': new_points,})
                
                # 积分记录
                new_records = {
                    'member_id': mem_ids,
                    'points': points,
                    'user_id': uid,
                    'type': type,
                    'comment': comment,
                }
                if name:
                    new_records['name'] = name
                self.pool.get('vip.points.log').create(cr, uid, new_records)
                res['flag'] = True
            # 减少积分
            elif type in[u'消费积分', u'兑换礼物']:
                new_points = old_points - points
                if new_points >= 0:
                    self.write(cr, uid, ids, {'points': new_points,})
                
                    #积分记录
                    new_records = {
                        'member_id': mem_ids,
                        'points': -points,
                        'user_id': uid,
                        'type': type,
                        'comment': comment,
                    }
                    if name:
                        new_records['name'] = name
                    self.pool.get('vip.points.log').create(cr, uid, new_records)
                    res['flag'] = True
                else:
                    res['info'] = u'你的积分不够，无法进行此操作'
        else:
            res['info'] = u'积分表中不存在会员信息！'
            
        return res
#会员表
class vip_member(osv.osv):
    '''vip member'''
    _name = 'vip.member'
    
    def create(self, cr, uid, vals, context=None):
        ids = super(vip_member, self).create(cr, uid, vals, context=context)
        self.set_password(cr, uid, ids,'')
        self.pool['vip.money'].create(cr, uid, {'member_id':ids})
        self.pool['vip.points'].create(cr, uid, {'member_id':ids})
        #创建用户发送短信
        self.pool.get('message.template').send_sms_temp(cr,uid,[ids],u'会员注册成功短信')
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
            if charge.id:
                result[charge.id] = 0.00
                money_obj = part_obj.search(cr, uid, [('member_id','=',charge.id)], context=context)
                money_data = part_obj.read(cr, uid, money_obj, context=context)
                if money_data:
                    money_dict = money_data[0]
                    result[charge.id] = money_dict[field_names]
        return result
    
    def _get_points(self, cr, uid, ids, field_names, arg, context=None):
        result = {}
        part_obj = self.pool.get('vip.points')
        for charge in self.browse(cr, uid, ids, context=context):
            if charge.id:
                result[charge.id] = 0
                money_obj = part_obj.search(cr, uid, [('member_id','=',charge.id)], context=context)
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
                result[charge.id] = u'正常'
            elif charge.m_loss:
                result[charge.id] = u'挂失'
            elif charge.m_off:
                result[charge.id] = u'注销'
            else:
                raise osv.except_osv( _(u'错误!'),_(u'查询会员状态异常，请联系管理员'))
        return result

    _columns = {
        'member_id': fields.char(u'会员卡号', size=32, select=True, required=True),
        'card_status': fields.function(_get_card_status,type='char', string=u'会员卡状态'),
        'm_password': fields.char(u'支付密码',size=64),
        'm_normal': fields.boolean(u'激活状态', required=True),
        'm_loss': fields.boolean(u'挂失状态', required=True),
        'm_off': fields.boolean(u'注销状态', required=True),
        'm_level': fields.many2one('vip.level',string=u'会员等级', required=True),
        'm_name': fields.char(u'姓名', size=24, select=1),
        'm_sex': fields.selection(SEX_STATUS, u'性别'),
        'm_telephone': fields.char(u'手机号码', size=12, select=1),
        'm_address': fields.char(u'联系地址', size=128),
        'm_email': fields.char(u'电子邮件', size=32),
        'm_birthdate': fields.date(u'生日'),
        'm_identity_no': fields.char(u'身份证', size=24),
        'comment': fields.char(u'备注',size=128),
        #'name': fields.function(_get_member_id,type='char', size=32, string='会员卡号',multi='name'),
        'total_money': fields.function(_get_total_money,type='float', string=u'充值金额'),
        'points': fields.function(_get_points,type='integer', string=u'消费积分'),
    }
    _defaults = {
        'm_name': '',
        'm_sex': 1,
        'm_level': 1,
        'm_normal': True,
        'm_loss': False,
        'm_off': False,
 }

    _sql_constraints = [
        ('name_uniq', 'unique(member_id)',u'会员卡号已存在！'),
    ]
    def _check_meber_id(self, cr, uid, ids, context = None):
        for wiz in self.browse(cr, uid, ids, context = context):
            member_id = wiz.member_id
            if (member_id):
                state = re.match(r"^\w+$",member_id)
                if state:
                    return True
        return False

    _constraints = [
        (_check_meber_id,u'会员卡号必须为数字或字母',['member_id']),  # 会员卡号必须为数字或字母

    ]
    
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
    
    def set_password(self, cr, uid, ids, passwd, context=None):
        new_passwd = encryptData(key, passwd, mode)
        self.write(cr, uid, ids, {'m_password': new_passwd})

    def get_password(self, cr, uid, ids, context=None):
        m_password = ''
        records = self.browse(cr, uid, ids, context)
        if records and len(records) == 1:
            mem_obj = records[0]
            m_password = decryptData(key,mem_obj.m_password,mode) or ''
        return m_password
        
    def check(self, cr, uid, ids, old_passwd, context=None):
        records = self.browse(cr, uid, ids, context)
        if records and len(records) == 1:
            mem_obj = records[0]
            m_password = decryptData(key,mem_obj.m_password,mode) or ''
#             print '==db==',repr(m_password),'===input===',repr(old_passwd)
            if  m_password == old_passwd:
                return True
        return False
    
    def change_password(self, cr, uid, ids, old_passwd, new_passwd, context=None):
        """Change current user password. Old password must be provided explicitly
        to prevent hijacking an existing user session, or for cases where the cleartext
        password is not used to authenticate requests.

        :return: True
        :raise: openerp.exceptions.AccessDenied when old password is wrong
        :raise: except_osv when new password is not set or empty
        """
        res = {'flag':False,
               'info':''}
        records = self.browse(cr, uid, ids, context=context)
        if records and len(records) == 1:
            mem_obj = records[0]
        if not mem_obj:
            res['info'] = u'获取会员信息失败！'
        if not mem_obj.m_normal:
            res['info'] = u'会员状态不可用！'
        else:
            if self.check(cr, uid, ids,old_passwd):
                self.set_password(cr, uid, ids,new_passwd)
                res['flag'] = True
            else:
                res['info'] = u'原密码输入错误！'
        
        return res
    
    #充值
    def member_money(self, cr, uid, ids, context=None):
        return {
            'name': u"充值",
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
            'name': u"挂失",
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
            'name': u"激活",
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
            'name': u"修改密码",
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
        status = self.pool.get('message.template').send_sms_temp(cr,uid,ids,u'会员发送密码短信',context)
        if status["flag"]:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            raise osv.except_osv(u'发送失败!',status['info'])

    #注销
    def member_off(self, cr, uid, ids, context=None):
        return {
            'name': u"注销",
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
            'name': u"兑换礼物",
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
        'member_id': fields.many2one('vip.member',string=u'会员卡号', select=True, ondelete='cascade', required=True),
        'moneys': fields.float(u'消费金额', digits=(16,2), required=True),
        'name': fields.char(u'销售点名称', size=32,required=True),
        'date':  fields.datetime(u'日期', readonly=True, select=True),
        'user_id': fields.many2one('res.users', u'操作员', required=True),
        'comment': fields.char(u'备注',size=128),
        #'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
    }
    
    _defaults = {
        'date': lambda self, cr, uid, context={}: context.get('date', time.strftime("%Y-%m-%d %H:%M:%S")),
        'user_id': lambda self, cr, uid, context: uid,
        #'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        for inst in self.browse(cr, uid, ids, context=context):
            name = inst.member_id.member_id or ''
            res.append((inst.id, name))
        return res
    
#积分记录表
class vip_points_log(osv.osv):
    _name='vip.points.log'
    _order = 'date desc'

    _columns = {
        'member_id': fields.many2one('vip.member',string=u'会员卡号', select=True, ondelete='cascade', required=True),
        'points': fields.integer(u'消费积分', required=True),
        'name': fields.char(u'销售点名称', size=32,required=True),
        'date':  fields.datetime(u'日期', readonly=True, select=True, required=True),
        'type': fields.char(u'类型',size=12),
        'user_id': fields.many2one('res.users', u'操作员', required=True),
        'comment': fields.char(u'备注',size=128),
        #'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
    }
    
    _defaults = {
        'date': lambda self, cr, uid, context={}: context.get('date', time.strftime("%Y-%m-%d %H:%M:%S")),
        'user_id': lambda self, cr, uid, context: uid,
        #'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for inst in self.browse(cr, uid, ids, context=context):
            name = inst.member_id.member_id or ''
            res.append((inst.id, name))
        return res

#充值记录表
class vip_charge_log(osv.osv):
    _name='vip.charge.log'
    _order = 'date desc'

    _columns = {
        'member_id': fields.many2one('vip.member',string=u'会员卡号', select=True, ondelete='cascade', required=True),
        'moneys': fields.float(u'充值金额',digits=(16,2), required=True),
        'type': fields.char(u'类型',size=12, required=True),
        'date':  fields.datetime(u'日期', readonly=True, select=True),
        'user_id': fields.many2one('res.users', u'操作员', required=True),
        'comment': fields.char(u'备注',size=128),
        #'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
    }
    
    _defaults = {
        'date': lambda self, cr, uid, context={}: context.get('date', time.strftime("%Y-%m-%d %H:%M:%S")),
        'user_id': lambda self, cr, uid, context: uid,
        #'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for inst in self.browse(cr, uid, ids, context=context):
            name = inst.member_id.member_id or ''
            res.append((inst.id, name))
        return res

#积分规则表
class vip_setpoints(osv.osv):
    _name='vip.setpoints'

    _columns = {
        'rule_money': fields.float(u'消费金额(元)', required=True, digits=(16,2),help=u'每次订单消费多少金额'),
        'rule_point': fields.integer(u'返回积分', required=True, help=u'返回积分'),
        'rule_active': fields.boolean(u'激活状态', required=True,help=u'当处于激活状态时，会员消费可为会员积分'),
    }

    _sql_constraints = [
        ('money_greater_than_0', 'CHECK (rule_money>=0)', u'消费金额不能小于0'),
        ('point_greater_than_0', 'CHECK (rule_point>=0)', u'返回积分不能小于0'),
    ]
     
    _defaults = {
        'rule_money': 1,
        'rule_point': 1,
    }
    def name_get(self, cr, uid, ids, context=None):
        res = []
        for inst in self.browse(cr, uid, ids, context=context):
            name = u'积分规则'
            res.append((inst.id, name))
        return res
#商品兑换表
class vip_product(osv.osv):
    _name='vip.product'
    _order = 'product_name'

    _columns = {
        'product_id': fields.integer(u'商品ID',required=True),
        'product_name': fields.char(u'商品名称', size=12),
        'product_point': fields.integer(u'所需积分',required=True),
        # 'qty_available': fields.integer('商品数量',required=True),
        'start_date':  fields.date(u'开始日期',required=True),
        'end_date':  fields.date(u'结束日期',required=True),
        'product_status': fields.selection(ACTIVE2_TYPE, u'状态',required=True),
        'comment': fields.char(u'备注',size=128),
    }
    
    _sql_constraints = [
        ('greater_than_0', 'CHECK (product_point>=0)', u'积分值不能小于0'),
    ]
    
    _defaults = {
        'product_point': 0,
        'product_status': 1
    }
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        for inst in self.browse(cr, uid, ids, context=context):
            name = inst.product_name or ''
            res.append((inst.id, name))
        return res

#会员等级表
class vip_level(osv.osv):
    _name = 'vip.level'
    
    _columns = {
        'level_name': fields.char(u'等级名称', size=10, required=True, help=u'设置会员等级的名称'),
        'min_money': fields.float(u'最小金额', digits=(16,2),required=True, help=u'最小金额上限'),
        'max_money': fields.float(u'最大金额', digits=(16,2),required=True, help=u'最大金额上限'),
        'percent': fields.integer(u'享受折扣',digits=(16,2),required=True,help=u'该会员等级享受的折扣，取值范围：0-99的整数，输入0表示不打折，90表示为打9折，即原价100元，折后价为90元！'),
    }
    
    _sql_constraints = [
        ('percent_low_than_100', 'CHECK (percent<100)', u'折扣值必须小于100!'),
        ('percent_greater_than_0', 'CHECK (percent>=0)', u'折扣值不能小于0'),
        ('min_greater_than_0', 'CHECK (min_money>=0)', u'最小金额不能小于0'),
        ('max_greater_than_0', 'CHECK (max_money>=0)', u'最大金额不能小于0'),
        ('percent_uniq', 'unique(percent)',u'享受折扣不能和其他重复！'),
        ('percent_min_low_max', 'CHECK(min_money<=max_money)',u'最大金额必须大于等于最小金额！'),
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
        'percent': 0,
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
        'account': fields.char(u'用户名', size=18, required=True, help=u'发送短信需申请的账户信息'),
        'password': fields.char(u'密码', size=18,required=True, help=u'您申请的发送短信的账号的密码'),
    }
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        for inst in self.browse(cr, uid, ids, context=context):
            name = u'账户信息'
            res.append((inst.id, name))
        return res

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """ To call the init() method timely
        """
        res = super(message_setting, self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        return res
    
    def send_sms(self, cr, uid, msginfo, mobile, context=None):
        res = {'flag':False,
               'info':''}
        account = ''
        password = ''
        msg = ''
        ipadds = 'http://121.199.16.178'
        url = 'http://106.ihuyi.com'
        message=self.read(cr,uid,[1],['account','password'])
        if message:
            account=message[0]['account']
            password=message[0]['password']
        if  msginfo and mobile and account:
            try:
                send_url = ipadds + '/webservice/sms.php?method=Submit&account='+account+'&password='+password+'&mobile='+mobile+'&content='+msginfo
                sms_res=urllib2.urlopen(send_url.encode('utf-8')).read()
            except:
                res['info'] = u'无连接到短信发送服务器!'
                return res

            code=sms_res[sms_res.index("<code>")+6:sms_res.index("</code>")]
            msg=sms_res[sms_res.index("<msg>")+5:sms_res.index("</msg>")]
            if code!='2':
                res['info'] =  u"短信服务商返回信息：" + msg.decode("utf-8") + u"。"
            else:
                time.sleep(3)
                res['flag'] =True
        else:
            res['info'] = u'发送短信错误，会员无手机号或短信账户不正确'
        return res


class message_template(osv.osv):
    _name='message.template'

    _columns = {
        'name': fields.char(u'模板名称',size=18, required=True, readonly=True),
        'details': fields.text(u'模板内容',required=True),
        'content': fields.char(u'备注',size=64),
        'active': fields.boolean(u'发送短信'),
    }
    
    def get_info(self,cr,uid,ids,context=None):
        if not context:
            context = {}
        res = {
            'flag':False,
            'info':'',
            'CardID': '',
            'Name': '',
            'AddMoney': '',
            'CurMoney': '',
            'CutMoney': '',
            'Level': '',
            'SecCode': gen_salt(symbols=digits),
            'Time': time.strftime("%Y-%m-%d %H:%M:%S"),
            'AddPoint': '',
            'CurPoint': '',
            'CutPoint': '',
            'Discount': '',
            'Mobile':'',
            'MemPWD':'',
        }
        records = self.pool.get('vip.member').browse(cr, uid, ids, context=context)
        if records and len(records) == 1:
            mem_obj = records[0]
        if not mem_obj:
            res['info'] = u'获取会员信息失败！'
            return res

        res['CardID'] = mem_obj.member_id or ''
        res['Name'] = mem_obj.m_name or ''
        res['CurMoney'] = mem_obj.total_money or 0.00
        res['CurPoint'] = mem_obj.points or 0
        res['Mobile'] = mem_obj.m_telephone or ''
        res['Level'] = mem_obj.m_level.level_name or ''
        res['Discount'] = mem_obj.m_level.percent or ''
        res['MemPWD'] = self.pool.get('vip.member').get_password(cr, uid, ids) or u"空"
        
        res['AddMoney'] = context.get("AddMoney")
        res['CutMoney'] = context.get("CutMoney")
        res['CutPoint'] = context.get("CutPoint")
        res['AddPoint'] = context.get("AddPoint")
#         new_add = self.pool.get('vip.charge.log').search(cr, uid, [('member_id','=',res['CardID'])], limit=1,order='date DESC', context=context)
#         if new_add:
#             addmoney = self.pool.get('vip.charge.log').read(cr,uid,new_add)
#             res['AddMoney'] = addmoney[0]['moneys']
#             
#         new_add = self.pool.get('vip.money.log').search(cr, uid, [('member_id','=',res['CardID'])], limit=1,order='date DESC', context=context)
#         if new_add:
#             addmoney = self.pool.get('vip.money.log').read(cr,uid,new_add)
#             res['CutMoney'] = addmoney[0]['moneys']
#         
#         new_add = self.pool.get('vip.points.log').search(cr, uid, [('member_id','=',res['CardID'])], limit=1,order='date DESC', context=context)
#         if new_add:
#             addmoney = self.pool.get('vip.points.log').read(cr,uid,new_add)
#             points = addmoney[0]['points']
#             if points < 0:
#                 res['CutPoint'] = points
#             else:
#                 res['AddPoint'] = points
        
        res['flag'] = True
        return res
        
    def send_sms_temp(self, cr, uid, ids, modename, context=None):
        res = {'flag':False,
               'info':''}
        mode_data = self.search_read(cr, uid, [('name','=',modename)], limit=1,context=context)
        if not mode_data:
            res['info'] = u'模板名称不可用'
            return res
        
        modestatus = mode_data[0]['active']
        if not modestatus:
            res['info'] = u'模板名称为%s的模板设置了不可发送状态!' % modename
            return res
        modeinfo = mode_data[0]['details']
        
        tmpinfo = self.get_info(cr, uid, ids,context)
        if tmpinfo['flag']:
            for i in tmpinfo:
                modeinfo = modeinfo.replace('{%s}' % i,unicode(tmpinfo[i]))
            mobile = tmpinfo['Mobile']
            if mobile:
                status = self.pool.get('message.setting').send_sms(cr, uid, modeinfo, mobile)
                if status['flag']:
                    res['flag'] = True
                    if modename == u'会员动态支付短信':
                        res['SecCode'] = tmpinfo['SecCode']
                else:
                    res['info'] = status['info']
            else:
                res['info'] = u'当前会员手机号为空！'
        else:
            res['info'] = tmpinfo['info']
#         print u'=======发送内容======',modeinfo
#         print u'=======收到结果======',res['flag'],res['info']
        return res