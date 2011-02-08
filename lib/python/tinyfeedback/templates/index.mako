<html>
    <head>
        <link href='/static/css/style.css' type='text/css' rel='stylesheet' />
        <script type='text/javascript' src='static/js/protovis-r3.2.js'></script>
    </head>
    <body>
        <%include file="protovis.mako"/>
        <%include file="login.mako" args="username='${username}'"/>

        % if username is not None:
            <h2>dashboard
            % if edit is not None:
                <a href='/edit'>add</a> <a href='/'>cancel</a>
            % else:
                <a href='/?edit=true'>edit</a>
            % endif
            </h2>
            <table class='graph'>
            % if len(graphs) == 0:
                <tr><td>Want custom graphs? ^ Click up there!</td></tr>
            % endif
            % for index, (graph_name, graph_name_urlencoded, graph_type, graph_type_urlencoded, timescale, time_per_data_point, fields_urlencoded, line_names, data, current_time, length, max_value) in enumerate(graphs):
                % if index % 2 == 0:
                    <tr>
                % endif
                <td>
                    <h3>${graph_name}</h3>
                    % if edit is not None:
                        <a href='/edit?title=${graph_name_urlencoded}&timescale=${timescale}&graph_type=${graph_type_urlencoded}&${fields_urlencoded}'>edit</a>
                        <a href='/edit?title=${graph_name_urlencoded}&delete=true'>remove</a>
                    % endif
                    <a href='/graph?title=${graph_name_urlencoded}&timescale=${timescale}&graph_type=${graph_type_urlencoded}&${fields_urlencoded}'>
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
                    <br />
                </td>
                % if index % 2 != 0:
                    </tr>
                %endif
            % endfor
            % if len(graphs) % 2 != 0:
                </tr>
            % endif
            </table>
            <br />
        % endif
        <h2><a class='nav' href='/'>tf</a></h2>
        <ul>
            % for each in components:
                <li><a href='/view/${each}'>${each}</a></li>
            % endfor
        </ul>
    </body>
</html>
