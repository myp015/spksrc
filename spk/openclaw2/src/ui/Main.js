Ext.define('SYNO.SDS.OpenClaw2.Instance', {
    extend: 'SYNO.SDS.AppInstance',
    appWindowName: 'SYNO.SDS.OpenClaw2.Main',
    constructor: function() {
        this.callParent(arguments);
    }
});

Ext.define('SYNO.SDS.OpenClaw2.Main', {
    extend: 'SYNO.SDS.AppWindow',
    appInstance: null,

    constructor: function(cfg) {
        this.appInstance = cfg.appInstance;

        // If DSM still launches ui/Main.js path, force top-level jump to panel path
        // to avoid nested backend shell.
        var monitorUrl = '/webman/3rdparty/openclaw2/index.cgi?proxy=1&path=/app/trim-openclaw/';

        var config = Ext.apply({
            resizable: true,
            maximizable: true,
            minimizable: true,
            width: 1280,
            height: 820,
            layout: 'fit',
            items: [
                new Ext.BoxComponent({
                    height: '100%',
                    html: '<div style="padding:16px;font-size:14px;color:#666;">正在打开 OpenClaw2 面板…</div>' +
                          '<script>(function(){var u="' + monitorUrl + '";try{if(window.top&&window.top!==window){window.top.location.href=u;}else{window.location.href=u;}}catch(e){window.location.href=u;}})();</script>'
                })
            ]
        }, cfg);

        this.callParent([config]);
    }
});
