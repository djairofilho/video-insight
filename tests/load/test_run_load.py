import httpx

from run_load import measure


def test_load_report_counts_authentication_and_network_failures():
    def reply(request):
        assert request.headers["Authorization"] == "Bearer test-token"
        return httpx.Response(401)

    with httpx.Client(transport=httpx.MockTransport(reply),
                      headers={"Authorization": "Bearer test-token"}) as client:
        result = measure(client, "https://gateway.test/api/v1/videos", 5, 2)
    assert result["status_counts"] == {"401": 5}
    assert result["errors"] == 5
    assert result["p95_ms"] >= result["p50_ms"] >= 0
