import io

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from qicetong.app import app
from qicetong.documents import parse


@pytest.fixture
def client(isolated_store):
    with TestClient(app) as c:
        yield c


def test_dashboard_and_report_export(client):
    dashboard = client.get("/api/dashboard").json()
    assert len(dashboard["companies"]) == 5
    assert dashboard["health"]["region"] == "北京市"
    response = client.post("/api/reviews", json={"company_id":"demo-01","policy_id":"hnte-bj-2026","as_of":"2026-09-22"})
    assert response.status_code == 200
    report = response.json()
    exported = client.get(f"/api/reviews/{report['id']}/report.md")
    assert "模拟企业" in exported.text and "SHA-256" in exported.text
    assert client.get(f"/api/reviews/{report['id']}/graph").json()["nodes"]


def test_missing_evidence_can_be_completed_from_uploaded_csv(client):
    data = "字段,数值,单位,期间\nrd_2024,220,万元,2024\n".encode()
    asset = client.post("/api/assets", files={"file":("财务补证.csv",data,"text/csv")}, data={"purpose":"company"}).json()
    assert asset["status"] == "parsed"
    assert asset["proposals"][0]["value"] == 220
    before = client.get("/api/companies/demo-02").json()
    assert "rd_2024" not in before["facts"]
    proposal = asset["proposals"][0]["id"]
    accepted = client.post(f"/api/assets/{asset['id']}/proposals/{proposal}/accept", json={"company_id":"demo-02"})
    assert accepted.status_code == 200
    after = client.post("/api/reviews", json={"company_id":"demo-02","policy_id":"hnte-bj-2026","as_of":"2026-09-22"}).json()
    assert after["status"] == "pass"
    rd = next(c for c in after["checks"] if c["id"] == "rd_ratio")
    assert any(e["asset_id"] == asset["id"] for e in rd["evidence"])
    assert client.post(f"/api/assets/{asset['id']}/proposals/{proposal}/accept", json={"company_id":"demo-02"}).status_code == 400


def test_conflicting_upload_does_not_replace_old_value(client):
    raw = "employees,90,人,2025".encode()
    a = client.post("/api/assets", files={"file":("staff.csv",raw,"text/csv")}, data={"purpose":"company"}).json()
    client.post(f"/api/assets/{a['id']}/proposals/{a['proposals'][0]['id']}/accept", json={"company_id":"demo-01"})
    fact = client.get("/api/companies/demo-01").json()["facts"]["employees"]
    assert fact["value"] == 80 and fact["status"] == "conflict" and len(fact["evidence"]) == 2


def test_policy_upload_does_not_change_business_rules(client):
    before = client.get("/api/dashboard").json()["policies"]
    a = client.post("/api/assets", files={"file":("政策.txt","研发费用不低于销售收入的百分之五。".encode(),"text/plain")}, data={"purpose":"policy"}).json()
    assert a["proposals"]
    client.post(f"/api/assets/{a['id']}/proposals/{a['proposals'][0]['id']}/accept", json={})
    after = client.get("/api/dashboard").json()
    assert len(after["ontology"]) == 1 and before == after["policies"]


def test_unknown_company_and_bad_date(client):
    assert client.get("/api/companies/missing").status_code == 404
    assert client.post("/api/reviews", json={"company_id":"demo-01","policy_id":"hnte-bj-2026","as_of":"yesterday"}).status_code == 422


def test_image_is_not_falsely_marked_as_parsed(client):
    a = client.post("/api/assets", files={"file":("scan.png",b"image bytes","image/png")}, data={"purpose":"company"}).json()
    assert a["status"] == "pending_ocr" and a["proposals"] == []


def test_cross_origin_mutation_rejected(client):
    assert client.post("/api/reviews", headers={"Origin":"https://unrelated.example"}, json={"company_id":"demo-01","policy_id":"hnte-bj-2026"}).status_code == 403


def test_uploaded_filename_cannot_escape_storage(client, isolated_store):
    a = client.post("/api/assets", files={"file":("../../evil.txt",b"hello","text/plain")}, data={"purpose":"company"}).json()
    assert a["filename"] == "evil.txt"
    assert (isolated_store.runtime_dir()/"uploads"/f"{a['id']}.txt").exists()


def test_unsupported_upload(client):
    assert client.post("/api/assets", files={"file":("run.exe",b"MZ","application/octet-stream")}).status_code == 400


def test_corrupt_pdf_returns_client_error(client):
    assert client.post("/api/assets", files={"file":("broken.pdf",b"broken","application/pdf")}).status_code == 400


def test_duplicate_company_not_overwritten(client):
    original=client.get("/api/companies/demo-01").json()
    original["name"]="Other name"
    assert client.post("/api/companies", json=original).status_code == 409
    assert client.get("/api/companies/demo-01").json()["name"] != "Other name"


def test_manual_change_recalculates_but_saved_report_remains(client):
    r=client.post("/api/reviews",json={"company_id":"demo-01","policy_id":"sme-bj-2026","as_of":"2026-09-22"}).json()
    client.patch("/api/companies/demo-01/facts/employees",json={"value":501,"unit":"人","period":"2025","confirmed":True,"note":"对照人员台账核实"})
    updated=client.post("/api/reviews",json={"company_id":"demo-01","policy_id":"sme-bj-2026","as_of":"2026-09-22"}).json()
    assert updated["status"]=="fail"
    assert client.get('/api/reviews/'+r['id']).json()['status']=='pass'


def test_xlsx_keeps_sheet_row_locator():
    book=Workbook();book.active.title="财务数据";book.active.append(["rd_2024",220,"万元","2024"])
    raw=io.BytesIO();book.save(raw)
    chunks,status=parse(raw.getvalue(),".xlsx")
    assert status=="parsed" and chunks[0]["locator"]=="财务数据!第1行"


def test_search_returns_sources(client):
    r=client.get('/api/search',params={'q':'研发费用'}).json()
    assert r['results'] and all('locator' in x for x in r['results'])


def test_evaluation_endpoint_returns_measured_suite(client):
    result = client.get('/api/evaluation').json()
    assert result['engine']['summary']['case_count'] == 15
    assert result['engine']['summary']['exact_case_accuracy'] == 1.0
