Ext.ns('SYNOCOMMUNITY.OpenClaw2');

SYNOCOMMUNITY.OpenClaw2.API_BASE = '/webman/3rdparty/openclaw2/index.cgi?native_api=1&action=';

SYNOCOMMUNITY.OpenClaw2.api = function(action, method, payload, onSuccess, onFailure) {
    Ext.Ajax.request({
        url: SYNOCOMMUNITY.OpenClaw2.API_BASE + action,
        method: method || 'GET',
        jsonData: payload || null,
        headers: { 'Content-Type': 'application/json' },
        success: function(resp) {
            var data = {};
            try { data = resp.responseText ? Ext.decode(resp.responseText) : {}; }
            catch (e) { data = { error: 'JSON parse failed', raw: resp.responseText }; }
            if (onSuccess) { onSuccess(data); }
        },
        failure: function(resp) {
            if (onFailure) { onFailure(resp); }
        }
    });
};

SYNOCOMMUNITY.OpenClaw2.pretty = function(data) {
    return Ext.util.JSON.encode(data, true);
};

SYNOCOMMUNITY.OpenClaw2.makeJsonEditorPanel = function(title, loadAction, saveAction, options) {
    options = options || {};
    var editor = new Ext.form.TextArea({
        style: 'font-family: ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;',
        value: '',
        grow: false,
        height: options.height || 560,
        readOnly: !!options.readOnly
    });
    return new Ext.Panel({
        title: title,
        layout: 'fit',
        tbar: [{
            text: '刷新',
            handler: function() {
                SYNOCOMMUNITY.OpenClaw2.api(loadAction, 'GET', null, function(data) {
                    editor.setValue(SYNOCOMMUNITY.OpenClaw2.pretty(data));
                });
            }
        }].concat(options.readOnly ? [] : [{
            text: '保存',
            handler: function() {
                try {
                    var payload = Ext.decode(editor.getValue());
                    SYNOCOMMUNITY.OpenClaw2.api(saveAction, 'POST', payload, function(data) {
                        Ext.Msg.alert('OpenClaw2', title + ' 已提交');
                        editor.setValue(SYNOCOMMUNITY.OpenClaw2.pretty(data));
                    }, function(resp) {
                        Ext.Msg.alert('OpenClaw2', '保存失败: HTTP ' + resp.status);
                    });
                } catch (e) {
                    Ext.Msg.alert('OpenClaw2', 'JSON 格式错误: ' + e.message);
                }
            }
        }]),
        items: [editor],
        listeners: {
            activate: function() {
                SYNOCOMMUNITY.OpenClaw2.api(loadAction, 'GET', null, function(data) {
                    editor.setValue(SYNOCOMMUNITY.OpenClaw2.pretty(data));
                });
            }
        }
    });
};

SYNOCOMMUNITY.OpenClaw2.AppInstance = Ext.extend(SYNO.SDS.AppInstance, {
    appWindowName: 'SYNOCOMMUNITY.OpenClaw2.AppWindow',
    constructor: function () {
        SYNOCOMMUNITY.OpenClaw2.AppInstance.superclass.constructor.apply(this, arguments);
    }
});

SYNOCOMMUNITY.OpenClaw2.AppWindow = Ext.extend(SYNO.SDS.AppWindow, {
    appInstance: null,

    constructor: function (config) {
        this.appInstance = config.appInstance;

        var overviewTpl = new Ext.XTemplate(
            '<div style="padding:16px;">',
              '<h2 style="margin:0 0 12px;">概览</h2>',
              '<table style="width:100%;border-collapse:collapse;">',
                '<tr><td style="width:180px;padding:10px;border-bottom:1px solid #eee;color:#666;">实例 ID</td><td style="padding:10px;border-bottom:1px solid #eee;">{instanceId}</td></tr>',
                '<tr><td style="padding:10px;border-bottom:1px solid #eee;color:#666;">显示名</td><td style="padding:10px;border-bottom:1px solid #eee;">{displayName}</td></tr>',
                '<tr><td style="padding:10px;border-bottom:1px solid #eee;color:#666;">已安装</td><td style="padding:10px;border-bottom:1px solid #eee;">{[values.installed ? "是" : "否"]}</td></tr>',
                '<tr><td style="padding:10px;border-bottom:1px solid #eee;color:#666;">运行中</td><td style="padding:10px;border-bottom:1px solid #eee;">{[values.running ? "是" : "否"]}</td></tr>',
                '<tr><td style="padding:10px;border-bottom:1px solid #eee;color:#666;">版本</td><td style="padding:10px;border-bottom:1px solid #eee;">{version}</td></tr>',
                '<tr><td style="padding:10px;border-bottom:1px solid #eee;color:#666;">端口</td><td style="padding:10px;border-bottom:1px solid #eee;">{port}</td></tr>',
                '<tr><td style="padding:10px;border-bottom:1px solid #eee;color:#666;">代理路径</td><td style="padding:10px;border-bottom:1px solid #eee;">{proxyBasePath}</td></tr>',
              '</table>',
            '</div>'
        );

        var overviewPanel = new Ext.Panel({
            title: '概览',
            autoScroll: true,
            listeners: {
                activate: function(p) {
                    p.body.update('<div style="padding:16px;color:#666;">加载中…</div>');
                    SYNOCOMMUNITY.OpenClaw2.api('status', 'GET', null, function(data) { overviewTpl.overwrite(p.body, data || {}); });
                }
            }
        });

        var modelsPanel = SYNOCOMMUNITY.OpenClaw2.makeJsonEditorPanel('模型配置', 'models', 'models_save');
        var channelsPanel = SYNOCOMMUNITY.OpenClaw2.makeJsonEditorPanel('消息渠道', 'channels', 'channels_save');
        var pluginsPanel = SYNOCOMMUNITY.OpenClaw2.makeJsonEditorPanel('插件管理', 'plugins', 'plugin_install');
        pluginsPanel.getTopToolbar().add({
            text: '刷新插件状态',
            handler: function() {
                SYNOCOMMUNITY.OpenClaw2.api('plugins_refresh', 'POST', {}, function(data) {
                    pluginsPanel.items.get(0).setValue(SYNOCOMMUNITY.OpenClaw2.pretty(data));
                });
            }
        });

        var installPanel = SYNOCOMMUNITY.OpenClaw2.makeJsonEditorPanel('安装 / 控制', 'install', 'install_run');
        var governorPanel = SYNOCOMMUNITY.OpenClaw2.makeJsonEditorPanel('进程治理', 'process_governor', null, { readOnly: true });
        var logsPanel = SYNOCOMMUNITY.OpenClaw2.makeJsonEditorPanel('运行日志', 'logs', null, { readOnly: true, height: 560 });
        logsPanel.items.get(0).setStyle('background', '#111');
        logsPanel.items.get(0).setStyle('color', '#ddd');

        var tabs = new Ext.TabPanel({
            activeTab: 0,
            deferredRender: false,
            border: false,
            items: [overviewPanel, modelsPanel, channelsPanel, pluginsPanel, installPanel, governorPanel, logsPanel]
        });

        config = Ext.apply({
            resizable: true,
            maximizable: true,
            minimizable: true,
            width: 1240,
            height: 860,
            layout: 'fit',
            border: false,
            cls: 'synocommunity-openclaw2',
            items: [tabs]
        }, config);

        SYNOCOMMUNITY.OpenClaw2.AppWindow.superclass.constructor.call(this, config);
    }
});
