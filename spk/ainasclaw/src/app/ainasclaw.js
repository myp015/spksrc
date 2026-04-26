Ext.ns('SYNOCOMMUNITY.AiNasClaw');

SYNOCOMMUNITY.AiNasClaw.API_BASE = '/webman/3rdparty/ainasclaw/index.cgi?native_api=1&action=';

SYNOCOMMUNITY.AiNasClaw.api = function(action, method, payload, onSuccess, onFailure) {
    Ext.Ajax.request({
        url: SYNOCOMMUNITY.AiNasClaw.API_BASE + action,
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

SYNOCOMMUNITY.AiNasClaw.pretty = function(data) {
    return Ext.util.JSON.encode(data, true);
};

SYNOCOMMUNITY.AiNasClaw.makeJsonEditorPanel = function(title, loadAction, saveAction, options) {
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
                SYNOCOMMUNITY.AiNasClaw.api(loadAction, 'GET', null, function(data) {
                    editor.setValue(SYNOCOMMUNITY.AiNasClaw.pretty(data));
                });
            }
        }].concat(options.readOnly ? [] : [{
            text: '保存',
            handler: function() {
                try {
                    var payload = Ext.decode(editor.getValue());
                    SYNOCOMMUNITY.AiNasClaw.api(saveAction, 'POST', payload, function(data) {
                        Ext.Msg.alert('AiNasClaw', title + ' 已提交');
                        editor.setValue(SYNOCOMMUNITY.AiNasClaw.pretty(data));
                    }, function(resp) {
                        Ext.Msg.alert('AiNasClaw', '保存失败: HTTP ' + resp.status);
                    });
                } catch (e) {
                    Ext.Msg.alert('AiNasClaw', 'JSON 格式错误: ' + e.message);
                }
            }
        }]),
        items: [editor],
        listeners: {
            activate: function() {
                SYNOCOMMUNITY.AiNasClaw.api(loadAction, 'GET', null, function(data) {
                    editor.setValue(SYNOCOMMUNITY.AiNasClaw.pretty(data));
                });
            }
        }
    });
};

SYNOCOMMUNITY.AiNasClaw.AppInstance = Ext.extend(SYNO.SDS.AppInstance, {
    appWindowName: 'SYNOCOMMUNITY.AiNasClaw.AppWindow',
    constructor: function () {
        SYNOCOMMUNITY.AiNasClaw.AppInstance.superclass.constructor.apply(this, arguments);
    }
});

SYNOCOMMUNITY.AiNasClaw.AppWindow = Ext.extend(SYNO.SDS.AppWindow, {
    appInstance: null,

    constructor: function (config) {
        this.appInstance = config.appInstance;

        // Package Center opens via a marked launch path.
        // `launchApp=1` without marker should be blocked as direct link.
        var monitorUrl = '/webman/3rdparty/ainasclaw/index.cgi?launchApp=1&fromApp=1';

        config = Ext.apply({
            resizable: true,
            maximizable: true,
            minimizable: true,
            width: 1280,
            height: 860,
            layout: 'fit',
            border: false,
            cls: 'synocommunity-ainasclaw',
            items: [
                new Ext.BoxComponent({
                    height: '100%',
                    html: '<iframe src="' + monitorUrl + '" frameborder="0" marginheight="0" marginwidth="0" width="100%" height="100%"></iframe>'
                })
            ]
        }, config);

        SYNOCOMMUNITY.AiNasClaw.AppWindow.superclass.constructor.call(this, config);
    }
});
