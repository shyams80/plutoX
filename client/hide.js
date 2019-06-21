define(['base/js/namespace', 'base/js/utils'], function(Jupyter, utils) {
    function load_ipython_extension() {

        var handler = function () {
	    Jupyter.notebook.save_notebook(false);
	    var payload = {};
            payload.notebook = Jupyter.notebook.notebook_path;

	    var success = function(data){
		if(data.resp == "success"){
			location.reload();
                }
	    };
	    var error = function(err) { console.log(err); } ;
	    utils.ajax(Jupyter.notebook.base_url + "/plutoEx", {
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
            icon: 'fa-play-circle-o ', // a font-awesome class used on buttons, etc
            help    : 'upload and run',
            help_index : 'zz',
            handler : handler
        };
        var prefix = 'upload and run_extension';
        var action_name = 'upload-run';

        var full_action_name = Jupyter.actions.register(action, action_name, prefix); // returns 'my_extension:show-alert'
        Jupyter.toolbar.add_buttons_group([full_action_name]);
	$("li[id*=run_]").each(function(){
		$(this).hide();
	});
	$("[id='run_int']").hide();
	delete Jupyter.actions._actions["jupyter-notebook:run-cell-and-select-next"];
	delete Jupyter.actions._actions["jupyter-notebook:run-cell"];
	delete Jupyter.actions._actions["jupyter-notebook:run-cell-and-insert-below"];
	delete Jupyter.actions._actions["jupyter-notebook:run-all-cells"];
	delete Jupyter.actions._actions["jupyter-notebook:run-all-cells-above"];
	delete Jupyter.actions._actions["jupyter-notebook:run-all-cells-below"];
	delete Jupyter.actions._actions["jupyter-notebook:restart-kernel-and-run-all-cells"];
	delete Jupyter.actions._actions["jupyter-notebook:confirm-restart-kernel-and-run-all-cells"];
    }

    return {
        load_ipython_extension: load_ipython_extension
    };
});
