define(['base/js/namespace', 'base/js/utils'], function(Jupyter, utils) {
    function load_ipython_extension() {
		Jupyter.notebook.kernel.comm_manager.register_target('progress_msg_comm_target',
			function(comm, msg) {
				// comm is the frontend comm instance
				// msg is the comm_open message, which can carry data

				// Register handlers for later messages:
				comm.on_msg(function(msg) {
					Console.log(msg);
				});
				comm.on_close(function(msg) {});
			});
    }

    return {
        load_ipython_extension: load_ipython_extension
    };
});
