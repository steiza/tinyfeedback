<!DOCTYPE html>
<meta charset='utf-8'>
<html>
    <head>
        <link href='/static/css/style.css' type='text/css' rel='stylesheet' />
        <script type='text/javascript' src='/static/js/jquery.min.js'></script>
        <script type='text/javascript' src='/static/js/jquery-ui.min.js'></script>
    </head>
    <body>
        <script type='text/javascript'>
            $(document).ready(function(){
                var update_name = function() {
                    if ($(this).val() != '') {
                        $(this).attr('name', $(this).val());
                    } else {
                        $(this).attr('name', '');
                    }
                }

                function deleteField() {
                    var fieldInList = $(this).parent();
                    $(fieldInList).remove();
                }

                $("#explicit_metrics").delegate('.wildcard', 'change', update_name);
                $("#explicit_metrics").delegate('.wildcard', 'keydown', update_name);
                $("#explicit_metrics").delegate('.delete_field', 'click', deleteField);

                $('#add_field').click(function() {
                    $('#explicit_metrics').append("<li><button class='delete_field' type='button'>x</button><input type='text' class='wildcard' /></li>");
                });

                function updateMetricSearch() {
                    var currentComponent = $('#autocompleteComponent').val();

                    if (currentComponent != "") {
                        var currentComponentIndex = componentsArray.indexOf(currentComponent);
                        $('#autocompleteMetric').autocomplete("option", "source", metricsArray[currentComponentIndex]);
                    }
                    else {
                        $('#autocompleteMetric').autocomplete("option", "source", []);
                    }
                };

                function addSearchedField() {
                    var newField = $("#autocompleteComponent").val() + "|" + $("#autocompleteMetric").val();
                    var openField = $(".wildcard").filter("[name='']").first();

                    openField.attr("value", newField);
                    openField.attr("name", newField);
                    $("#add_field").click();
                    $(".searchbox").attr("value", "");
                    $('#autocompleteMetric').autocomplete("option", "source", []);
                };

                function showFullSearchList(e) {
                    if (e) {
                        if ((e.which == 40) && ($(this).val() == "")) {
                            $(this).autocomplete("search", "");
                        }
                    }
                };

                var componentsArray = [];
                var metricsArray = [];
                % for component, metrics in data_sources.iteritems():
                    metricsArray[componentsArray.length] = [];
                    % for metric in metrics:
                        metricsArray[componentsArray.length].push("${metric}");
                    % endfor
                    componentsArray.push("${component}");
                % endfor

                $("#autocompleteComponent").autocomplete({
                    source: componentsArray,
                    minLength: 0,
                    change: function(event,ui){updateMetricSearch.call();}
                });

                $('#autocompleteMetric').autocomplete({
                    source: [],
                    minLength: 0
                });

                $('#auto_add').click(function(){
                    addSearchedField.call();
                });

                $(".searchbox").keydown(function(e){
                    showFullSearchList.call(e);
                });
            });
        </script>

        <%include file="login.mako" args="username='${username}'"/>
        % if 'error' in kwargs:
            <h2 class='error'>
            % if kwargs['error'] == 'no_title':
                You must specify a title
            % elif kwargs['error'] == 'no_fields':
                You must specify at least one field
            % elif kwargs['error'] == 'bad_wildcard_filter':
                Fields must contain a "|"
            % endif
            </h2>
        % endif

        <h2><a class='nav' href='/'>tf</a> :: edit graph</h2>
        <form action='/edit' method='post'>
            <p>Note that if you modified the graph type or timescale on the previous page those changes are propogated below</p>
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
                % elif 'graph_type' not in kwargs and graph_type == 'line':
                    <option selected value='line'>line</option>
                % else:
                    <option value=${graph_type}>${graph_type}</option>
                % endif
            % endfor
            </select></p>
            <p>
              % if updates_infrequently:
                  <input type='checkbox' name='updates_infrequently' value='true' checked='checked'/>
              % else:
                  <input type='checkbox' name='updates_infrequently' value='true' />
              % endif
              Graph Values Don't Update Once Per Minute (so don't drop values to 0)
            </p>

            <b>Fields</b>
            <p>Search for the specific component and metric you want to add or write it in yourself. Supports wildcard queries i.e. component|metric* or *|metric.</p>
            <table>
                <tr>
                    <td>Component:</td>
                    <td>Metric:</td>
                </tr>
                <tr>
                    <td><input type="text" id="autocompleteComponent" class="searchbox"></td>
                    <td><input type="text" id="autocompleteMetric" class="searchbox"></td>
                    <td><button id="auto_add" type="button">Add</button></td>
                </tr>
            </table>
            <br>
            <ul id='explicit_metrics'>
                % for item in fields:
                        <li><button class="delete_field" type="button">x</button><input type='text' name='${cgi.escape(item)}' value='${cgi.escape(item)}' class='wildcard' /></li>
                % endfor
                <li><button class="delete_field" type="button">x</button><input type='text' class='wildcard' /></li>
            </ul>
            <button id='add_field' type='button'>Add a blank field</button>
            <br><br>
            <input type='submit' value='save' />
            <br>
            <br />
        </form>
    </body>
</html>
