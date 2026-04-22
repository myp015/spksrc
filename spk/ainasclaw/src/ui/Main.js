Ext.define('SYNO.SDS.AiNasClaw.Instance', {
    extend: 'SYNO.SDS.AppInstance',
    appWindowName: 'SYNO.SDS.AiNasClaw.Main',
    constructor: function() {
        this.callParent(arguments);
    }
});

Ext.define('SYNO.SDS.AiNasClaw.Main', {
    extend: 'SYNO.SDS.AppWindow',
    appInstance: null,

    constructor: function(cfg) {
        this.appInstance = cfg.appInstance;

        // Launch via DSM 3rdparty proxy entry.
        // Add launchApp=1 so index.cgi direct-link guard won't misclassify
        // Package Center iframe open as a blocked direct URL.
        var monitorUrl = '/webman/3rdparty/ainasclaw/index.cgi?launchApp=1';

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
