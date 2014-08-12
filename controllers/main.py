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
import itertools
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

fields_ranking = {
    'member_id':      0,
    'm_name':         1,
    'm_level':        2,
    'total_money':    3,
    'cost_moneys':    4,
    'moneys':         5,
    'rule_money':     6,
    'points':         7,
    'rule_point':     8,
    'rule_active':    9,
    'card_status':   10,
    'name':          11,
    'm_normal':      12,
    'm_loss':        13,
    'm_off':         14,
    'm_sex':         15,
    'm_telephone':   16,
    'm_birthdate':   17,
    'm_identity_no': 18,
    'm_email':       19,
    'm_address':     20,
    'type':          21,
    'user_id':       22,
    'date':          23,
    'comment':       24,
}
def field_cmp(x,y):
    x = fields_ranking.get(x, 999)
    y = fields_ranking.get(y, 999)
    if x < y:
        return -1
    elif x == y:
        return  0
    else:
        return 1
    
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

                    discount = member_data.m_level.percent
                    if discount == 0:
                        discount = 100                    
                    member_info['discount'] = "%.2f" % (discount / float(100))
                    
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
                                                money=last_money,)
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
            f.extract(file,self.path)
    
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
        field_names.sort(cmp=field_cmp)
        import_data = Model.export_data(ids, field_names, self.raw_data, context=request.context).get('datas',[])
        columns_headers = field_names
        self.data2csv(modename,columns_headers,import_data)
        
    def data2csv(self, modename,fields, rows):
        fullpath = os.path.join(self.path,modename+'.csv')
        fp = file(fullpath,'wb+')
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

        writer.writerow([name.encode('utf-8') for name in fields])

        for data in rows:
            writer.writerow(self._row(data))
        fp.close()
        
    def _row(self,data):
        row = []
        for d in data:
            if isinstance(d, basestring):
                d = d.replace('\n',' ').replace('\t',' ')
                try:
                    d = d.encode('utf-8')
                except UnicodeError:
                    pass
            if d is False: d = ''
            if d is None: d = ''
            row.append(d)
        return row
    
    @http.route('/vip_import/set_file')
    def set_file(self, req, file, jsonp='callback'):
        res = {'flag':False,
               'info':'',
               'result':{}}
        
        try:
            self.extract_file(file)
        except:
            res['info'] = u'上传文件失败！'
            return res
        
        res['flag'] = True
        res['result'] = self.read_csv()
        return 'window.top.%s(%s)' % (
            jsonp, simplejson.dumps(res))
        
    def read_csv(self):
        options = {"headers":True,"encoding":"utf-8","separator":",","quoting":"\""}
        count = 10000
        res = {}
        tmp = os.getcwd()
        os.chdir(self.path)
        for i in os.listdir(os.getcwd()):
            if i.endswith('.csv'):
                res_model = i[:-4]
                Model = request.session.model(res_model)
                fields = Model.fields_get()
                rows = self._read_csv(open(i).readlines(),options)
                os.remove(i)
                headers, matches = self._match_headers(rows, fields, options)
                if "member_id" in headers:
                    id_index = headers.index("member_id")
                    preview = {}
                    back = list(itertools.islice(rows, count))
                    for cow in back:
                        ids = Model.search([('member_id','=',cow[id_index])], 0, False, False, request.context)
                        data = Model.export_data(ids, headers, self.raw_data, context=request.context).get('datas',[])
                        back_tmp = self._row(cow)
                        db_tmp = self._row(data[0])
                        if back_tmp != db_tmp:
                            data_tmp = {
                                "back_data": back_tmp,
                                "db_data":  db_tmp,
                            }
                            preview[cow[id_index]] = data_tmp
                    if preview:
                        res[res_model] = {
                        'model': res_model,
                        'fields': fields,
                        'matches': matches or False,
                        'headers': headers or False,
                        'preview': preview,
                        }
        os.chdir(tmp)
        return res
    
    def _read_csv(self, csvfile, options):
        """ Returns a CSV-parsed iterator of all empty lines in the file

        :throws csv.Error: if an error is detected during CSV parsing
        :throws UnicodeDecodeError: if ``options.encoding`` is incorrect
        """
        csv_iterator = csv.reader(
            csvfile,
            quotechar=str(options['quoting']),
            delimiter=str(options['separator']))
        csv_nonempty = itertools.ifilter(None, csv_iterator)
        # TODO: guess encoding with chardet? Or https://github.com/aadsm/jschardet
        encoding = options.get('encoding', 'utf-8')
        return itertools.imap(
            lambda row: [item.decode(encoding) for item in row],
            csv_nonempty)
        
    def ifilter_data(self,data):
        res = []
        for i in data:
            if i == '':
                i = False
            res.append(i)
        return res
                
        
    def _match_headers(self, rows, fields, options):
        """ Attempts to match the imported model's fields to the
        titles of the parsed CSV file, if the file is supposed to have
        headers.

        Will consume the first line of the ``rows`` iterator.

        Returns a pair of (None, None) if headers were not requested
        or the list of headers and a dict mapping cell indices
        to key paths in the ``fields`` tree

        :param Iterator rows:
        :param dict fields:
        :param dict options:
        :rtype: (None, None) | (list(str), dict(int: list(str)))
        """
        if not options.get('headers'):
            return None, None

        headers = next(rows)
        return headers, dict(
            (index, [field['name'] for field in self._match_header(header, fields, options)] or None)
            for index, header in enumerate(headers)
        )
        
    def _match_header(self, header, fields, options):
        """ Attempts to match a given header to a field of the
        imported model.

        :param str header: header name from the CSV file
        :param fields:
        :param dict options:
        :returns: an empty list if the header couldn't be matched, or
                  all the fields to traverse
        :rtype: list(Field)
        """
        for field in fields:
            field_dict = fields[field]
            # FIXME: should match all translations & original
            # TODO: use string distance (levenshtein? hamming?)
            if header == field \
              or header.lower() == field_dict['string'].lower():
                field_dict['name'] = field
                return [field_dict]

        if '/' not in header:
            return []

        # relational field path
        traversal = []
        subfields = fields
        # Iteratively dive into fields tree
        for section in header.split('/'):
            # Strip section in case spaces are added around '/' for
            # readability of paths
            match = self._match_header(section.strip(), subfields, options)
            # Any match failure, exit
            if not match: return []
            # prep subfields for next iteration within match[0]
            field = match[0]
            subfields = field['fields']
            traversal.append(field)
        return traversal
