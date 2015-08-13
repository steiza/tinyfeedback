<!DOCTYPE html>
<meta charset='utf-8'>
<html>
    <head>
        <link href='/static/css/style.css' type='text/css' rel='stylesheet' />
        <script type='text/javascript' src='/static/js/jquery.min.js'></script>
        <script type='text/javascript' src='/static/js/jquery.confirm-1.3.js'></script>
        <script type='text/javascript' src='/static/js/jquery.sparkline.min.js'></script>

        <script type='text/javascript'>
            $(document).ready(function() {
                $('#delete_old').confirm({
                    msg: 'Really delete old metrics? ',
                    dialogShow: 'fadeIn',
                    dialogSpeed: 'slow',
                    buttons: {
                        wrapper: '<button></button>',
                        separator: ' ',
                    }
                });
            });

            $(function() {
                % for index, (metric, data, current, min, max) in enumerate(metrics):
                    var data_${index} = ${data};
                    $('.data_${index}').sparkline(data_${index}, {width: '250px'});
                % endfor
            });
        </script>
    </head>
    <body>
        <%include file="login.mako" args="username='${username}'"/>
        <h2><a class='nav' href='/'>tf</a> :: <a class='nav' href='/view'>components</a> :: ${component}</h2>
        <div class='timescale'>
        % for each_timescale in timescales:
            % if timescale == each_timescale:
                ${timescale}
            % else:
                <a class='timescale' href='/view/${component}?ts=${each_timescale}'>${each_timescale}</a>
            % endif
            % if each_timescale != timescales[-1]:
                :
            % endif
        % endfor
        </div>
        <br />
        <form action='/view/${component}' method='get'>
            <input type='hidden' name='delete_older_than_a_week' value='true' />
            <input type='hidden' name='ts' value='${timescale}' />
            <input type='submit' id='delete_old' value='Delete metrics older than a week' />
        </form>
        <table class='sparkline'>
            <tr>
                <td></td>
                <td></td>
                <td><b>last</b></td>
                <td><b>min</b></td>
                <td><b>max</b></td>
            </tr>
            % for index, (metric, data, current, min, max) in enumerate(metrics):
                <tr>
                    <td>${cgi.escape(metric)}</td>
                    <td><span class='data_${index}'>Loading...</span></td>
                    <td>${current}</td>
                    <td>${min}</td>
                    <td>${max}</td>
                </tr>
            % endfor
        </table>
    </body>
</html>
