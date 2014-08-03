# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
import openerp
from openerp.addons.pos_membership.pos_membership import generate_validate_code

CHARGE_TYPE=[
    (1,'正常充值'),
    (2,'奖励充值')
]
ACTIVE_TYPE=[
    (1,'是'),
    (2,'否')
]
class pro_exchange(osv.osv_memory):
#     _register = False
    _name = 'pro.exchange'
    
    _columns = {
        'charge_amount': fields.float('充值金额',digits=(16,2)),
        'charge_type': fields.selection(CHARGE_TYPE, '充值类型'),
        'comment': fields.char('备注',size=36),
    }
    
    _defaults = {
        'charge_type': 1,
    }

    def _sortSetcharges(self,setcharges): 
        a={}
        for setcharge in setcharges:
            a[setcharge['money']]=setcharge['id']
        items = a.items() 
        items.sort(reverse=True) 
        return items

    def run(self, cr, uid, ids, context=None):
        if not context:
            context = dict()
        
        #表单信息
        self_obj = None
        records = self.browse(cr, uid, ids, context=context)
        if records and len(records) == 1:
            self_obj = records[0]
        if not (self_obj  or self_obj.charge_amount):
            return {}
        c_type = self_obj.charge_type
        c_amount = self_obj.charge_amount
        
        #会员信息
        mem_obj = None
        active_model = context.get('active_model', False) or False
        active_ids = context.get('active_ids', []) or []
        records = self.pool.get(active_model).browse(cr, uid, active_ids, context=context)
        if records and len(records) == 1:
            mem_obj = records[0]
        if not mem_obj:
            raise osv.except_osv( _('警告!'),_('获取会员信息失败！'))
        if not mem_obj.m_normal:
            raise osv.except_osv( _('警告!'),_('会员状态不可用！'))
        old_level = mem_obj.m_level
        
        
        #充值
        money_obj = self.pool.get('membership.smallpos.money').search(cr, uid, [('member_id','=',mem_obj.member_id)], context=context)
        money_data = self.pool.get('membership.smallpos.money').read(cr, uid, money_obj, context=context)
        old_money = money_data[0]['total_money']
        new_money = old_money + c_amount
        self.pool.get('membership.smallpos.money').write(cr, uid, money_data[0]['id'], {'total_money': new_money,})
        
        #充值记录
        
        #弹出等级提示窗口
        #如果新的折扣小于旧的折扣，则提示窗口
        if c_type == 1 and context.get('up_level_status',True): # 正常充值
            #查询级别
            new_level = None
            level_domain = [('min_money','<=',c_amount),('max_money','>',c_amount)]
            level_ids = self.pool.get('membership.smallpos.level').search(cr, uid,level_domain)
            if level_ids and len(level_ids) == 1:
                records = self.pool.get('membership.smallpos.level').read(cr, uid,level_ids)
                new_level = records[0]
            if not new_level:
                raise osv.except_osv( _('警告!'),_('获取等级信息失败！'))

            if new_level.get('percent') < old_level.percent:
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
                    'name': _('会员升级'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'member.charge.level',
                    'view_id': False,
                    'target': 'new',
                    'views': False,
                    'type': 'ir.actions.act_window',
                    'context': ctx,
                }
        
        
        #发送短信提醒
        pass

member_charge()


class member_charge_level(osv.osv_memory):
#     _register = False
    _name = 'member.charge.level'
    
    _columns = {
        'comment': fields.char('',size=64, readonly=True),
    }
    _defaults ={
        'comment': lambda self, cr, uid, context={}: '会员卡号为%(card_no)s的会员,当前会员等级为%(old_level)s,由于充值金额达到%(charge_amount)s,可升级为%(new_level)s，享受折扣%(new_percent)s，点击确定升级，是否升级？' % context,
    }

    def run(self, cr, uid, ids, context=None):
        #修改等级
        id=context.get("id",None)
        level_id = context.get("level_id",None)
        if id and level_id:
            self.pool.get('membership.smallpos.member').write(cr, uid, id, {'m_level':level_id})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
