<span class='login'>
    <form action='/timezone' method='post'>
      Timezone: <select name='timezone'>
        % for each_timezone in ['local', 'UTC']:
          % if each_timezone == timezone:
            <option selected value="${each_timezone}">${each_timezone}</option>
          % else:
            <option value="${each_timezone}">${each_timezone}</option>
          % endif
        % endfor
        </select>
        <input type="submit" value="save"></input>
    </form>
    <br>
    % if username is None:
    <form action='/login' method='post'>
        <input type='text' name='username' />
        <input type='submit' value='login' />
    </form>
    % else:
    Hi ${username}! <a href='/logout'>logout</a>
    <br><a href="/dashboards/${username}">dashboard</a>
    % endif
    <br><a href="/dashboards">all dashboards</a>
    <br><a href="/view">all components</a>
</span>
<br />
