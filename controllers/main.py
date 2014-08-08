# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.translate import _
import zipfile
import openerp
import csv
import os
import simplejson
import operator
import tempfile
from cStringIO import StringIO
try:
    import xlwt
except ImportError:
    xlwt = None
import urllib2
import werkzeug
import functools
from openerp.http import request, serialize_exception as _serialize_exception

MEMBER_CODE = {}
def serialize_exception(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception, e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "OpenERP Server Error",
                'data': se
            }
            return werkzeug.exceptions.InternalServerError(simplejson.dumps(error))
    return wrap

def content_disposition(filename):
    filename = filename.encode('utf8')
    escaped = urllib2.quote(filename)
    browser = request.httprequest.user_agent.browser
    version = int((request.httprequest.user_agent.version or '0').split('.')[0])
    if browser == 'msie' and version < 9:
        return "attachment; filename=%s" % escaped
    elif browser == 'safari':
        return "attachment; filename=%s" % filename
    else:
        return "attachment; filename*=UTF-8''%s" % escaped
    
class vip_membership(http.Controller):
    @http.route(['/vip_membership/get_validate_code'], type='json', auth="user")
    def get_validate_code(self, args=None):
        res = {'flag':False,
               'info':''
        }
        cr, uid = request.cr, openerp.SUPERUSER_ID
        member_id = str(args['member_id'])
        if member_id:
            ids = request.registry.get('vip.member').search(cr,uid,[('member_id', '=', member_id),])
            modename = u'会员动态支付短信'
            res = request.registry.get('message.template').send_sms_temp(cr, uid, ids, modename)
            if res['flag']:
                MEMBER_CODE[member_id] = res['SecCode']
        else:
            res['info'] = u'无效的会员号！'
        return res
        
    @http.route(['/vip_membership/check_validate_pwd'], type='json', auth="user")
    def check_validate_pwd(self, args=None):
        res = {'flag':False,
               'info':''
        }
        cr, uid = request.cr, openerp.SUPERUSER_ID
        member_id = str(args['member_id'])
        old_passwd = str(args['old_passwd'])
        if member_id:
            ids = request.registry.get('vip.member').search(cr,uid,[('member_id', '=', member_id),])
            if ids:
                if request.registry.get('vip.member').check(cr, uid, ids, old_passwd):
                    res['flag'] = True
                else:
                    res['info'] = u'支付密码输入错误！'
            else:
                res['info'] = u'无效的会员号！'
        else:
            res['info'] = u'无效的会员号！'
        return res
    
    @http.route(['/vip_membership/get_member_info'], type='json', auth="user")
    def get_member_info(self, args=None):
        res = {'flag':False,
               'info':''
        }
        member_info = {'m_name': None,
                       'card_status':None,
                       'm_level': None,
                       'discount': None,
                       'total_money': None,
                       'points': None,
                       'points_rule': None,
                       'member_id':None,
                       'has_pwd':False,
                       }
        cr, uid = request.cr, openerp.SUPERUSER_ID
        member_id = str(args['member_id'])
        if member_id:
            ids = request.registry.get('vip.member').search(cr,uid,[('member_id', '=', member_id),])
            if ids and len(ids) == 1:
                member_obj = request.registry.get('vip.member').browse(cr,uid,ids)
                member_data = member_obj[0]
                if member_data.card_status != u"正常":
                    res['info'] = u'会员状态不可用，当前状态为：%s' % member_data['card_status']
                else:
                    member_info['m_name'] = member_data.m_name
                    member_info['member_id'] = member_data.member_id
                    member_info['card_status'] = member_data.card_status
                    member_info['m_level'] = member_data.m_level.level_name
                    member_info['discount'] = "%.2f" % (member_data.m_level.percent / float(100))
                    member_info['total_money'] = member_data.total_money
                    member_info['points'] = member_data.points
                    
                    if request.registry.get('vip.member').get_password(cr, uid, ids):
                        member_info['has_pwd'] = True
                    member_info['points_rule'] = 0
                    rule_obj = request.registry.get('vip.setpoints').search_read(cr,uid,[])
                    if rule_obj:
                        rule_data = rule_obj[0]
                        if rule_data['rule_active']:
                            member_info['points_rule'] = rule_data['rule_point'] / float(rule_data['rule_money'])
                    res['flag'] = True
                    res.update(member_info)
            else:
                res['info'] = u'无效的会员号!'
        else:
            res['info'] = u'无效的会员号！'

        return res
    
    @http.route(['/vip_membership/member_sale_money_points'], type='json', auth="user")
    def member_sale_money_points(self, args=None):
        res = {'flag':False,
               'info':''
        }
        context = {}
        cr, uid = request.cr, openerp.SUPERUSER_ID
        member_id = str(args['member_id'])
        first_moneys = args['first_moneys']
        last_money = args['last_money']
        points = args['points']
        context['CutMoney'] = last_money
        context['AddPoint'] = points
        name = str(args['name'])
        type = args['type']
        password = str(args['pwd'])
        pwd_pass = False
        if type == 1: #短信支付
            if password == MEMBER_CODE.get(member_id):
                pwd_pass = True
        elif type == 2: # 密码支付
            if member_id:
                ids = request.registry.get('vip.member').search(cr,uid,[('member_id', '=', member_id),])
                if ids:
                    if request.registry.get('vip.member').check(cr, uid, ids, password):
                        pwd_pass = True
        else:
            raise u'类型错误'
        
        if not pwd_pass:
            res['info'] = '短信密码或支付密码输入错误！'
            return res

        #计算消费
        status = request.registry.get('vip.money').oper_money(cr,uid,
                                                type=u'消费',
                                                member_id=member_id,
                                                name=name,
                                                money=last_money,
                                                cost_moneys=first_moneys,)
        if status['flag']:
            #计算积分
            status = request.registry.get('vip.points').oper_points(cr,uid,
                                                    type=u'消费增加积分',
                                                    member_id=member_id, 
                                                    points=points,
                                                    name=name)
            if status['flag']:
                #发送短信
                modename = u'会员消费发送短信'
                ids = request.registry.get('vip.member').search(cr,uid,[('member_id', '=', member_id),])
                request.registry.get('message.template').send_sms_temp(cr, uid, ids, modename,context)
                res['flag'] = True
            else:
                res['info'] = status['info']
        else:
            res['info'] = status['info']

        return res
    
    @http.route(['/vip_membership/member_sale_points'], type='json', auth="user")
    def member_sale_points(self, args=None):
        res = {'flag':False,
               'info':''
        }
        context = {}
        cr, uid = request.cr, openerp.SUPERUSER_ID
        member_id = str(args['member_id'])
        last_money = args['last_money']
        points = args['points']
        context['CutMoney'] = last_money
        context['AddPoint'] = points
        name = str(args['name'])

        #计算积分
        status = request.registry.get('vip.points').oper_points(cr,uid,
                                                type=u'消费增加积分',
                                                member_id=member_id, 
                                                points=points,
                                                name=name)
        if status['flag']:
            #发送短信
            modename = u'会员积分发送短信'
            ids = request.registry.get('vip.member').search(cr,uid,[('member_id', '=', member_id),])
            request.registry.get('message.template').send_sms_temp(cr, uid, ids, modename,context)
            res['flag'] = True
        else:
            res['info'] = status['info']
        return res

class zip_obj(object):
    def __init__(self):
        # Create the in-memory file-like object
        tmpdir = tempfile.gettempdir()
        self.path = os.path.join(tmpdir,"openerp_vip")
        if not os.path.isdir(self.path):
            os.mkdir(self.path)
        self.in_memory_zip = StringIO()
    def add_file(self):
        f = zipfile.ZipFile(self.in_memory_zip,'w',zipfile.ZIP_DEFLATED)
        tmp = os.getcwd()
        os.chdir(self.path)
        for i in os.listdir(os.getcwd()):
            if i.endswith('.csv'):
                f.write(i)
                os.remove(i)
        os.chdir(tmp)

    def extract_file(self,files):
        f = zipfile.ZipFile(files,'r')
        for file in f.namelist():
            f.extract(file,"temp/")
    
    def read(self):
        '''Returns a string with the contents of the in-memory zip.'''
        self.in_memory_zip.seek(0)
        return self.in_memory_zip.read()
    
class ZIPRecovery(zip_obj, http.Controller):
    raw_data = False
    @http.route('/vip_membership/export/zip', type='http', auth="user")
    def export_zip(self,data,token):
        return self.base(data,token)

    @property
    def content_type(self):
        return 'application/zip'

    def base(self,modes,token):
        modes_dir = {'1':'vip.member','2':'vip.money','3':'vip.points','5':'vip.money.log','6':'vip.points.log','4':'vip.charge.log'}
        for modename in modes:
            if modename in modes_dir:
                self.mode2file(modes_dir[modename])
        self.add_file()
        exname = u'会员管理备份'
        return request.make_response(self.read(),
            headers=[('Content-Disposition',
                            content_disposition(self.filename(exname))),
                     ('Content-Type', self.content_type)],
            cookies={'fileToken': token})
        
    def filename(self, base):
        return base + '.zip'

    def file_data(self,csv_data = {}):
        pass
    
    def mode2file(self,modename):
        Model = request.session.model(modename)
        ids = Model.search([], 0, False, False, request.context)
        fields = Model.fields_get()
        field_names = [i for i in fields if 'function' not in fields[i]]
        field_names.sort()
        import_data = Model.export_data(ids, field_names, self.raw_data, context=request.context).get('datas',[])
        columns_headers = field_names
        self.data2csv(modename,columns_headers,import_data)
        
    def data2csv(self, modename,fields, rows):
        print "self.path",self.path
        fullpath = os.path.join(self.path,modename+'.csv')
        fp = file(fullpath,'w')
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

        writer.writerow([name.encode('utf-8') for name in fields])

        for data in rows:
            row = []
            for d in data:
                if isinstance(d, basestring):
                    d = d.replace('\n',' ').replace('\t',' ')
                    try:
                        d = d.encode('utf-8')
                    except UnicodeError:
                        pass
                if d is False: d = None
                row.append(d)
            writer.writerow(row)
        fp.close()

    @http.route('/vip_import/set_file')
    def set_file(self, req, file, jsonp='callback'):
        return 'window.top.%s(%s)' % (
            jsonp, simplejson.dumps({'result': file.read()}))
