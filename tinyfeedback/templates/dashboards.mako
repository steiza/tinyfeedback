<!DOCTYPE html>
<meta charset='utf-8'>
<html>
    <head>
        <link href='/static/css/style.css' type='text/css' rel='stylesheet' />
    </head>
    <body>
        <%include file="login.mako" args="username='${username}'"/>
        <h2><a class='nav' href='/'>tf</a> :: dashboards</h2>
        <h2>Known users</h2>
        % if len(graphs_per_user) == 0:
            None yet! Log in above!
        % else:
            <ul>
                % for username, graph_count in graphs_per_user:
                    <li>
                        <a href='/dashboards/${username}'>${username}'s dashboard</a>
                        - ${graph_count}
                        % if graph_count == 1:
                            graph
                        % else:
                            graphs
                        % endif
                    </li>
                % endfor
            </ul>
        % endif
    </body>
</html>
