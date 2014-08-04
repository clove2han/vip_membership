# -*- coding: utf-8 -*-
from openerp.osv import fields, osv

class member_loss(osv.osv_memory):
#     _register = False
    _name = 'member.loss'
    
    _columns = {
        'comment': fields.char('',size=64, readonly=True),
    }
    _defaults ={
        'comment': u'确定要挂失该会员吗？',
    }

    def run(self, cr, uid, ids, context=None):
        #会员信息
        active_model = context.get('active_model', False)
        active_ids = context.get('active_ids', [])
        records = self.pool.get(active_model).browse(cr, uid, active_ids, context=context)
        if records and len(records) == 1:
            new_status = {
                'm_normal': False,
                'm_loss': True,
                'm_off': False,
            }
            self.pool.get('vip.member').write(cr, uid, active_ids, new_status)
            self.pool.get('message.template').send_sms_temp(cr,uid,active_ids,u'会员挂失发送短信')
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
member_loss()