# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _

CHARGE_TYPE=[
    (1,u'正常充值'),
    (2,u'赠送金额')
]
ACTIVE_TYPE=[
    (1,u'是'),
    (2,u'否')
]
class member_charge(osv.osv_memory):
#     _register = False
    _name = 'member.charge'
    
    _columns = {
        'charge_amount': fields.float(u'充值金额',digits=(16,2)),
        'charge_type': fields.selection(CHARGE_TYPE, u'充值类型'),
        'comment': fields.char(u'备注',size=36),
    }
    
    _defaults = {
        'charge_type': 1,
    }

    def run(self, cr, uid, ids, context=None):
        if not context:
            context = dict()
        
        #表单信息
        self_obj = None
        records = self.browse(cr, uid, ids, context=context)
        if records and len(records) == 1:
            self_obj = records[0]
        if not self_obj:
            return {}
        if self_obj.charge_amount <= 0:
            return {}
        c_type = self_obj.charge_type
        c_amount = self_obj.charge_amount
        context['AddMoney'] = c_amount
        comment = self_obj.comment
        
        #会员信息
        mem_obj = None
        active_model = context.get('active_model', False) or False
        active_ids = context.get('active_ids', []) or []
        records = self.pool.get(active_model).browse(cr, uid, active_ids, context=context)
        if records and len(records) == 1:
            mem_obj = records[0]
        if not mem_obj:
            raise osv.except_osv( _(u'充值失败!'),_(u'获取会员信息失败！'))
        if not mem_obj.m_normal:
            raise osv.except_osv( _(u'充值失败!'),_(u'会员状态不可用！'))
        old_level = mem_obj.m_level
        
        type_dict = {
                     1: u'正常充值',
                     2: u'赠送金额',
                     }
        status = self.pool.get('vip.money').oper_money(cr,uid,
                                                type=type_dict[c_type],
                                                member_id=mem_obj.member_id, 
                                                money=c_amount,
                                                comment=comment,
                                                context=None)
        if 'fail' in status:
            raise osv.except_osv( _(u'充值失败!'),status['fail'])

        #弹出等级提示窗口
        #正常充值时，判断是弹出升级框
        if c_type == 1: # 
            #查询级别
            new_level = None
            level_model = self.pool.get('vip.level')
            level_domain = [('min_money','<=',c_amount),('max_money','>',c_amount)]
            level_ids = level_model.search(cr, uid,level_domain)
            if level_ids and len(level_ids) == 1:
                records = level_model.read(cr, uid,level_ids)
                new_level = records[0]
            else:
                max_money = level_model.get_max_money(cr, uid)
                if max_money and (c_amount >= max_money):
                    level_ids = level_model.search(cr, uid,[('max_money','=',max_money)])
                    records = level_model.read(cr, uid,level_ids)
                    new_level = records[0]
            if new_level:
                # 如果新的折扣小于旧的折扣，则提示窗口
                old_percent = old_level.percent
                new_percent = new_level.get('percent')
                if old_percent == 0:
                    old_percent = 100
                if new_percent == 0:
                    new_percent = 100
                if new_percent < old_percent:
                    ctx = context.copy()
                    ctx.update({'id': mem_obj.id,
                                'level_id': new_level['id'],
                                'card_no': mem_obj.member_id,
                                'old_level': old_level.level_name,
                                'new_level': new_level['level_name'],
                                'charge_amount':c_amount,
                                'new_percent':new_level['percent'],
                                'content':context})
                    
                    return {
                        'name': _(u'会员升级'),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'member.charge.level',
                        'view_id': False,
                        'target': 'new',
                        'views': False,
                        'type': 'ir.actions.act_window',
                        'context': ctx,
                    }
        
        
        #未升级情况发送发送短信提醒
        self.pool.get('message.template').send_sms_temp(cr,uid,active_ids,u'会员充值发送短信',context)

member_charge()


class member_charge_level(osv.osv_memory):
#     _register = False
    _name = 'member.charge.level'
    
    _columns = {
        'comment': fields.char('',size=64, readonly=True),
    }
    _defaults ={
        'comment': lambda self, cr, uid, context={}: u'会员卡号为%(card_no)s的会员,当前会员等级为%(old_level)s,由于充值金额达到%(charge_amount)s,可升级为%(new_level)s，享受折扣%(new_percent)s，点击确定升级，是否升级？' % context,
    }

    def run(self, cr, uid, ids, context=None):
        #修改等级
        id=context.get("id",None)
        level_id = context.get("level_id",None)
        if id and level_id:
            self.pool.get('vip.member').write(cr, uid, id, {'m_level':level_id})
            #升级情况发送发送短信提醒
            self.pool.get('message.template').send_sms_temp(cr,uid,[id],u'会员充值发送短信',context)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }