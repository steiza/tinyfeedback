<!DOCTYPE html>
<meta charset='utf-8'>
<html>
    <head>
        <link href='/static/css/style.css' type='text/css' rel='stylesheet' />
    </head>
    <body>
        <%include file="login.mako" args="username='${username}'"/>
        <h2><a class='nav' href='/'>tf</a> :: components</h2>
        <ul>
          % for component in components:
          <li><a href="/view/${component}">${component}</a></li>
          % endfor
        </ul>
    </body>
</html>
