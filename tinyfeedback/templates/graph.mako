<!DOCTYPE html>
<meta charset='utf-8'>
<html>
  <head>
    <link href='../../static/css/style.css' type='text/css' rel='stylesheet' />
    <script type='text/javascript' src='/static/js/jquery.min.js'></script>
    <script type='text/javascript' src='/static/js/d3.v3.min.js'></script>
    <script type='text/javascript' src='/static/js/jquery-ui.min.js'></script>
  </head>
  <script type="text/javascript">
    $(document).ready(function(){
        loadGraphData('${graph_type}', '${timescale}', '${graph_timezone}', 'False');
        var refresh_turned_off = true;
        var refresh_timer_id = 0;

        $("#infoshow").hover(function(){
          $("#info").show();
        }, function(){
          $("#info").hide();
        });

        function createGraph(data, timezone) {
          $("#datagoeshere").empty();

          var graph_type = data[2];
              time_per_data_point = data[5];
              line_names = data[6];
              data_rows = data[7];
              length = data[8];
              max_value = data[9];

          var time = d3.range(data[8]);
          var local_date = new Date();

          var utc_time = local_date.getTime() + local_date.getTimezoneOffset()*60*1000;
          var current_time = utc_time;

          if (timezone == 'local') {
            var local_time = local_date.getTime();
            current_time = local_time;
          }

          time.forEach(function(each, i) {
              time[i] = new Date(current_time + ((i - length) * time_per_data_point));
          });

          var legendHeight = 10*line_names.length;
          var graphHeight = 220 + legendHeight;

          custom_graph('datagoeshere', line_names, data_rows, max_value, time, time_per_data_point, graph_type, 800, graphHeight)
        }

        function handleQuickswitch(data, graph_type, timescale, timezone, refresh) {
          var quickswitch_timescale = timescale;
              quickswitch_graph_type = graph_type;
              quickswitch_timezone = timezone;
              quickswitch_refresh = refresh;

          if (quickswitch_graph_type == "") {
            quickswitch_graph_type = data[2];
          }
          if (quickswitch_timescale == "") {
            quickswitch_timescale = data[4];
          }

          $("input:radio[value="+ quickswitch_timescale + "]").attr('checked', 'checked');
          $("input:radio[value=" + quickswitch_graph_type + "]").attr('checked', 'checked');
          $("input:radio[value=" + quickswitch_timezone + "]").attr('checked', 'checked');
          $("input:radio[value=" + quickswitch_refresh + "]").attr('checked', 'checked');

          $("input:radio[name='timescale_value']").unbind().change(function(){
            quickswitch_timescale = $("input[name='timescale_value']:checked").val();
          });

          $("input:radio[name='graph_type_value']").unbind().change(function(){
            quickswitch_graph_type = $("input[name='graph_type_value']:checked").val();
          });

          $("input:radio[name='timezone_value']").unbind().change(function(){
            quickswitch_timezone = $("input[name='timezone_value']:checked").val();
          });

          $("input:radio[name='refresh_value']").unbind().change(function(){
            quickswitch_refresh = $("input[name='refresh_value']:checked").val();
          });

          $("#quickswitch-button").unbind().click(function() {
            loadGraphData(quickswitch_graph_type, quickswitch_timescale, quickswitch_timezone, quickswitch_refresh);
          });
        }

        function handleRefresh(graph_type, timescale, timezone, refresh) {
          if (refresh == 'True') {
            clearInterval(refresh_timer_id);
            var refresh_interval = 1000*60;
            refresh_turned_off = false;

            refresh_timer_id = setInterval(function(){
                loadGraphData(graph_type, timescale, timezone, 'True');},
                refresh_interval);
          }
          else if ((refresh == 'False') && (!refresh_turned_off)) {
            clearInterval(refresh_timer_id);
            refresh_turned_off = true;
          }
        }

        function handleLinks(data) {
          var title_urlencoded = data[1];
              graph_type_urlencoded = data[3];
              timescale = data[4];

          $("#edit_link").attr('href', "/edit?title=" + title_urlencoded + "&amp;timescale=" + timescale + "&amp;graph_type=" + graph_type_urlencoded);

          $("#stats_link").attr('href', "/stats/${graph_username}/" + title_urlencoded + "?timescale=" + timescale + "&amp;graph_type=" + graph_type_urlencoded);
        }

        function loadGraphData(graph_type, timescale, timezone, refresh) {
          $("#datagoeshere").empty();
          $(".loading").show();
          $(".graph_controls").hide();

          $.ajax({
            type: 'GET',
            url: '/graphdata/${graph_username}/${title}',
            data: {timescale: timescale, graph_type: graph_type,
                    timezone: timezone, refresh: refresh},
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            async: true,
            success: function (data) {
              createGraph(data, timezone);
              handleQuickswitch(data, graph_type, timescale, timezone, refresh);
              handleRefresh(graph_type, timescale, timezone, refresh);
              handleLinks(data);
            },
            error: function(xhr, status) {
              console.log("error loading data");
              console.log("hatada: " + xhr.responseXML);
            },
            complete: function() {
              $(".loading").hide();
              $(".graph_controls").show();

              if ((timescale !== "") && (graph_type !== "")) {
                history.replaceState({}, "", "${title}?timescale=" + timescale + "&amp;graph_type=" + graph_type);
              }
            }
          });
        }
    });
  </script>
  <body>
    <div class='tooltip'></div>
    <%include file="d3.mako"/>
    <%include file="login.mako" args="username='${username}'"/>
    <h2><a class='nav' href='/'>tf</a> :: view graph</h2>

    % if username is not None and username != graph_username:
        <form action='/add_graph' method='post'>
          <input type='hidden' name='graph_username' value='${graph_username}'/>
          <input type='hidden' name='title' value='${title}'/>
          <input type='hidden' name='timescale' value='${timescale}'/>
          <input type='hidden' name='graph_type' value='${graph_type}'/>
          <input type='submit' value='Add to my dashboard' />
        </form>
        <br>
    % elif username is None:
      Want this graph on your dashboard? Log in above!
        <br>
    % endif

    <div class="quickswitch">
      % for timescale_value in ['6h', '36h', '1w', '1m', '6m']:
        <input type='radio' name='timescale_value' value='${timescale_value}' class="quicktimescale"/>${timescale_value}
      % endfor
      <br>
      % for graphtype in ['line', 'stacked']:
        <input type='radio' name='graph_type_value' value='${graphtype}' class="quickgraphtype"/>${graphtype}
      % endfor
      <br>
      % for timezone_value in ['local', 'UTC']:
        <input type='radio' name='timezone_value' value='${timezone_value}' class="quicktimezone"/>${timezone_value}
      % endfor
      <br>
        <input type='radio' name='refresh_value' value='True' class="quickrefresh"/>autorefresh on
        <input type='radio' name='refresh_value' value='False' class="quickrefresh"/>autorefresh off
      <br>
      <button type="button" id="quickswitch-button">switch</button>
      <br>
    </div>

    <table class='graph'>
      <tr>
        <td>
            <p>
              <span class='graph_title'>
                ${title}
              </span>
              <p class="loading">loading...</p>
              % if username == graph_username:
                <span class='graph_controls'>
                  <a id='edit_link' href=''>edit</a>
                </span>
              <br>
              % endif
              <span class="graph_controls">
                <a id="stats_link" href=''>stats</a>
              </span>
              <br>
              <span id="infoshow" class='graph_controls'>info></span>
            </p>
            <div id="datagoeshere"></div>
        </td>
        <td id="info">
            **Autofresh will refresh the page every minute<br>
            **Changing the timezone in quickswitch will not affect your global timezone setting. To change your global timezone setting use the option in the top right above login.<br>
            **Data is collected over a time frame dependent on the timescale.
            <br>
            6h: every minute
            <br>
            36h: 5 minutes
            <br>
            1w: 30 minutes
            <br>
            1m: 2 hours
            <br>
            6m: 12 hours
        </td>
      </tr>
    </table>
  </body>
</html>
