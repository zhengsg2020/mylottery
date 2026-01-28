"""网络数据获取模块"""
import requests
from bs4 import BeautifulSoup


def fetch_500_data(l_type, limit: int = 30):
    """从500.com抓取开奖数据

    :param l_type: "ssq" 或 "dlt"
    :param limit: 拉取最近多少期，默认 30 期
    """
    url = f"http://datachart.500.com/{l_type}/history/newinc/history.php?limit={int(limit)}"
    resp = requests.get(url, timeout=10)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.find_all("tr", class_="t_tr1")
    results = []
    for row in rows:
        tds = [td.get_text().strip() for td in row.find_all("td")]
        if len(tds) < 8:
            continue
        try:
            if l_type == "ssq":
                results.append(
                    {
                        "issue": tds[0],
                        "nums": [[int(x) for x in tds[1:7]], [int(tds[7])]],
                    }
                )
            else:
                results.append(
                    {
                        "issue": tds[0],
                        "nums": [
                            [int(x) for x in tds[1:6]],
                            [int(tds[6]), int(tds[7])],
                        ],
                    }
                )
        except Exception:
            continue
    return results
