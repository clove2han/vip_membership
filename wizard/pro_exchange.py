# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _

class pro_exchange(osv.osv_memory):
#     _register = False
    _name = 'pro.exchange'
    
    _columns = {
        'vip_product_id': fields.many2one('vip.product',string=u'兑换礼品'),
        'comment': fields.char(u'备注',size=36),
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
        if not self_obj.vip_product_id:
            return {}
        vip_product_id = self_obj.vip_product_id
        comment = self_obj.comment or u"无"

        #会员信息
        mem_obj = None
        active_model = context.get('active_model', False) or False
        active_ids = context.get('active_ids', []) or []
        records = self.pool.get(active_model).browse(cr, uid, active_ids, context=context)
        if records and len(records) == 1:
            mem_obj = records[0]
        if not mem_obj:
            raise osv.except_osv( _(u'警告!'),_(u'获取会员信息失败！'))
        if not mem_obj.m_normal:
            raise osv.except_osv( _(u'警告!'),_(u'会员状态不可用！'))
        
        status = self.pool.get('vip.points').oper_points(cr,uid,
                                                    type=u'兑换礼物',
                                                    member_id=mem_obj.member_id, 
                                                    points=vip_product_id.product_point)
        if not status['flag']:
            raise osv.except_osv( _(u'错误!'),status['info'])
        return {}
