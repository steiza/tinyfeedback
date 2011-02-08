<script type='text/javascript+protovis'>
    function custom_graph(line_name, data, time, max, graph_type) {
        var width = 400;
        var height = 150;

        var colors = ['#ff0000', '#ff8000', '#fff000', '#00ff00', '#00ffff',
                '#0000ff', '#ff00ff', '#ff8080', '#814100', '#808080', '#000000'];

        var vis = new pv.Panel()
                .width(width)
                .height(height)
                .bottom(25)
                .left(40)
                .right(170)
                .top(25);

        // HACK: to smooth out graphs that have 0 for every other value
        for(var i = 0;i<data.length;i++) {
            for(var j = 0;j<data[i].length;j++) {
                if(j >0 && j + 2 < data[i].length){
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

        var x = pv.Scale.linear(time).range(0, width);
        var y = pv.Scale.linear(0, max).range(0, height);

        // Add x-axis
        vis.add(pv.Rule)
                .bottom(0)
                .strokeStyle('#000')
                .add(pv.Rule)
                .data(x.ticks())
                .left(x)
                .bottom(1)
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
                .right(-15)
                .top(function() this.index * 14)
                .size(8)
                .strokeStyle(null)
                .fillStyle(function() colors[this.index % colors.length])
                .anchor('right').add(pv.Label);

        if(graph_type == "stacked") {
            vis.add(pv.Layout.Stack)
            .layers(data)
            //.values(line_names)
            .x(function() this.index * width / (length-1))
            .y(function(d) d / (max) * height )
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
                    .bottom(function(y) y * height / max)
                    .left(function(x) this.index * width / (length-1));
            }
        }


        vis.render();
    }
</script>
