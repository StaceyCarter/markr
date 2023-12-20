# Overview

Markr is a light flask service backed by a PostgreSQL db.

The database schema is 3 tables:

- Tests: Contains information pertaining to a single test ID.
- TestScores: Maps test IDs to individual student scores. There is an index on test_id to improve lookup time from the /aggregate endpoint.
- Students: Table mapping student IDs to first and last names (we could probably do without this table, if we don't mind the data being anonymous). There is no requirement to populate first and last names in this table.

There are 2 endpoints:

"/import" - Accepts test results formatted as XML and pulls out key data pertaining to each result.

"/results/<test_id>/aggregate" - Provides aggregate data (mean, median, p25|50|75 etc) for a particular test.

# Test Plan

# Manual testing

Clone repo:

```
git clone https://github.com/StaceyCarter/markr.git
```

CD into the directory where you cloned it, and run with docker:

```
docker compose up --build
```

**Happy Case**
Sanity check correct processing and responses is achieved on one sample:

```
(env) stacey@StaceyMacbook markr % curl -X POST -H 'Content-Type: text/xml+markr' http://localhost:4567/import -d @- <<XML
    <mcq-test-results>
        <mcq-test-result scanned-on="2017-12-04T12:12:10+11:00">
            <first-name>Jane</first-name>
            <last-name>Austen</last-name>
            <student-number>521585128</student-number>
            <test-id>1234</test-id>
            <summary-marks available="20" obtained="13" />
        </mcq-test-result>
    </mcq-test-results>
XML
"Added/modified 1 test scores"
(env) stacey@StaceyMacbook markr % curl http://localhost:4567/results/1234/aggregate
{"count":1,"max":65,"mean":65.0,"median":65.0,"min":65,"p25":65.0,"p50":65.0,"p95":65.0,"stddev":0.0}
```

Bulk add sample data to the endpoint:

```
(env) stacey@StaceyMacbook markr % curl -X POST -H 'Content-Type: text/xml+markr' http://localhost:4567/import -d @tests/sample_data.xml
"Added/modified 100 test scores"
```

Then verify it aggregates:

```
(env) stacey@StaceyMacbook markr % curl http://localhost:4567/results/9863/aggregate
{"count":81,"max":15,"mean":10.160493827160494,"median":10.0,"min":6,"p25":9.0,"p50":10.0,"p95":14.0,"stddev":1.984239071887846}
```

**Unhappy Cases**

Wrong content type is rejected:

```
(env) stacey@StaceyMacbook markr % curl -X POST -H 'Content-Type: application/json' http://localhost:4567/import -d @tests/sample_data.xml
<!doctype html>
<html lang=en>
<title>400 Bad Request</title>
<h1>Bad Request</h1>
<p>content_type must be text/xml+markr</p>
```

Sending missing data is rejected:

```
(env) stacey@StaceyMacbook markr % curl -X POST -H 'Content-Type: text/xml+markr' http://localhost:4567/import -d @- <<XML
    <mcq-test-results>
        <mcq-test-result scanned-on="2017-12-04T12:12:10+11:00">
            <first-name>Jane</first-name>
            <last-name>Austen</last-name>
            <student-number>521585128</student-number>
            <test-id>1234</test-id>
        </mcq-test-result>
    </mcq-test-results>
XML
<!doctype html>
<html lang=en>
<title>400 Bad Request</title>
<h1>Bad Request</h1>
<p>Error extracting test data: No summary marks available</p>
```

More unhappy cases covered in unit tests.

# Unit tests

Run unit tests with:

```
(env) stacey@StaceyMacbook markr % cd tests
(env) stacey@StaceyMacbook tests % pytest
======================================================================== test session starts =========================================================================
platform darwin -- Python 3.11.3, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/stacey/development/markr/tests
configfile: pytest.ini
plugins: env-1.1.3
collected 11 items

test_aggregate.py ...                                                                                                                                          [ 27%]
test_import.py ........                                                                                                                                        [100%]

========================================================================== warnings summary ==========================================================================
...
================================================================== 11 passed, 638 warnings in 0.67s ==================================================================
(env) stacey@StaceyMacbook tests %
```

Note: did not have time to address warnings.

# Future

- Speed up aggregate endpoint: Currently the endpoint is slow since at request time we must gather all entries for that test ID from the database, and perform the calculations on them each time we receive a request. To make this more efficient in the future we could consider aynchronously calculating the new stats and storing them in the db each time a new test score(s) is added. If we need to supply realtime updates to another service, we could potentially use a Postgres Trigger to do this or have some logic on the python side that checks if it is changing these aggregate values and if so, calls the dashboard service to update.
  The drawback of this is that we are relying on eventual consistency, and there will be some lag between when we add a new datapoint, vs when its effect on the data makes it to the dashboard. So the results may be slightly stale in this case, but it would make the request time constant rather than dependent on the number of test scores in the db. This approach doesn't actually speed up the calculation time for the aggregate values.
  To make the calculation of the running median faster, we could keep track of 2 heaps, and each time a data point comes in, we can insert it into the correct heap depending on if it is larger or smaller than the current root values. The median is the average of the 2 root values or the root of the larger heap. This doesn't help us with p25/p75 though.

- Logging, monitoring & alarming.
- Security: right now dummy secrets for connecting with the DB are hard-coded.
