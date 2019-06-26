function getXsrfToken(){
    var name = '_xsrf';
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

define(['base/js/namespace', 'base/js/utils'], function(Jupyter, utils) {
    function load_ipython_extension() {

        var handler = function () {
	    Jupyter.notebook.save_notebook(false);
            Jupyter.notebook.restart_clear_output({confirm: false});
	    var payload = {};
            payload.notebook = Jupyter.notebook.notebook_path;

	    var error = err => { 
                console.log("ERROR: " + err); 
            } ;

            var xsrf_token = getXsrfToken();
            var lastResponseLength = false;

            //modified from: https://gist.github.com/sohelrana820/63f029d3aa12936afbc50eb785c496c0
	    $.ajax(Jupyter.notebook.base_url + "/plutoEx", {
		type: "POST",
		cache: false,
		dataType: "text",
		success: data => {},
		error: error,
		data: JSON.stringify(payload),
		contentType: 'application/json',
                headers: {
                    'X-XSRFToken': xsrf_token
                },
                processData: false,
                xhrFields: {
                    onprogress: function(e){
                        var progressResponse;
                        var response = e.currentTarget.response;
                        if(lastResponseLength === false){
                            progressResponse = response;
                            lastResponseLength = response.length;
                        } else {
                            progressResponse = response.substring(lastResponseLength);
                            lastResponseLength = response.length;
                        }
                        //console.log("STATUS: " + progressResponse);
                        var parsedResponse = JSON.parse(progressResponse);

                        if (parsedResponse.ok) {
                            Jupyter.notification_area.widget_dict["notebook"].info(parsedResponse.text);
                            if (parsedResponse.finished){
                                location.reload();
                            }
                        } else {
                            Jupyter.notification_area.widget_dict["notebook"].danger("Error!");
                            console.log(parsedResponse.text);
                        }
                    }
                }
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
