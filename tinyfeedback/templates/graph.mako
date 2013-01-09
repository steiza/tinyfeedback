<!DOCTYPE html>
<meta charset='utf-8'>
<html>
    <head>
        <link href='../../static/css/style.css' type='text/css' rel='stylesheet' />
        <script type='text/javascript' src='/static/js/jquery.min.js'></script>
        <script type='text/javascript' src='/static/js/d3.v3.min.js'></script>
        <script type='text/javascript' src='/static/js/jquery-ui.min.js'></script>
    </head>
    <body>
        <div class='tooltip'></div>
        <%include file="d3.mako"/>
        <%include file="login.mako" args="username='${username}'"/>
        <h2><a class='nav' href='/'>tf</a> :: view graph</h2>

        % if username is not None and username != graph_username:
            % for (graph_name, graph_name_urlencoded, graph_type, graph_type_urlencoded, timescale, time_per_data_point, line_names, data, current_time, length, max_value) in graph:
                <form action='/add_graph' method='post'>
                    <input type='hidden' name='graph_username' value='${graph_username}'/>
                    <input type='hidden' name='title' value='${graph_name}'/>
                    <input type='hidden' name='timescale' value='${timescale}'/>
                    <input type='hidden' name='graph_type' value='${graph_type}'/>
                    <input type='submit' value='Add to my dashboard' />
                </form>
            % endfor
        % elif username is None:
            Want this graph on your dasboard? Log in above!
        % endif
        <table class='graph'>
            <tr>
                <td id='graph_0'>
                % for (graph_name, graph_name_urlencoded, graph_type, graph_type_urlencoded, timescale, time_per_data_point, line_names, data, current_time, length, max_value) in graph:
                    <h3>${graph_name}</h3>
                    <script type='text/javascript'>
                        var line_names = ${line_names};
                        var data = ${data};
                        % if force_max_value:
                            var max = ${force_max_value};
                        % else:
                            var max = ${max_value};
                        % endif
                        var length = ${length};
                        var graph_type = '${graph_type}';

                        var time = d3.range(0, ${length});
                        time.forEach(function(each, i) {
                            time[i] = new Date(${current_time} + ((i - ${length}) * ${time_per_data_point}));
                        });

                        custom_graph('graph_0', line_names, data, max, time, ${time_per_data_point}, graph_type, 800, 300);
                    </script>
                % endfor
                </td>
            </tr>
        </table>
    </body>
</html>

