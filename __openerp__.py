# -*- coding: utf-8 -*-

{
    'name': u'VIP会员管理',
    'version': '0.1',
    'category': u'VIP会员管理',
    'sequence': 5,
    'summary': u'Small Pos VIP会员预付款、积分管理',
    'description': u"""
通过会员管理，企业就可以记录所有会员客户的资料，了解用户的兴趣爱好、消费特 \
点、意向需求 等；同时针对客户的需求，为其提供优质的个性化服务；会员管理系统还能 \
为企业的产品开发、事业发展提供可靠的市场调研数据，是企业经营不可或缺的一个有利 \
工具。

该会员管理具有如下功能:
-----------------------
    * 会员资料管理
    * 会员积分管理
    * 防数据丢失，轻松备份。
    * 报表
    """,
    'author': 'SmallPos Co. Ltd.',
    'depends': ['base'],
    'data': [
        'security/vip_membership_security.xml',
        'security/ir.model.access.csv',
        'wizard/member_active_view.xml',
        'wizard/member_charge_view.xml',
        'wizard/member_loss_view.xml',
        'wizard/member_off_view.xml',
        'wizard/member_pwd_view.xml',
        'wizard/vip_member_details.xml',
        'wizard/vip_charge_details.xml',
        'wizard/vip_pay_details.xml',
        'wizard/vip_points_details.xml',
        'wizard/pro_exchange_view.xml',
        'vip_membership_view.xml', 
        'vip_membership_data.xml',
        'vip_membership_report.xml'
    ],
    'js' : [
        "static/src/js/*.js",
    ],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
