<!DOCTYPE html>
<meta charset='utf-8'>
<html>
  <head>
    <link href='../../static/css/style.css' type='text/css' rel='stylesheet' />
    <script type='text/javascript' src='/static/js/jquery.min.js'></script>
    <script type='text/javascript' src='/static/js/d3.v3.min.js'></script>
    <script type='text/javascript' src='/static/js/jquery-ui.min.js'></script>
    <script type='text/javascript' src='/static/js/jquery.sparkline.min.js'></script>
  </head>
  <%include file="statsJS.mako"/>
  <script type="text/javascript">
    $(document).ready(function(){
      $(".statsbutton").click(function(){
        $("#colorbutton").show();

        $(".statsgraph").each(function(){
          $(this).hide();
        });
        if ($(this).text() == "raw data") {
          $("#raw").show();
        }
        else if ($(this).text() == "percent change") {
          $("#percent").show();
        }
      });

      $("#colorbutton").toggle(function(){
        $(this).text("turn color on");
        $("#raw table td, #percent table td").addClass("colorOverride");
      }, function(){
        $(this).text("turn color off");
        $("#raw table td, #percent table td").removeClass("colorOverride");
      });

      $.ajax({
        type: 'GET',
        url: '/statsdata/${graph_username}/${title}',
        data: {timescale: '${timescale}', graph_type: '${graph_type}'},
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        async: true,
        success: function (data) {
          var time = createTime(data['graph_details'][5], data['graph_details'][8]);

          createColorGrid(data['graph_details'][7], data['percentiles'], time);
          createSummaryTable(data['summary'], data['graph_details'][7]);
          createRawDataTable(data['graph_details'][7], data['percentiles'], time);
          createPercentsTable(data['percents'], time);
        },
        error: function(xhr, status) {
          console.log("error loading data");
          console.log("hatada: " + xhr.responseXML);
        },
        complete: function() {
          $(".loading").hide();
          $(".statsbutton").show();
        }
      });
    });
  </script>
  <body>
    <div class='tooltip'></div>
    <%include file="login.mako" args="username='${username}'"/>
    <h2><a class='nav' href='/'>tf</a> :: <a class='nav' href='/graph/${graph_username}/${title}?timescale=${timescale}&amp;graph_type=${graph_type}'>view graph</a> :: statistics</h2>
    <h1>${title}</h1>
    <div id="colorgrid"></div>
    <div id="summary">
      <p class="loading">loading...</p>
    </div>
    <br>
    <button id="rawbutton" class="statsbutton" type="button">raw data</button>
    <button id="percentbutton" class="statsbutton" type="button">percent change</button>
    <br><br>
    <button id="colorbutton" type="button">turn color off</button>
    <div id="raw" class="statsgraph">
      <p>Raw Data: red-highest values, white-lowest values across all columns</p>
    </div>
    <div id="percent" class="statsgraph">
      <p>Percent Change: the percent change over five data points [columns are independent]</p>
    </div>
  </body>
</html>
