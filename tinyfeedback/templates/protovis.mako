<script type='text/javascript+protovis'>
    function custom_graph(line_name, data, time, max, graph_type) {
        var width = 400;
        var panel_height = 230;
        var height = 150;

        var colors = ['#ff0000', '#ff8000', '#fff000', '#00ff00', '#00ffff',
                '#0000ff', '#ff00ff', '#ff8080', '#814100', '#808080', '#000000'];

        var vis = new pv.Panel()
                .width(width)
                .height(panel_height)
                .bottom(25)
                .left(40)
                .right(170)
                .top(25);

        // HACK: to smooth out graphs that have 0 for every other value
        for(var i = 0; i < data.length; i++) {
            for(var j = 0; j < data[i].length; j++) {
                if(j > 0 && j + 2 < data[i].length) {
                    if(data[i][j] == 0 &&
                        (
                            ( data[i][j-1] != 0 && data[i][j+1] != 0 ) ||
                            ( data[i][j-1] != 0 && data[i][j+2] != 0 )
                        )

                        ){
                        data[i][j] = data[i][j-1];
                    }
                }
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
            .order('reverse')
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
