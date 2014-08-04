# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
import time
from openerp.report import report_sxw

class vip_pay_details(report_sxw.rml_parse):
    def _get_all_users(self):
        user_obj = self.pool.get('res.users')
        return user_obj.search(self.cr, self.uid, [])
    
    def _vip_pay_info(self,form):
        charge_obj = self.pool.get('vip.money.log')
        data = []
        result = {}
        date_start = form['date_start'] + ' 00:00:00'
        date_end = form['date_end'] + ' 23:59:59'
        user_ids = form['user_ids'] or self._get_all_users()
        charge_ids = charge_obj.search(self.cr, self.uid, [('date','>=',date_start),('date','<=',date_end),('user_id','in',user_ids),])
        for charge in charge_obj.browse(self.cr, self.uid, charge_ids):
            if charge.moneys:
                self.all_money += charge.moneys
                if (self.min_money == 0) or (self.min_money and charge.moneys < self.min_money):
                    self.min_money = charge.moneys
                if charge.moneys > self.max_money:
                    self.max_money = charge.moneys
            result = {
                'date': charge.date, 
                'member_id': charge.member_id.member_id,
                'm_name': charge.member_id.m_name,
                'name': charge.name.name,
                'moneys': charge.moneys,
                'user_id': charge.user_id.login,
            }
            data.append(result)

        if data:
            return data
        else:
            return {}

    def _get_all_money(self):
        return self.all_money
    
    def _get_min_money(self):
        return self.min_money
    
    def _get_max_money(self):
        return self.max_money
    
    def __init__(self, cr, uid, name, context):
        super(vip_pay_details, self).__init__(cr, uid, name, context=context)
        self.all_money = 0
        self.min_money = 0
        self.max_money = 0
        self.localcontext.update({
            'time': time,
            'vip_pay_info':self._vip_pay_info,
            'get_all_money': self._get_all_money,
            'get_min_money': self._get_min_money,
            'get_max_money': self._get_max_money,
        })
report_sxw.report_sxw('report.vip.pay.details', 'vip.money.log', 'addons/vip_membership/report/vip_pay_details.rml', parser=vip_pay_details, header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
