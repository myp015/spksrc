Ext.define('SYNO.SDS.Frpc.Instance', {
    extend: 'SYNO.SDS.AppInstance',
    appWindowName: 'SYNO.SDS.Frpc.Main',
    constructor: function() {
        this.callParent(arguments);
    }
});

Ext.define('SYNO.SDS.Frpc.Main', {
    extend: 'SYNO.SDS.AppWindow',
    appInstance: null,

    constructor: function(cfg) {
        this.appInstance = cfg.appInstance;

        var config = Ext.apply({
            resizable: true,
            maximizable: true,
            minimizable: true,
            width: 900,
            height: 680,
            layout: 'fit',
            items: [
                new Ext.BoxComponent({
                    height: "100%",
                    html: '<iframe src="/webman/3rdparty/frpc/gettoken.html" frameborder="0" marginheight="0" marginwidth="0" width="100%" height="100%"></iframe>'
                })
            ]
        }, cfg);

        this.callParent([config]);
    }
});
