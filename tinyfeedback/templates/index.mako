<!DOCTYPE html>
<meta charset='utf-8'>
<html>
  <head>
    <link href='/static/css/style.css' type='text/css' rel='stylesheet' />
    <script type='text/javascript' src='/static/js/jquery.min.js'></script>
    <script type='text/javascript' src='/static/js/d3.v3.min.js'></script>
    <script type='text/javascript' src='/static/js/jquery-ui.min.js'></script>
  </head>
  <%include file="d3.mako"/>
  <script type="text/javascript">
    function createGraph(data, index) {
      var title = data[0];
          title_urlencoded = data[1];
          graph_type = data[2];
          graph_type_urlencoded = data[3];
          timescale = data[4];
          time_per_data_point = data[5];
          line_names = data[6];
          data_rows = data[7];
          length = data[8];
          max_value = data[9];

      var time = d3.range(data[8]);
      var local_time = new Date();

      % if timezone == 'local':
          var current_time = local_time.getTime();
      % else:
          var current_time = (local_time.getTime() + local_time.getTimezoneOffset()*60*1000);
      % endif

      time.forEach(function(each, i) {
          time[i] = new Date(current_time + ((i - length) * time_per_data_point));
      });

      var legendHeight = 10*line_names.length;
      var graphHeight = 220 + legendHeight;

      custom_graph("graph_" + index, line_names, data_rows, max_value, time, time_per_data_point, graph_type);

      $("#edit_" + index).attr('href', "/edit?title=" + title_urlencoded + "&amp;timescale=" + timescale + "&amp;graph_type=" + graph_type_urlencoded);
      $("#remove_" + index).attr('href', "/edit?title=" + title_urlencoded + "&amp;delete=true");
      $("#stats_" + index).attr('href', "/stats/${dashboard_username}/" + title_urlencoded + "?timescale=" + timescale + "&amp;graph_type=" + graph_type_urlencoded);
      $("#graph_" + index).attr('href', "/graph/${dashboard_username}/" + title_urlencoded + "?timescale=" + timescale + "&amp;graph_type=" + graph_type_urlencoded);
    }

    function callForData(title, index) {
      $.ajax({
        type: 'GET',
        url: '/graphdata/${dashboard_username}/' + title,
        data: {},
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        async: true,
        success: function (data) {
          createGraph(data, index);
        },
        error: function(xhr, status) {
          console.log("error loading data");
          console.log("hatada: " + xhr.responseXML);
        },
        complete: function() {
          $("#graph_" + index + " .loading").hide();
        }
      });
    }

    % for title in graph_titles:
      callForData('${title}', '${graph_titles.index(title)}');
    % endfor
  </script>
  <body>
    <div class='tooltip'></div>
    % if edit is not None:
      <script type='text/javascript'>
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
    % if username == dashboard_username:
      <script type='text/javascript'>
        $(function() {
          // Handle graph control mouseover
          function handle_graph_mouseover() {
            var controls = $(this).find('.graph_controls');
            controls.show();
          }

          function handle_graph_mouseout() {
            var controls = $(this).find('.graph_controls');
            controls.hide();
          }

          $('#sortable li').each(function() {
            $(this)[0].onmouseover = handle_graph_mouseover;
            $(this)[0].onmouseout = handle_graph_mouseout;
          });
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
      <a href='/edit'>new graph</a>
      <br />
      % if edit is not None:
        <a href='/'>freeze graphs</a> <span class='hint'>Drag graphs to re-order them!</span>
      % elif username == dashboard_username:
        <a href='/?edit=true'>move graphs</a>
      % endif
      </h2>

      % if len(graph_titles) == 0:
        % if username == dashboard_username:
          Want custom graphs? Click new graph to create one!
        % else:
          No graphs yet!
        % endif
      % endif

      <ul id='sortable'>
        % for title in graph_titles:
        <li>
          <p>
            <span class='graph_title'>
              ${title}
            </span>
            % if username == dashboard_username:
              <span class='graph_controls'>
                <a href='' id="edit_${graph_titles.index(title)}">edit</a>
                <a href='' id="remove_${graph_titles.index(title)}">remove</a>
              </span>
            <br>
            % endif
            <span class="graph_controls">
              <a href="" id="stats_${graph_titles.index(title)}">stats</a>
            </span>
          </p>
          <a class='bare' id="graph_${graph_titles.index(title)}" href="/graph/${dashboard_username}/${graph_titles_urlencoded[graph_titles.index(title)]}">
            <span id='graph_${graph_titles.index(title)}'>
              <span class="loading">loading...</span>
            </span>
          </a>
        </li>
        % endfor
      </ul>
      <div id='post_float' />
      <br />
    % endif
  </body>
</html>
