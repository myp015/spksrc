Ext.ns('SYNOCOMMUNITY.OpenClaw2');

SYNOCOMMUNITY.OpenClaw2.apiBase = '/webman/3rdparty/openclaw2/index.cgi?native_api=1&action=';

SYNOCOMMUNITY.OpenClaw2.loadInto = function(panel, action, renderer) {
    panel.body.update('<div style="padding:16px;color:#666;">加载中…</div>');
    Ext.Ajax.request({
        url: SYNOCOMMUNITY.OpenClaw2.apiBase + action,
        method: 'GET',
        success: function(resp) {
            var data = {};
            try { data = Ext.decode(resp.responseText); } catch (e) { data = { error: 'JSON parse failed', raw: resp.responseText }; }
            renderer(panel, data);
        },
        failure: function(resp) {
            panel.body.update('<div style="padding:16px;color:#c00;">加载失败：HTTP ' + resp.status + '</div>');
        }
    });
};

SYNOCOMMUNITY.OpenClaw2.renderJson = function(panel, title, data) {
    var html = '<div style="padding:16px;">'
        + '<div style="font-size:18px;font-weight:600;margin-bottom:12px;">' + title + '</div>'
        + '<pre style="white-space:pre-wrap;word-break:break-word;background:#f7f7f7;border:1px solid #ddd;border-radius:6px;padding:12px;max-height:620px;overflow:auto;">'
        + Ext.util.Format.htmlEncode(Ext.encode(data))
        + '</pre></div>';
    panel.body.update(html);
};

SYNOCOMMUNITY.OpenClaw2.renderOverview = function(panel, data) {
    var rows = [
        ['实例', data.instanceId || '-'],
        ['显示名', data.displayName || '-'],
        ['已安装', data.installed ? '是' : '否'],
        ['运行中', data.running ? '是' : '否'],
        ['版本', data.version || '-'],
        ['端口', data.port || '-'],
        ['代理路径', data.proxyBasePath || '-']
    ];
    var html = '<div style="padding:16px;">'
        + '<div style="font-size:18px;font-weight:600;margin-bottom:12px;">概览</div>'
        + '<table style="width:100%;border-collapse:collapse;">';
    for (var i = 0; i < rows.length; i++) {
        html += '<tr>'
             + '<td style="width:160px;padding:10px;border-bottom:1px solid #eee;color:#666;">' + rows[i][0] + '</td>'
             + '<td style="padding:10px;border-bottom:1px solid #eee;">' + Ext.util.Format.htmlEncode(String(rows[i][1])) + '</td>'
             + '</tr>';
    }
    html += '</table>';
    if (data.dashboardUrl) {
        html += '<div style="margin-top:16px;"><a href="' + data.dashboardUrl + '" target="_blank">打开 Dashboard</a></div>';
    }
    html += '</div>';
    panel.body.update(html);
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

        var overviewPanel = new Ext.Panel({
            title: '概览',
            autoScroll: true,
            listeners: {
                activate: function(p) { SYNOCOMMUNITY.OpenClaw2.loadInto(p, 'status', SYNOCOMMUNITY.OpenClaw2.renderOverview); }
            }
        });
        var modelsPanel = new Ext.Panel({
            title: '模型配置',
            autoScroll: true,
            listeners: {
                activate: function(p) { SYNOCOMMUNITY.OpenClaw2.loadInto(p, 'models', function(panel, data){ SYNOCOMMUNITY.OpenClaw2.renderJson(panel, '模型配置', data); }); }
            }
        });
        var channelsPanel = new Ext.Panel({
            title: '消息渠道',
            autoScroll: true,
            listeners: {
                activate: function(p) { SYNOCOMMUNITY.OpenClaw2.loadInto(p, 'channels', function(panel, data){ SYNOCOMMUNITY.OpenClaw2.renderJson(panel, '消息渠道', data); }); }
            }
        });
        var logsPanel = new Ext.Panel({
            title: '运行日志',
            autoScroll: true,
            listeners: {
                activate: function(p) { SYNOCOMMUNITY.OpenClaw2.loadInto(p, 'logs', function(panel, data){ panel.body.update('<div style="padding:16px;"><div style="font-size:18px;font-weight:600;margin-bottom:12px;">运行日志</div><pre style="white-space:pre-wrap;word-break:break-word;background:#111;color:#ddd;border-radius:6px;padding:12px;max-height:620px;overflow:auto;">' + Ext.util.Format.htmlEncode(data.log || '') + '</pre></div>'); }); }
            }
        });

        var tabs = new Ext.TabPanel({
            activeTab: 0,
            deferredRender: false,
            border: false,
            items: [overviewPanel, modelsPanel, channelsPanel, logsPanel]
        });

        config = Ext.apply({
            resizable: true,
            maximizable: true,
            minimizable: true,
            width: 1100,
            height: 760,
            layout: 'fit',
            border: false,
            cls: 'synocommunity-openclaw2',
            items: [tabs]
        }, config);

        SYNOCOMMUNITY.OpenClaw2.AppWindow.superclass.constructor.call(this, config);
    }
});
