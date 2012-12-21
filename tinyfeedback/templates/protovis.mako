<script type='text/javascript'>
    function custom_graph(line_name, data, time, max, graph_type, width, height) {
        var width = width || 400;
        var panel_height = height || 250;
        var height = 150;


        var colors = ['#ff0000', '#ff8000', '#fff000', '#00ff00', '#00ffff',
                '#0000ff', '#ff00ff', '#ff8080', '#814100', '#808080', '#000000', 
                '#aa00cc', '#ee00ee', '#00eebb', '#ff99dd', '#55bb00',
                '#eeeeff', '#ee00cc', '#44bbff', '#00ff88', '#dddddd' , '#880000'];

        var vis = new pv.Panel()
                .width(width)
                .height(panel_height)
                .bottom(25)
                .left(40)
                .right(170)
                .top(25);

        // HACK: if last value is 0, set it to the previous value so graphs don't always drop off to 0
        for(var i = 0; i < data.length; i++) {
            var len = data[i].length;
            if(data[i][len-1] == 0 && data[i][len-2] != 0) {
                data[i][len-1] = data[i][len-2];
            }
        }

        if (max == 0) {
            max = 1;
        }

        var x = pv.Scale.linear(time).range(0, width);
        var y = pv.Scale.linear(0, max).range(panel_height-height, panel_height);

        // Add x-axis
        vis.add(pv.Rule)
                .bottom(panel_height-height)
                .strokeStyle('#000')
                .add(pv.Rule)
                .data(x.ticks())
                .left(x)
                .strokeStyle('#eee')
                .anchor('bottom').add(pv.Label)
                .text(x.tickFormat);

        // Add y-axis
        vis.add(pv.Rule)
                .data(y.ticks())
                .bottom(y)
                .strokeStyle(function(d) d ? '#eee' : '#000')
                .anchor('left').add(pv.Label)
                .text(y.tickFormat);

        // Add legend
        vis.add(pv.Dot)
                .data(line_names)
                .left(function() -15 + (this.index % 2) * (width / 2 + 20))
                .top(function() height + 25 + (this.index - this.index % 2) * 7)
                .size(8)
                .strokeStyle(null)
                .fillStyle(function() colors[this.index % colors.length])
                .anchor('right').add(pv.Label);

        if(graph_type == "stacked") {
            vis.add(pv.Layout.Stack)
            .layers(data)
            .x(function() this.index * width / (length-1))
            .y(function(d) d / max * height)
            .bottom(panel_height - height)
            .layer.add(pv.Area)
                .fillStyle(function(d){
                    return colors[this.parent.index % colors.length]
                });

        } else {
            // Graph lines
            for(var i = 0; i < data.length; i++) {
                vis.add(pv.Line)
                    .data(data[i])
                    .strokeStyle(colors[i % colors.length])
                    .lineWidth(1)
                    .bottom(function(y) panel_height - height + (y * height / max))
                    .left(function(x) this.index * width / (length-1));
            }
        }

        vis.render();
    }
</script>
