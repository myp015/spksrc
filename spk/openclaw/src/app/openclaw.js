Ext.ns('SYNOCOMMUNITY.OpenClaw');

SYNOCOMMUNITY.OpenClaw.API_BASE = '/webman/3rdparty/openclaw/index.cgi?native_api=1&action=';

SYNOCOMMUNITY.OpenClaw.api = function(action, method, payload, onSuccess, onFailure) {
    Ext.Ajax.request({
        url: SYNOCOMMUNITY.OpenClaw.API_BASE + action,
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

SYNOCOMMUNITY.OpenClaw.AppInstance = Ext.extend(SYNO.SDS.AppInstance, {
    appWindowName: 'SYNOCOMMUNITY.OpenClaw.AppWindow',
    constructor: function () {
        SYNOCOMMUNITY.OpenClaw.AppInstance.superclass.constructor.apply(this, arguments);
    }
});

SYNOCOMMUNITY.OpenClaw.AppWindow = Ext.extend(SYNO.SDS.AppWindow, {
    appInstance: null,

    constructor: function (config) {
        this.appInstance = config.appInstance;

        var monitorUrl = '/webman/3rdparty/openclaw/index.cgi?launchApp=1&fromApp=1';

        config = Ext.apply({
            resizable: true,
            maximizable: true,
            minimizable: true,
            width: 1280,
            height: 860,
            layout: 'fit',
            border: false,
            cls: 'synocommunity-openclaw',
            items: [
                new Ext.BoxComponent({
                    height: '100%',
                    html: '<iframe src="' + monitorUrl + '" frameborder="0" marginheight="0" marginwidth="0" width="100%" height="100%"></iframe>'
                })
            ]
        }, config);

        SYNOCOMMUNITY.OpenClaw.AppWindow.superclass.constructor.call(this, config);
    }
});
