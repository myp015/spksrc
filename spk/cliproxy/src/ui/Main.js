Ext.define('SYNO.SDS.CLIProxyAPI.Instance', {
    extend: 'SYNO.SDS.AppInstance',
    appWindowName: 'SYNO.SDS.CLIProxyAPI.Main',
    constructor: function() {
        this.callParent(arguments);
    }
});

Ext.define('SYNO.SDS.CLIProxyAPI.Main', {
    extend: 'SYNO.SDS.AppWindow',
    appInstance: null,

    constructor: function(cfg) {
        this.appInstance = cfg.appInstance;

        var config = Ext.apply({
            resizable: true,
            maximizable: true,
            minimizable: true,
            width: 1200,
            height: 820,
            layout: 'fit',
            items: [
                new Ext.BoxComponent({
                    height: '100%',
                    html: '<iframe src="/webman/3rdparty/cliproxy/index.cgi" frameborder="0" marginheight="0" marginwidth="0" width="100%" height="100%"></iframe>'
                })
            ]
        }, cfg);

        this.callParent([config]);
    }
});
