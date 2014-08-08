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

class vip_points_details(report_sxw.rml_parse):
    def _get_all_users(self):
        user_obj = self.pool.get('res.users')
        return user_obj.search(self.cr, self.uid, [])
    
    def _vip_points_info(self,form):
        points_obj = self.pool.get('vip.points.log')
        data = []
        result = {}
        date_start = form['date_start'] + ' 00:00:00'
        date_end = form['date_end'] + ' 23:59:59'
        user_ids = form['user_ids'] or self._get_all_users()
        points_ids = points_obj.search(self.cr, self.uid, [('date','>=',date_start),('date','<=',date_end),('user_id','in',user_ids),])
        for points in points_obj.browse(self.cr, self.uid, points_ids):
            if points.points:
                if points.type == u'消费增加积分':
                    self.add_points += points.points
                elif points.type == u'兑换礼物':
                    self.cut_points += points.points
            result = {
                'date': points.date, 
                'member_id': points.member_id.member_id,
                'm_name': points.member_id.m_name,
                'type': points.type,
                'points': points.points,
                'name':points.name,
                'user_id': points.user_id.login,
            }
            data.append(result)

        if data:
            return data
        else:
            return {}

    def _get_add_points(self):
        return self.add_points
    
    def _get_cut_points(self):
        return self.cut_points
    
    def __init__(self, cr, uid, name, context):
        super(vip_points_details, self).__init__(cr, uid, name, context=context)
        self.add_points = 0
        self.cut_points = 0
        self.localcontext.update({
            'time': time,
            'vip_points_info':self._vip_points_info,
            'get_add_points': self._get_add_points,
            'get_cut_points': self._get_cut_points,
        })

report_sxw.report_sxw('report.vip.points.details', 'vip.points.log', 'addons/vip_membership/report/vip_points_details.rml', parser=vip_points_details, header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
