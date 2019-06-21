define(['base/js/namespace', 'base/js/utils'], function(Jupyter, utils) {
    function load_ipython_extension() {

        var handler = function () {
	    var payload = {};
            payload.notebook = Jupyter.notebook.notebook_path;

	    var success = function(data){
		if(data.resp == "success"){
			location.reload();
                }
	    };
	    var error = function(err) { console.log(err); } ;
	    utils.ajax(Jupyter.notebook.base_url + "/plutoDl", {
		type: "POST",
		cache: false,
		dataType: "json",
		success: success,
		error: error,
		data: JSON.stringify(payload),
		contentType: 'application/json'
	    });
        };

	
        var action = {
            icon: 'fa fa-cloud-download', // a font-awesome class used on buttons, etc
            help    : 'download github version of this file',
            help_index : 'zz',
            handler : handler
        };
        var prefix = 'download file from github';
        var action_name = 'sync-git';

        var full_action_name = Jupyter.actions.register(action, action_name, prefix); // returns 'my_extension:show-alert'
        Jupyter.toolbar.add_buttons_group([full_action_name]);
    }

    return {
        load_ipython_extension: load_ipython_extension
    };
});
