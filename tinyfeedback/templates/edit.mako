<html>
    <head>
        <link href='/static/css/style.css' type='text/css' rel='stylesheet' />
    </head>
    <body>
        <%include file="login.mako" args="username='${username}'"/>
        % if 'error' in kwargs:
            <h2 class='error'>
            % if kwargs['error'] == 'no_title':
                You must specify a title
            % elif kwargs['error'] == 'no_fields':
                You must specify at least one field
            % endif
            </h2>
        % endif
        <h2><a class='nav' href='/'>tf</a></h2>
        <h2>setup custom graph</h2>
        <form action='/edit' method='post'>
            Title: <input type='text' size=30 name='title' value="${kwargs['title']}"/>
            <p>Timescale: <select name='timescale'>
            % for each_timescale in timescales:
                % if 'timescale' in kwargs and each_timescale == kwargs['timescale']:
                    <option selected value=${each_timescale}>${each_timescale}</option>
                % else:
                    <option value=${each_timescale}>${each_timescale}</option>
                % endif
            % endfor
            </select></p>
            <p>Graph Type: <select name='graph_type'>
            % for graph_type in graph_types:
                % if 'graph_type' in kwargs and graph_type == kwargs['graph_type']:
                    <option selected value=${graph_type}>${graph_type}</option>
                % elif 'graph_type' not in  kwargs:
                    <option selected value='line'>line</option>
                % else:
                    <option value=${graph_type}>${graph_type}</option>
                % endif
            % endfor
            </select></p>
            % for component, metrics in data_sources.iteritems():
                <p>${component}</p>
                % for metric in metrics:
                    % if '%s|%s' % (component, metric) in kwargs:
                        <input type='checkbox' name='${component}|${metric}' value='true' checked='checked'/> ${metric}<br />
                    % else:
                        <input type='checkbox' name='${component}|${metric}' value='true' /> ${metric}<br />
                    % endif
                % endfor
            % endfor
            <br />
            <input type='submit' value='save' />
        </form>
    </body>
</html>
