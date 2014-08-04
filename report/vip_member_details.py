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
import datetime
from openerp.report import report_sxw

def date_calc(start,end,o_date,isbirth=False):
    format_ = '%Y-%m-%d %H:%M:%S'
    t_start = time.strptime(start, format_)
    t_end = time.strptime(end, format_)
    if isbirth:
        tmp_date = time.strptime(o_date, format_)
        o_year = t_start.tm_year
        if t_start.tm_year < t_end.tm_year:
            if tmp_date.tm_mon < t_end.tm_mon or \
                (tmp_date.tm_mon == t_end.tm_mon and
                    tmp_date.tm_mday <= t_end.tm_mday):
                o_year = t_end.tm_year
        o_date = str(o_year) + o_date[4:]
        
    t_o_date = time.strptime(o_date, format_)
    
    d_start =  datetime.datetime(*t_start[:3])
    d_o_date =  datetime.datetime(*t_o_date[:3])
    d_end =  datetime.datetime(*t_end[:3])
    zreo = d_start - d_start
    if d_o_date-d_start >= zreo and d_end-d_o_date >= zreo:
        return True

class vip_member_details(report_sxw.rml_parse):
    def _get_all_users(self):
        user_obj = self.pool.get('res.users')
        return user_obj.search(self.cr, self.uid, [])
    
    def _vip_member_info(self,form):
        member_obj = self.pool.get('vip.member')
        data = []
        result = {}
        date_start = form['date_start'] + ' 00:00:00'
        date_end = form['date_end'] + ' 23:59:59'
        user_ids = form['user_ids'] or self._get_all_users()
        if len(user_ids) == 1:
            user_ids = '(%s)' % user_ids[0]
        else:
            user_ids = str(tuple(user_ids))
        self.cr.execute("select create_date,member_id,m_loss,m_off,m_normal,m_name,m_sex,m_telephone,m_birthdate " \
                "from vip_member where write_date >= '%s' and write_date <= '%s' and write_uid IN %s " % (date_start,date_end,user_ids))
        for mem in self.cr.dictfetchall():
            self.all_total += 1
            if mem['m_sex'] == 1:
                sex = u'男'
                self.man_total += 1
            else:
                sex = u'女'
            if mem['m_normal']:
                cs = u'正常'
            if mem['m_loss']:
                self.loss_total += 1
                cs = u'挂失'
            if mem['m_off']:
                self.off_total += 1
                cs = u'注销'

            create_date = mem['create_date'].split('.')[0]
            if date_calc(date_start,date_end,create_date):
                self.new_total += 1
            if mem['m_birthdate'] and date_calc(date_start,date_end,mem['m_birthdate']+' 00:00:00',isbirth=True):
                self.birth_total += 1
                
            result = {
                'create_date': mem['create_date'], 
                'member_id': mem['member_id'],
                'card_status': cs,
                'm_name': mem['m_name'],
                'm_sex': sex,
                'm_telephone': mem['m_telephone'],
                'm_birthdate': mem['m_birthdate']
            }
            data.append(result)

        if data:
            return data
        else:
            return {}
    def _get_all_total(self):
        return self.all_total
    
    def _get_new_total(self):
        return self.new_total
    
    def _get_loss_total(self):
        return self.loss_total
    
    def _get_get_off_total(self):
        return self.off_total
    
    def _get_birth_total(self):
        return self.birth_total
    
    def _get_sex_percent(self):
        return '%d : %d ' % (self.man_total, self.all_total-self.man_total)
    
    def __init__(self, cr, uid, name, context):
        super(vip_member_details, self).__init__(cr, uid, name, context=context)
        self.all_total = 0
        self.new_total = 0
        self.loss_total = 0
        self.off_total = 0
        self.birth_total = 0
        self.man_total = 0
        self.localcontext.update({
            'time': time,
            'vip_member_info':self._vip_member_info,
            'get_all_total': self._get_all_total,
            'get_new_total': self._get_new_total,
            'get_loss_total': self._get_loss_total,
            'get_off_total': self._get_get_off_total,
            'get_birth_total': self._get_birth_total,
            'get_sex_percent': self._get_sex_percent,
        })

report_sxw.report_sxw('report.vip.member.details', 'vip.member', 'addons/vip_membership/report/vip_member_details.rml', parser=vip_member_details, header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
