# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _

class member_pwd(osv.osv_memory):
#     _register = False
    _name = 'member.pwd'
    
    _columns = {
        'old_pwd': fields.char(u'旧密码', size=16),
        'new_pwd': fields.char(u'新密码', size=16),
        'confirm_pwd': fields.char(u'确认新密码',size=16),
    }
    
    def run(self, cr, uid, ids, context=None):
        if not context:
            context = dict()
        
        #表单信息
        self_obj = None
        records = self.browse(cr, uid, ids, context=context)
        if records and len(records) == 1:
            self_obj = records[0]
        old_pwd = self_obj.old_pwd or ''
        new_pwd = self_obj.new_pwd or ''
        confirm_pwd = self_obj.confirm_pwd or ''
        if new_pwd != confirm_pwd:
            raise osv.except_osv( _(u'错误!'),_(u'新密码和确认新密码不一致！'))

        #会员信息
        mem_obj = None
        active_model = context.get('active_model', False) or False
        active_ids = context.get('active_ids', []) or []
        records = self.pool.get(active_model).browse(cr, uid, active_ids, context=context)
        if records and len(records) == 1:
            mem_obj = records[0]
        if not mem_obj:
            raise osv.except_osv( _(u'错误!'),_(u'获取会员信息失败！'))
        if not mem_obj.m_normal:
            raise osv.except_osv( _(u'错误!'),_(u'会员状态不可用！'))
        
        status = self.pool.get(active_model).change_password(cr, uid, active_ids, old_pwd, new_pwd)
        if not status['flag']:
            raise osv.except_osv( _(u'错误!'),_(status['info']))
#         if mem_obj.m_password:
#             db_pwd = mem_obj.m_password
#         else:
#             db_pwd = ''
#         if db_pwd != old_pwd:
#             raise osv.except_osv( _(u'错误!'),_(u'原密码输入错误！'))
#         else:
#             self.pool.get(active_model).write(cr, uid, mem_obj.id, {'m_password': new_pwd,})

member_pwd()
