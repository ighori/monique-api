# Monique API

Monique API is an HTTP REST API application usually working in tandem with [Monique Web](https://github.com/monique-dashboards/monique-web). The application allows submitting new report instances and fetching the already created.

## Installation

[Monique library](https://github.com/monique-dashboards/monique) must be already [installed](http://monique-dashboards.readthedocs.io/en/latest/installation.html) and the database migrations of [Monique Web](https://github.com/monique-dashboards/monique-web) must be executed.

Monique API should be run from a git clone:

    $ git clone https://github.com/monique-dashboards/monique-api.git

The requirements can be installed using `pip`:

    $ pip install -r monique-api/requirements.txt


### Configuring the app

It's recommended that an URL under which the application is externally available is configured. The setting is available in the configuration module `apiconfig.py` and can be overriden by creating the file `apiconfig_override.py` and putting the value there:

    BASE_URL_API = 'https://example.com:8101'


### Running the WSGI app

The WSGI application (which is also a Flask application) is returned by the function `mqeapi.apiapp.create()`.

Monique API needs a checkout of [Monique Web](https://github.com/monique-dashboards/monique-web) repository to be included in `$PYTHONPATH`.

For example, the following commands run Monique API using [Gunicorn](http://gunicorn.org/) server:

    $ ls monique-web/mqeconfig_override.py monique-api/apiconfig_override.py  # ensure the configuration modules are present
    monique-web/mqeconfig_override.py monique-api/apiconfig_override.py

    $ cd monique-api
    $ pip install gunicorn
    $ PYTHONPATH=../monique-web gunicorn -b 0.0.0.0:8101 'mqeapi.apiapp:create()'

The application should be running under URL `http://localhost:8101`. Note that when the application is available through the internet, using HTTPS is strongly recommended - an API key is transmitted as a part of a request.

The installation can be tested by creating an account using [Monique Web](https://github.com/monique-dashboards/monique-web), getting the assigned API key from the settings page and submitting a sample report instance:

    $ df | curl --user <API_KEY>: --request POST --data-binary @- 'https://example.com:8101/reports/diskfree'


## Response format

A sample API response looks as follows:

    {
      "success": true,
      "details": {
        "next": "http://example.com:8101/reports?lastName=diskfree&limit=10"
      },
      "result": [
        { "name": "diskfree",
          "href": "http://example.com:8101/reports/diskfree" }
      ]
    }

All API responses are JSON objects. The following attributes are used:

* `success` attribute is a boolean telling if the call was successful
* `details` attribute contains optional metadata - in the example it contains a link for fetching next page of results. In case of an error, it will contain an error message.
* `results` attribute contains an actual result - usually an array or an object. Sometimes a result contains an attribute named `href` - it will contain an URL of a resource that can be fetched with the `GET` method.


## Passing an API key

An API key can be passed using two methods:

* HTTP Basic Authentication - an API key should be specified as either a username or a password
* URL query parameter `key`


## Available endpoints


### POST /reports/\<name\>

Create a report instance belonging to a report `<name>`.

**The input** from which a report instance is created must be passed as either `POST` binary data or set under a form key specified with the query parameter ``formKey`` (in the latter case, the content type must be `application/x-www-form-urlencoded`).

**Query parameters**:

* `created` - an explicitly set creation datetime (recommended format: ISO8601)
* `tags` - a comma-separated list of tags to attach to the report instance
* `format` - an input format, one of:
    * `any` (the default) - the format will be guessed
    * `json` - the input is a JSON document. A normalized representation of a report instance is an array of rows, where each row is an object mapping a column name to a column value. However, inputs not conforming to the representation will be also parsed by filling missing columns with `null` values and flattening nested objects (see [JsonDeepParser docs](http://monique-dashboards.readthedocs.io/en/latest/reference.html#mqe.pars.basicparsing.JsonDeepParser) for a further description).
    * `jsonraw` - the same as `json`, but the flattening of objects is not aplied.
    * `csv` - a CSV file. A delimiter is either guessed or can be specified with the `delimiter` query param.
    * `ascii` - an ASCII table that uses either the characters `| = + -` to "draw" a table or uses whitespace characters to align colums
    * `asciitable` - a subset of of the `ascii` format that requires usage of the `| = + -` characters
    * `asciispace` - a subset of the `ascii` format that requires usage of whitespace for aligning columns
    * `props` - each input line is treated as containing a property definition - a key, value pair, possibly separated with a delimiter. Each row of the parsed table will have the two elements.
    * `tokens` - each word is converted to a table row
    * `markdown` - the whole input is put inside a single-cell table. The input should be a Markdown document
    * `single` - the whole input is put inside a single-cell table. The input is treated as raw ASCII text.
* `delimiter` - an explicilty passed cell delimiter
* `header` - a comma-separated list of row indexes forming a header. It's useful when the guessed value is wrong.
* `autotags` - a comma-separated list of automatically computed tags, one of:
    * `ip` - attaches a tag `ip:<ip-address>`, where `<ip-address>` is the public IP address of the calling host
* `link` - an URL associated with the report instance
* `formKey` - a form key holding the data to parse (default behaviour: use the direct `POST` data)

**Result**:

An object representing a report instance, containing the attributes `id`, `tags`, `created`, `rows`, `header`.

**Sample invocation**:

Create a report instance from `df` command output and auto-assign an `ip` tag:

    $ df | curl --user WNKCPwiHfvIZRvfqsZa7Kai1: --request POST --data-binary @- 'https://example.com:8101/reports/diskfree?autotags=ip'

Assign explicit tags and set the `created` datetime:

    $ echo OK | curl --user WNKCPwiHfvIZRvfqsZa7Kai1: --request POST --data-binary @- 'https://example.com:8101/reports/process_state?tags=process:search,pid:1023&created=2017-09-08T21:00:08Z'

Send a report instance from Python using `requests` library:

    instance = [{'name': 'monique', 'points': 123}, {'name': 'john', 'points': 34}]
    r = requests.post('https://example.com:8101/reports/points',
                      params={'key': 'WNKCPwiHfvIZRvfqsZa7Kai1'},
                      json=instance)
    assert r.json()['success']


### GET /reports

Fetch a list of created reports.

**Query parameters**:

* `prefix` - select reports with a name starting with the prefix
* `limit` - the limit of results to return

**Result**:

An array of objects with attributes `name` (a report name) and `href` (the URL of the report). If the number of available results exceeds the `limit`, the `details.next` attribute will contain a link for fetching a next page.

**Sample invocation**:

    $ curl --user WNKCPwiHfvIZRvfqsZa7Kai1: 'https://example.com:8101/reports?prefix=disk'
    {
      "success": true,
      "details": {
        "next": null
      },
      "result": [
        {
          "name": "diskfree",
          "href": "https://example.com:8101/reports/diskfree"
        },
        {
          "name": "diskfree2",
          "href": "https://example.com:8101/reports/diskfree2"
        },
        {
          "name": "diskfree_old",
          "href": "https://example.com:8101/reports/diskfree_old"
        }
      ]
    }

### GET /reports/\<name\>/instances

Fetch a list of report instances belonging to the report `<name>`.

**Query parameters**:

* `from` - fetch instances created on the specified date or later
* `to` - fetch instances created on the specified date or earlier
* `tags` - a comma-separated list of tags that the instances must have attached
* `expand` - 0 or 1 (default) - whether the returned instances should contain the rows and header attributes containing the instance's tabular representation
* `expandInput` - 0 (default) or 1 - whether the returned instances should contain the `input` attribute containing the original instance's input from which the tabular representation was created
* `order` - `asc` (default) or `desc` - the direction of ordering of the returned instances by a creation datetime (ascending / descending)
* `fromId` - fetch instances starting from (and including) the given report instance id (specified as a hex string)
* `lastId` - the same as fromId, but excludes the given report instance id
* `limit` - limit the number of returned results to the specified number

**Result**:

An array of objects representing report instances, containing the attributes: `id`, `created`, `tags`, `rows` (if `expand == 1`), `input` (if `expandInput == 1`). If the number of available results exceeds the `limit`, the `details.next` attribute will contain a link for fetching a next page.

**Sample invocation**:

Fetch the latest report instance:

    $ curl --user WNKCPwiHfvIZRvfqsZa7Kai1: 'https://example.com:8101/reports/diskfree/instances?order=desc&limit=1&expand=0'
    {
      "success": true,
      "details": {
        "next": "https://example.com:8101/reports/diskfree/instances?lastId=23b6dfec954911e79f91bc5ff4d0b01f&limit=1&order=desc&expand=0"
      },
      "result": [
        {
          "id": "23b6dfec954911e79f91bc5ff4d0b01f",
          "tags": [ "ip:127.0.0.1" ],
          "created": "2017-09-09T10:25:02.242814",
          "href": "https://example.com:8101/reports/diskfree/instances/23b6dfec954911e79f91bc5ff4d0b01f"
        }
      ]


### GET /reports/\<name\>/instances/\<id\>

Fetch a single report instance having the passed `<id>`, belonging to the report `<name>`. The result is an object representing the report instance (see the previous paragraph for a description)


### DELETE /reports/\<name\>/instances

Delete a range of report instances belonging to the report `<name>`.

**Query parameters**:

* `from` - delete instances created on the specified date or later
* `to` - delete instances created on the specified date or earlier
* `tags` - a comma-separated list of tags that the deleted instances must have attached


### DELETE /reports/\<name\>/instances/\<id\>

Delete a single report instance having the passed `<id>`, belonging to the report `<name>`.
