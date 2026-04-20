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

        // Launch via DSM 3rdparty proxy entry.
        var monitorUrl = '/webman/3rdparty/openclaw2/index.cgi';

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
                    html: '<iframe src="' + monitorUrl + '" frameborder="0" marginheight="0" marginwidth="0" width="100%" height="100%"></iframe>'
                })
            ]
        }, cfg);

        this.callParent([config]);
    }
});
