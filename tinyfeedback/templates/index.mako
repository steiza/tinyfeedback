<html>
    <head>
        <link href='/static/css/style.css' type='text/css' rel='stylesheet' />
        <script type='text/javascript' src='/static/js/jquery.min.js'></script>
        <script type='text/javascript' src='static/js/protovis-r3.2.js'></script>
        <script type='text/javascript' src='/static/js/jquery-ui.min.js'></script>
    </head>
    <body>
        % if edit is not None:
            <script>
                function on_update(event, ui) {
                    // HACK: get around bug in jQuery UI that adds script elements
                    $('#sortable').children().remove('script');

                    // Save the new ordering
                    var new_ordering = $.map($('#sortable li'), function (each) {
                        return $(each).attr('id');
                    });

                    $.post('/graph_ordering', {'new_ordering':
                            JSON.stringify(new_ordering)});
                }

                $(function() {
                    $('#sortable').sortable({update: on_update});
                    $('#sortable').disableSelection();
                });
            </script>
        % endif

        <%include file="protovis.mako"/>
        <%include file="login.mako" args="username='${username}'"/>
        <h2><a class='nav' href='/'>tf</a><h2>

        % if username is not None:
            <h2>dashboard
            % if edit is not None:
                <a href='/edit'>new graph</a> <a href='/'>go back</a> <span class='hint'>Drag graphs to re-order them!</span>
            % else:
                <a href='/?edit=true'>edit</a>
            % endif
            </h2>
            % if len(graphs) == 0:
                Want custom graphs? ^ Click up there!
            % endif
            <ul id='sortable'>
            % for index, (graph_name, graph_name_urlencoded, graph_type, graph_type_urlencoded, timescale, time_per_data_point, line_names, data, current_time, length, max_value) in enumerate(graphs):
                <li id='${graph_name}'>
                    <h3>${graph_name}</h3>
                    % if edit is not None:
                        <a href='/edit?title=${graph_name_urlencoded}&timescale=${timescale}&graph_type=${graph_type_urlencoded}'>edit</a>
                        <a href='/edit?title=${graph_name_urlencoded}&delete=true'>remove</a>
                    % endif
                    <a href='/graph/${username}/${graph_name_urlencoded}?timescale=${timescale}&graph_type=${graph_type_urlencoded}'>
                        <script type='text/javascript+protovis'>
                            var line_names = ${line_names};
                            var data = ${data};
                            var max = ${max_value};
                            var length = ${length};
                            var graph_type = '${graph_type}';
                            var time = pv.range(0, ${length}).map(function(x) (
                                    new Date(${current_time} + (x - length)*${time_per_data_point})
                                    ));

                            custom_graph(line_names, data, time, max, graph_type);
                        </script>
                    </a>
                </li>
            % endfor
            </ul>
            <div id='post_float' />
            <br />
        % endif

        <h2><a class='nav' name='components'>Components</a></h2>
        <ul>
            % for each in components:
                <li><a href='/view/${each}'>${each}</a></li>
            % endfor
        </ul>
    </body>
</html>
