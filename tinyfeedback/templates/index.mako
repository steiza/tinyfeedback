<!DOCTYPE html>
<meta charset='utf-8'>
<html>
    <head>
        <link href='/static/css/style.css' type='text/css' rel='stylesheet' />
        <script type='text/javascript' src='/static/js/jquery.min.js'></script>
        <script type='text/javascript' src='/static/js/d3.v3.min.js'></script>
        <script type='text/javascript' src='/static/js/jquery-ui.min.js'></script>
    </head>
    <body>
        <div class='tooltip'></div>
        % if edit is not None:
            <script>
                function on_update(event, ui) {
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

        <%include file="d3.mako"/>
        <%include file="login.mako" args="username='${username}'"/>
        <h2>
            <a class='nav' href='/'>tf</a> :: <a class='nav' href='/dashboards'>dashboards</a>
            % if dashboard_username:
                :: ${dashboard_username}
            % endif
        </h2>

        % if username is not None or dashboard_username is not None:
            % if edit is not None:
                <a href='/edit'>new graph</a> <a href='/'>cancel</a> <span class='hint'>Drag graphs to re-order them!</span>
            % elif username == dashboard_username:
                <a href='/?edit=true'>edit dashboard</a>
            % endif
            </h2>
            % if len(graphs) == 0:
                % if username == dashboard_username:
                    Want custom graphs? Click edit!
                % else:
                    No graphs yet!
                % endif
            % endif
            <ul id='sortable'>
            % for index, (graph_name, graph_name_urlencoded, graph_type, graph_type_urlencoded, timescale, time_per_data_point, line_names, data, current_time, length, max_value) in enumerate(graphs):
                <li id='${graph_name}'>
                    <h3>${graph_name}</h3>
                    % if edit is not None:
                        <a href='/edit?title=${graph_name_urlencoded}&timescale=${timescale}&graph_type=${graph_type_urlencoded}'>edit</a>
                        <a href='/edit?title=${graph_name_urlencoded}&delete=true'>remove</a>
                    % endif
                    <a class='bare' href='/graph/${dashboard_username}/${graph_name_urlencoded}?timescale=${timescale}&graph_type=${graph_type_urlencoded}'>
                        <span id='graph_${index}'>
                            <script type='text/javascript'>
                                var line_names = ${line_names};
                                var data = ${data};
                                var max = ${max_value};
                                var length = ${length};
                                var graph_type = '${graph_type}';
                                var time = d3.range(0, ${length});
                                time.forEach(function(each, i) {
                                    time[i] = new Date(${current_time} + (i * ${time_per_data_point}));
                                });

                                custom_graph('graph_${index}', line_names, data, max, time, ${time_per_data_point}, graph_type);
                            </script>
                        </span>
                    </a>
                </li>
            % endfor
            </ul>
            <div id='post_float' />
            <br />
        % endif

        % if len(components) > 0:
            <h2><a class='nav' name='components'>Components</a></h2>
            <ul>
                % for each in components:
                    <li><a href='/view/${each}'>${each}</a></li>
                % endfor
            </ul>
        % endif
    </body>
</html>
