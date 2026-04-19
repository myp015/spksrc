Ext.ns('SYNOCOMMUNITY.OpenClaw2');

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

        var panelUrl = '/webman/3rdparty/openclaw2/index.cgi';

        config = Ext.apply({
            resizable: true,
            maximizable: true,
            minimizable: true,
            width: 1280,
            height: 820,
            layout: 'fit',
            border: false,
            cls: 'synocommunity-openclaw2',
            items: [{
                xtype: 'box',
                autoEl: {
                    tag: 'iframe',
                    src: panelUrl,
                    frameborder: 0,
                    width: '100%',
                    height: '100%'
                }
            }]
        }, config);

        SYNOCOMMUNITY.OpenClaw2.AppWindow.superclass.constructor.call(this, config);
    }
});
