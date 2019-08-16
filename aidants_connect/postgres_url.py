# from https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
def turn_psql_url_into_param(postgres_url: str) -> dict:
    """
    >>> turn_psql_url_into_param(
    ... 'postgres://USERNAME:PASSWORD@URL:PORT/USER?sslmode=SSLMODE') == {
    ... 'db_user':'USERNAME', 'db_password': 'PASSWORD', 'db_host': 'URL', 'db_port':
    ... 'PORT', 'db_name': 'USER', 'sslmode': 'SSLMODE'}
    True
    >>> turn_psql_url_into_param(
    ... 'USERNAME:PASSWORD@URL:PORT/USER?sslmode=SSLMODE')
    Traceback (most recent call last):
        ...
    AttributeError: The database URL is not well formated

    >>> turn_psql_url_into_param(
    ... 'postgres://USERNAME:PASSWORD@URL:PORT/USER') == {
    ... 'db_user': 'USERNAME', 'db_password': 'PASSWORD', 'db_host': 'URL',
    ... 'db_port': 'PORT', 'db_name': 'USER'}
    True

    >>> turn_psql_url_into_param("postgresql://") == {}
    True

    >>> turn_psql_url_into_param('postgresql://localhost') == {'db_host':
    ... 'localhost'}
    True

    >>> turn_psql_url_into_param('postgresql://localhost:5433') == {'db_host':
    ... 'localhost', 'db_port': '5433'}
    True

    >>> turn_psql_url_into_param('postgresql://localhost/mydb') == {'db_host':
    ... 'localhost', 'db_name': 'mydb'}
    True

    >>> turn_psql_url_into_param('postgresql://user@localhost') == {'db_host':
    ... 'localhost', 'db_user': 'user'}
    True

    >>> turn_psql_url_into_param('postgresql://user:secret@localhost') == {
    ... 'db_host': 'localhost', 'db_user': 'user', 'db_password': 'secret'}
    True

    >>> turn_psql_url_into_param('postgresql://oto@localhost/ther?'
    ... 'connect_timeout=10&application_name=myapp') == {
    ... 'db_host': 'localhost', 'db_user': 'oto', 'db_name': 'ther',
    ... 'connect_timeout': '10', 'application_name': 'myapp'}
    True
    """

    if not postgres_url.startswith(("postgres://", "postgresql://")):
        raise AttributeError("The database URL is not well formated")
    response = {}

    # Get parameters
    params_start = postgres_url.rfind("?")
    if not params_start == -1:
        params = postgres_url[params_start + 1 :]
        params = [param.split("=") for param in params.split("&")]
        for param in params:
            response[param[0]] = param[1]
        user_and_db_info = postgres_url[postgres_url.find("://") + 3 : params_start]
    else:
        user_and_db_info = postgres_url[postgres_url.find("://") + 3 :]

    if not user_and_db_info:
        return response

    # User information
    if "@" in user_and_db_info:
        user_info, db_info = tuple(user_and_db_info.split("@"))

        user_info = user_info.split(":")
        response["db_user"] = user_info[0]
        if len(user_info) > 1:
            response["db_password"] = user_info[1]
    else:
        db_info = user_and_db_info

    # Database information

    db_info = db_info.split("/")
    if len(db_info) > 1:
        response["db_name"] = db_info[1]

    url_and_port = db_info[0]
    url_and_port = url_and_port.split(":")
    response["db_host"] = url_and_port[0]
    if len(url_and_port) > 1:
        response["db_port"] = url_and_port[1]
    return response
