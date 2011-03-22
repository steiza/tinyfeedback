<span class='login'>
    % if username is None:
    <form action='/login' method='post'>
        <input type='text' name='username' />
        <input type='submit' value='login' />
    </form>
    % else:
    Hi ${username}! <a href='/logout'>logout</a>
    % endif
</span>
<br />
