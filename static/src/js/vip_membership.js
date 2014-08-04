openerp.vip_membership = function (instance) {
    _t = instance.web._t;
    instance.web.client_actions.add('vip.membership.export.manual', 'instance.web.vip_export');
    instance.web.vip_export = instance.web.Widget.extend({
    template: 'VIPExportView',
    dialog_title: {toString: function () { return _t("导出数据"); }},
    events: {
        'click .oe_list_export': 'on_click_export_data',
    },
    init: function(parent) {
        var self = this;
        this._super(parent);
    },
    start: function() {
        var self = this;
        $('.oe_list_save').addClass('oe_hidden');
    },
    on_click_export_data: function() {
        var self = this;
        
        var chk_value =[];
        self.$el.find('input[name="backup"]:checked').each(function(){
            chk_value.push($(this).val());    
        });
        if (chk_value.length == 0){
            alert('请选择需要备份的数据！');
        } else {
            instance.web.blockUI();
            this.session.get_file({
                url: '/vip_membership/export/zip',
                data: {data: chk_value},
                complete: instance.web.unblockUI,
                });
        }
    },
});
    instance.web.client_actions.add('vip.membership.import.file', 'instance.web.vip_import_file');
    instance.web.vip_import_file = instance.web.Widget.extend({
    template: 'VIPImportView',
    dialog_title: {toString: function () { return _t("导入数据"); }},
    events: {
        'click .oe_list_import': 'on_click_import_data',
        'change .oe_import_file': 'loaded_file',
        'click .oe_import_file_reload': 'loaded_file',
    },
    init: function(parent) {
        var self = this;
        this._super(parent);
    },
    start: function() {
        var self = this;
    },

    loaded_file: function () {
        alert("aaa");
        var ajax_option=
        {
            url:"/vip_import/set_file",
            success:function(data){
                alert(data);
            },
        };
        console.log(this.$el.find('form.oe_import'));
        this.$el.find('form.oe_import').ajaxSubmit(ajax_option);
    },
    settings_changed: function(){
        alert('settings_changed');
    },
    on_click_export_data: function() {
        var self = this;
        
        var chk_value =[];
        self.$el.find('input[name="backup"]:checked').each(function(){
            chk_value.push($(this).val());    
        });
        if (chk_value.length == 0){
            alert('请选择需要备份的数据！');
        } else {
            instance.web.blockUI();
            this.session.get_file({
                url: '/vip_membership/export/zip',
                data: {data: chk_value},
                complete: instance.web.unblockUI,
                });
        }
    },
    });
};
