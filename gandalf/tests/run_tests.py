import urllib
import urllib2
import cookielib
import json

TEST_GANDALF_URL = "http://localhost:8080/gandalf/tests/run_step"

last_opener = None

def test_response(step, data={}):
    global last_opener

    if last_opener is None:
        cj = cookielib.CookieJar()
        last_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

        # Login as administrator during first request
        last_opener.open("http://localhost:8080/_ah/login?email=test%40example.com&admin=True&action=Login&continue=%2Fpostlogin")

    data["step"] = step

    req = last_opener.open("%s?%s" % (TEST_GANDALF_URL, urllib.urlencode(data)))

    try:
        response = req.read()
    finally:
        req.close()

    return json.loads(response)

def run_tests():

    assert(test_response("can_cross_empty_bridge") == False)
    assert(test_response("can_cross_all_users_whitelist") == True)
    assert(test_response("can_cross_all_users_blacklist") == False)
    assert(test_response("can_cross_all_users_whitelist_and_blacklist") == False)

    # Try these a few times to make sure that users do not jump between
    # being inside or outside a percentage between requests
    assert(test_response("can_cross_all_users_inside_percentage") == True)
    assert(test_response("can_cross_all_users_outside_percentage") == False)

    print "Tests successful."

if __name__ == "__main__":
    run_tests()
