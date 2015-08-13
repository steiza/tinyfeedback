<script type='text/javascript'>

    function createTime(time_per_data_point, length) {
      var time = d3.range(0, length);
      var local_time = new Date();

      % if timezone == 'local':
          var current_time = local_time.getTime();
      % else:
          var current_time = (local_time.getTime() + local_time.getTimezoneOffset()*60*1000);
      % endif

      time.forEach(function(each, i) {
          time[i] = new Date(current_time + ((i - length) * time_per_data_point));
      });

      return time
    }

    function colorGrid(td, datapoint, percentiles) {
      var colorrange = d3.scale.linear()
        .domain([0, .5, 1])
        .range(["white", "yellow", "red"]);

      switch(true) {
        case (datapoint > percentiles[98][1]):
          td.css("background-color", String(colorrange(1)));
          break;
        case (datapoint > percentiles[88][1]):
          td.css("background-color", String(colorrange(.9)));
          break;
        case (datapoint > percentiles[78][1]):
          td.css("background-color", String(colorrange(.8)));
          break;
        case (datapoint > percentiles[68][1]):
          td.css("background-color", String(colorrange(.7)));
          break;
        case (datapoint > percentiles[58][1]):
          td.css("background-color", String(colorrange(.6)));
          break;
        case (datapoint > percentiles[48][1]):
          td.css("background-color", String(colorrange(.5)));
          break;
        case (datapoint > percentiles[38][1]):
          td.css("background-color", String(colorrange(.4)));
          break;
        case (datapoint > percentiles[28][1]):
          td.css("background-color", String(colorrange(.3)));
          break;
        case (datapoint > percentiles[18][1]):
          td.css("background-color", String(colorrange(.2)));
          break;
        default:
          td.css("background-color", String(colorrange(0)));
      }
    }

    function colorRaw(td, percentiles) {
      var colorrange = d3.scale.linear()
        .domain([0, .5, 1])
        .range(["white", "yellow", "red"]);

      switch(true) {
        case (td.text() > percentiles[98][1]):
          td.css("background-color", String(colorrange(1)));
          break;
        case (td.text() > percentiles[78][1]):
          td.css("background-color", String(colorrange(.8)));
          break;
        case (td.text() > percentiles[58][1]):
          td.css("background-color", String(colorrange(.6)));
          break;
        case (td.text() > percentiles[38][1]):
          td.css("background-color", String(colorrange(.4)));
          break;
        case (td.text() > percentiles[18][1]):
          td.css("background-color", String(colorrange(.2)));
          break;
        default:
          td.css("background-color", String(colorrange(0)));
      }
    }

    function colorPercent(td) {
      switch(true) {
        case (td.text() > 0 || td.text() == "inf"):
          td.css("background-color", "lawngreen");
          break;
        case (td.text() == 0 || td.text() == "na"):
          td.css("background-color", "white");
          break;
        case (td.text() < 0 || td.text() == "-inf"):
          td.css("background-color", "#FF3333");
          break;
        default:
          td.css("background-color", "white");
      }
    }

    function createSummaryTable(summarystats, data) {
        summaryTable = $("<table></table>").addClass('stats-table');

        var headRow = $("<tr></tr>");
        headRow.append($("<th>Index</th><th>Metric</th><th>Sparkline</th><th>Last</th><th>Min</th><th>Max</th><th>Range</th><th>Mean</th><th>Median</th><th>SD</th>"));

        summaryTable.append(headRow);

        for (i=0; i<summarystats.length; i++) {
          var newRow = $("<tr></tr>");
          var index = $("<td>" + i + "</td>");
          var name = $("<td>" + summarystats[i][0] + "</td>");
          newRow.append(index);
          newRow.append(name);

          var spark = $("<td></td>").addClass("spark").sparkline(data[i], {width: '250px', height: "15px"});
          var lastValue = $("<td>" + data[i][(data[i].length-1)] + "</td>");

          newRow.append(spark);
          newRow.append(lastValue);

          for (j=1; j<summarystats[i].length; j++) {
            var newTD = $("<td>" + Math.floor(summarystats[i][j]) + "</td>");
            newRow.append(newTD);
          }

          summaryTable.append(newRow);
        }

        $("#summary").first().append(summaryTable);
    }

    function createColorGrid(data, percentiles, time) {
      var table = $('<table></table>').addClass('color-table');

      for (i=0; i<data.length; i++) {
        var row = $('<tr></tr>');

        for (j=0; j<time.length; j++) {
          var td = $('<td></td>');

          colorGrid(td, data[i][j], percentiles);

          row.append(td);
        }
        table.append(row);
      }
      $("#colorgrid").append(table);
      $("#colorgrid").append($("<br>"));
    }

    function createRawDataTable(data, percentiles, time) {
      var table = $('<table></table>').addClass('stats-table');
      var headrow = $('<tr></tr>');
      var headtd = $('<th></th>').text("Time");
      headrow.append(headtd);

      for (i=0; i<data.length; i++) {
        var headtd = $('<th></th>').text(String(i));
        headrow.append(headtd);
      }

      table.append(headrow);

      for(j=0; j<time.length; j++){
          var row = $('<tr></tr>');
          var td = $('<th></th>').addClass('tabledata').text(String(time[j]));
          row.append(td);

          for (i=0; i<data.length; i++) {
            var td = $('<td></td>').addClass('tabledata').text(String(data[i][j]));
            colorRaw(td, percentiles);
            row.append(td);
          }
          table.append(row);
      }
      $("#raw").append(table);
    }

    function createPercentsTable(data, time) {
      var table = $('<table></table>').addClass('stats-table');
      var headrow = $('<tr></tr>');
      var headtd = $('<th></th>').text("Time");
      headrow.append(headtd);

      for (i=0; i<data[0].length; i++) {
        var headtd = $('<th></th>').text(String(i));
        headrow.append(headtd);
      }

      table.append(headrow);

      for(j=0; j<time.length; j++){
          var row = $('<tr></tr>');
          var td = $('<th></th>').addClass('tabledata').text(String(time[j]));
          row.append(td);

          for (i=0; i<data[j].length; i++) {
            var value = data[j][i];
            if (typeof value == "number") {
              value = Math.floor(value);
            }

            var td = $('<td></td>').addClass('tabledata').text(String(value));
            colorPercent(td);
            row.append(td);
          }
          table.append(row);
      }
      $("#percent").append(table);
    }
</script>
