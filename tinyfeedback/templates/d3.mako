<script type='text/javascript'>
  function custom_graph(container_id, line_names, data, max, time, time_per_data_point, graph_type, width, height) {
    var margins = {top: 10, right: 10, bottom: 150, left: 50};
    var width = width || 500;
    var height = height || 300;
    var graph_width = width - margins.left - margins.right;
    var graph_height = height - margins.top - margins.bottom;

    // HACK: if the last value is 0, set it to the previous value so graphs don't always drop off to 0
    data.forEach(function(each) {
      var len = each.length;
      if (each[len-1] == 0 && each[len-2] != 0) {
        each[len-1] = each[len-2];
      }
    });

    if (max == 0) {
      max = 1;
    }

    var colors = ['#ff0000', '#ff8000', '#fff000', '#00ff00', '#00ffff',
        '#0000ff', '#ff00ff', '#ff8080', '#814100', '#808080', '#000000',
        '#aa00cc', '#ee00ee', '#00eebb', '#ff99dd', '#55bb00', '#eeeeff',
        '#ee00cc', '#44bbff', '#00ff88', '#dddddd' , '#880000'];

    var graph = d3.select('#' + container_id).append('svg')
        .attr('class', 'chart')
        .attr('width', width)
        .attr('height', height)
        .on('mousemove', handleMouseMove)
        .append('g')
        .attr('transform', 'translate(' + margins.left + ', ' + margins.top + ')');

    // Handle mouse events
    function handleMouseMove() {
      var infobox = d3.select('.tooltip');

      infobox.style('left', d3.event.pageX + 20 + 'px');
      infobox.style('top', d3.event.pageY - 20 + 'px');
    }

    function handleMouseOver() {
      var path = d3.select(this);

      var all_paths = d3.select(path[0][0].parentElement.parentElement)
          .selectAll('path')

      // Dim all paths
      all_paths.each(function() {
        d3.select(this).style('opacity', 0.3);
      });

      // Leave this path undimmed
      d3.select(this).style('opacity', 1);

      d3.select('.tooltip')
          .text(this.getAttribute('line_name'))
          .style('display', 'block');
    }

    function handleMouseOut() {
      var path = d3.select(this);

      var all_paths = d3.select(path[0][0].parentElement.parentElement)
          .selectAll('path')

      // Undim all paths
      all_paths.each(function() {
        d3.select(this).style('opacity', 1);
      });

      d3.select('.tooltip')
          .style('display', 'none');
    }

    // Calculate the axes
    var x = d3.time.scale()
        .domain(d3.extent(time))
        .range([0, graph_width]);

    var xAxis = d3.svg.axis()
        .scale(x)
        .tickSize(5, 0) // 5px is how "tall" the ticks are, 0 gets rid of end tick
        .orient('bottom');

    var xGrid = d3.svg.axis()
        .scale(x)
        .tickSize(graph_height, 0)
        .orient('bottom')
        .tickFormat('');

    if (time_per_data_point == 60 * 1000) {
      xGrid.ticks(d3.time.hours, 1);

      xAxis.ticks(d3.time.hours, 1)
          .tickFormat(d3.time.format('%I:%M %p'));

    } else if (time_per_data_point == 5 * 60 * 1000) {
      xGrid.ticks(d3.time.hours, 6);

      xAxis.ticks(d3.time.hours, 6)
          .tickFormat(d3.time.format('%I:%M %p'));

    } else if (time_per_data_point == 30 * 60 * 1000) {
      xGrid.ticks(d3.time.days, 1);

      xAxis.ticks(d3.time.days, 1)
          .tickFormat(d3.time.format('%a'));

    } else if (time_per_data_point == 2 * 60 * 60 * 1000) {
      xGrid.ticks(d3.time.mondays, 1);

      xAxis.ticks(d3.time.mondays, 1)
          .tickFormat(d3.time.format('%b %e'));

    } else {
      xGrid.ticks(d3.time.months, 1);

      xAxis.ticks(d3.time.months, 1)
          .tickFormat(d3.time.format('%b'));
    }

    var y = d3.scale.linear()
        .domain([0, max])
        .range([graph_height, 0]);

    var yAxis = d3.svg.axis()
        .scale(y)
        .ticks(8)
        .tickSize(5, 0) // 5px is how "tall" the ticks are, 0 gets rid of end tick
        .orient('left');

    var yGrid = d3.svg.axis()
        .scale(y)
        .ticks(8)
        .tickSize(-1 * graph_width, 0)
        .orient('left')
        .tickFormat('');

    // Draw grid
    graph.append('g')
        .attr('class', 'grid')
        .call(xGrid);

    graph.append('g')
        .attr('class', 'grid')
        .call(yGrid);

    // Draw the data
    if (graph_type == 'stacked') {
      var area = d3.svg.area()
          .x(function(d, i) {return x(time[i])})
          .y1(function(d) {return y(d[1]);})
          .y0(function(d) {return y(d[0]);});

      var baseline = time.map(function (x) {return 0;});
      var topline = time.map(function (x) {return 0;});

      data.forEach(function(each, i) {
        each.forEach(function(val, j) {
          topline[j] = baseline[j] + val;
        });

        graph.append('g').append('path')
            .datum(d3.zip(topline, baseline))
            .attr('d', area)
            .attr('class', 'area')
            .attr('line_name', line_names[i])
            .style('stroke', colors[i % colors.length])
            .style('fill', colors[i % colors.length])
            .on('mouseover', handleMouseOver)
            .on('mouseout', handleMouseOut);

        baseline = topline.slice(0);
      });

    } else { // Line graph
      var line = d3.svg.line()
          .x(function(d, i) {return x(time[i]);})
          .y(function(d) {return y(d);});

      data.forEach(function(each, i) {
        graph.append('g').append('path')
            .datum(each)
            .attr('d', line)
            .attr('class', 'line')
            .attr('line_name', line_names[i])
            .style('stroke', colors[i % colors.length])
            .on('mouseover', handleMouseOver)
            .on('mouseout', handleMouseOut);
      });
    }

    // Actually draw the axes
    graph.append('g')
        .attr('class', 'x axis')
        .attr('transform', 'translate(0, ' + graph_height + ')')
        .call(xAxis);

    graph.append('g')
        .attr('class', 'y axis')
        .call(yAxis);

    // Draw the legend
    line_names.forEach(function(each, i) {
      var legend_height = graph_height + margins.top + 30 + 20*Math.round((i - 1) / 2);
      var legend_width = 250 * (i % 2) - 30;

      graph.append('circle')
          .attr('transform', 'translate(' + legend_width + ', ' + legend_height + ')')
          .attr('r', '5')
          .style('fill', colors[i % colors.length]);

      legend_height = legend_height + 4;
      legend_width = legend_width + 10;

      if (each.length > 35) {
        each = each.slice(0, 35) + '...';
      }

      graph.append('text')
          .attr('class', 'axis')
          .attr('transform', 'translate(' + legend_width + ', ' + legend_height + ')')
          .attr('font-size', '13px')
          .text(each);
    });
  }
</script>
